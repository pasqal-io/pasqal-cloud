# Copyright 2020 Pasqal Cloud Services development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from warnings import warn

from requests.exceptions import HTTPError

from pasqal_cloud.authentication import TokenProvider
from pasqal_cloud.batch import Batch, RESULT_POLLING_INTERVAL
from pasqal_cloud.client import Client
from pasqal_cloud.device import BaseConfig, EmulatorType
from pasqal_cloud.endpoints import (
    AUTH0_CONFIG,  # noqa: F401
    Auth0Conf,
    Endpoints,
    PASQAL_ENDPOINTS,  # noqa: F401
)
from pasqal_cloud.errors import (
    BatchCancellingError,
    BatchClosingError,
    BatchCreationError,
    BatchFetchingError,
    DeviceSpecsFetchingError,
    JobCancellingError,
    JobCreationError,
    JobFetchingError,
    OnlyCompleteOrOpenCanBeSet,
    RebatchError,
    WorkloadCancellingError,
    WorkloadCreationError,
    WorkloadFetchingError,
)
from pasqal_cloud.job import CreateJob, Job
from pasqal_cloud.utils.constants import JobStatus  # noqa: F401
from pasqal_cloud.utils.filters import (
    CancelJobFilters,
    JobFilters,
    PaginationParams,
    RebatchFilters,
)
from pasqal_cloud.utils.responses import JobCancellationResponse, PaginatedResponse
from pasqal_cloud.workload import Workload


class SDK:
    _client: Client

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        token_provider: Optional[TokenProvider] = None,
        endpoints: Optional[Endpoints] = None,
        auth0: Optional[Auth0Conf] = None,
        webhook: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        """
        This class provides helper methods to call the PASQAL Cloud endpoints.

        To authenticate to PASQAL Cloud, you have to provide either an
        email/password combination or a TokenProvider instance.
        You may omit the password, you will then be prompted to enter one.

        Args:
            username: Email of the user to login as.
            password: Password of the user to login as.
            token_provider: The token provider is an alternative log-in method \
              not for human users.
            webhook: Webhook where the job results are automatically sent to.
            endpoints: Endpoints targeted of the public apis.
            auth0: Auth0Config object to define the auth0 tenant to target.
            project_id: ID of the owner project of the batch.
        """

        if not project_id:
            raise ValueError("You need to provide a project_id")

        self._client = Client(
            project_id=project_id,
            username=username,
            password=password,
            token_provider=token_provider,
            endpoints=endpoints,
            auth0=auth0,
        )
        self.batches: Dict[str, Batch] = {}
        self.workloads: Dict[str, Workload] = {}
        self.webhook = webhook

    def _get_batch(
        self,
        id: str,
    ) -> Dict[str, Any]:
        try:
            return self._client.get_batch(id)
        except HTTPError as e:
            raise BatchFetchingError(e) from e

    def create_batch(
        self,
        serialized_sequence: str,
        jobs: List[CreateJob],
        complete: Optional[bool] = None,
        open: Optional[bool] = None,
        emulator: Optional[EmulatorType] = None,
        configuration: Optional[BaseConfig] = None,
        wait: bool = False,
        fetch_results: bool = False,
    ) -> Batch:
        """Create a new batch and send it to the API.

        Args:
            serialized_sequence: Serialized pulser sequence.
            complete: Opposite of open, deprecated.
            jobs: List of jobs to be added to the batch at creation.
            open: If all jobs are sent at creation.
              If set to True, jobs can be added using the `Batch.add_jobs` method.
              Once all the jobs are sent, use the `Batch.close` method.
              Otherwise, the batch will be timed out if all jobs have already
              been terminated and no new jobs are sent.
            emulator: The type of emulator to use,
              If set to None, the device_type will be set to the one
              stored in the serialized sequence
            configuration: A dictionary with extra configuration for the emulators
             that accept it.
            wait: Whether to block on this statement until all the submitted jobs are
                terminated
            fetch_results (deprecated): Whether to wait for the batch to
              be done and fetch results


        Returns:
            Batch: The new batch that has been created in the database.

        Raises:
            BatchCreationError: If batch creation failed
            BatchFetchingError: If batch fetching failed
        """
        if complete is not None and open is not None:
            raise OnlyCompleteOrOpenCanBeSet
        if complete is not None:
            warn(
                "Argument `complete` is deprecated and will be removed in a"
                " future version. Please use argument `open` instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            open = not complete
        elif complete is None and open is None:
            open = False
        if fetch_results:
            warn(
                "Argument `fetch_results` is deprecated and will be removed in a"
                " future version. Please use argument `wait` instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            wait = wait or fetch_results

        req = {
            "sequence_builder": serialized_sequence,
            "webhook": self.webhook,
            "jobs": jobs,
            "open": open,
        }

        # the emulator field is only added in the case
        # an emulator job is requested otherwise it's left empty
        if emulator:
            req.update({"emulator": emulator})

        # The configuration field is only added in the case
        # it's requested
        if configuration:
            req.update({"configuration": configuration.to_dict()})  # type: ignore[dict-item]

        try:
            batch_rsp = self._client.send_batch(req)
        except HTTPError as e:
            raise BatchCreationError(e) from e

        batch = Batch(**batch_rsp, _client=self._client)

        if wait:
            while any(
                job.status in {"PENDING", "RUNNING"} for job in batch.ordered_jobs
            ):
                time.sleep(RESULT_POLLING_INTERVAL)
                batch.refresh()

        self.batches[batch.id] = batch
        return batch

    def get_batch(self, id: str, fetch_results: bool = False) -> Batch:
        """Retrieve a batch's data and all its jobs.

        Args:
            fetch_results (deprecated): Whether to wait for the batch to be
              done and fetch results
            id: ID of the batch.

        Returns:
            Batch: the batch stored in the PCS database.

        Raises:
            BatchFetchingError: in case fetching failed
        """
        if fetch_results:
            warn(
                "Argument `fetch_results` is deprecated and will be removed in a"
                " future version. Results are fetched anyway with this function.",
                DeprecationWarning,
                stacklevel=2,
            )
        batch_rsp = self._get_batch(id)
        batch = Batch(**batch_rsp, _client=self._client)
        self.batches[batch.id] = batch
        return batch

    def cancel_batch(self, id: str) -> Batch:
        """Cancel the given batch on the PCS

        Args:
            id: ID of the batch.
        """
        try:
            batch_rsp = self._client.cancel_batch(id)
        except HTTPError as e:
            raise BatchCancellingError(e) from e
        return Batch(**batch_rsp, _client=self._client)

    def rebatch(
        self,
        id: Union[UUID, str],
        filters: Optional[RebatchFilters] = None,
    ) -> Batch:
        """
        Retry a group of jobs matching filters in a new batch.

        Args:
            id: id of the batch to re-create
            filters: filters to be applied to find the jobs that will be retried

        Returns:
            An instance of a rescheduled Batch model. The fields
            can differ from the original batch as the record
            is recreated as to prevent modifying the original batch.

        Raises:
            RebatchError if rebatch call failed.
        """
        if filters is None:
            filters = RebatchFilters()
        elif not isinstance(filters, RebatchFilters):
            raise ValueError(
                f"Filters needs to be a RebatchFilters instance, not a {type(filters)}"
            )

        try:
            new_batch_data = self._client.rebatch(
                batch_id=id,
                filters=filters,
            )
        except HTTPError as e:
            raise RebatchError(e) from e
        return Batch(**new_batch_data, _client=self._client)

    def get_jobs(
        self,
        filters: Optional[JobFilters] = None,
        pagination_params: Optional[PaginationParams] = None,
    ) -> PaginatedResponse:
        """
        Retrieve a list of jobs matching filters using a pagination system.

        Jobs are sorted by their creation date in descending order.

        If no 'pagination_params' are provided, the first 100 jobs
        matching the query will be returned by default.

        Args:
            filters: Filters to be applied to the jobs.
            pagination_params: Pagination to be applied to the query.

        Examples:
        >>> get_jobs(filters=JobFilters(status=JobStatus.ERROR))
        Returns the first 100 jobs with an ERROR status.

        >>> get_jobs(filters=JobFilters(status=JobStatus.ERROR),
                     pagination_params=PaginationParams(offset=100))
        Returns jobs 101-200 with an ERROR status.

        >>> get_jobs(filters=JobFilters(status=JobStatus.ERROR),
                     pagination_params=PaginationParams(offset=200))
        Returns jobs 201-300 with an ERROR status.

        Returns:
            PaginatedResponse: A class instance with two fields:
                - total: An integer representing the total number of jobs
                         matching the filters.
                - results: A list of jobs matching the filters and pagination
                           parameters provided.

        Raises:
            JobFetchingError: If fetching jobs call failed.
            ValueError: If `filters` is not an instance of JobFilters
                    or if `pagination_params` is not an instance of PaginationParams.
        """

        if pagination_params is None:
            pagination_params = PaginationParams()
        elif not isinstance(pagination_params, PaginationParams):
            raise ValueError(
                "Pagination parameters needs to be a PaginationParams instance, "
                f"not a {type(pagination_params)}"
            )

        if filters is None:
            filters = JobFilters()
        elif not isinstance(filters, JobFilters):
            raise ValueError(
                f"Filters needs to be a JobFilters instance, not a {type(filters)}"
            )

        try:
            response = self._client.get_jobs(
                filters=filters, pagination_params=pagination_params
            )
            jobs = response["data"]
            pagination_response = response.get("pagination")
            # It should return a pagination all the time
            total_nb_jobs = pagination_response["total"] if pagination_response else 0
        except HTTPError as e:
            raise JobFetchingError(e) from e
        return PaginatedResponse(
            total=total_nb_jobs,
            offset=pagination_params.offset,
            results=[Job(**job, _client=self._client) for job in jobs],
        )

    def _get_job(self, id: str) -> Dict[str, Any]:
        try:
            return self._client.get_job(id)
        except HTTPError as e:
            raise JobFetchingError(e) from e

    def get_job(self, id: str, wait: bool = False) -> Job:
        """Retrieve a job's data.

        Args:
            id: ID of the job.
            wait: Whether to wait for the job to be done

        Returns:
            Job: The job stored in the PCS database.

        Raises:
            JobFetchingError: If fetching failed.
        """
        job_rsp = self._get_job(id)
        if wait:
            while job_rsp["status"] in ["PENDING", "RUNNING"]:
                time.sleep(RESULT_POLLING_INTERVAL)
                job_rsp = self._get_job(id)
        return Job(**job_rsp, _client=self._client)

    def add_jobs(self, batch_id: str, jobs: List[CreateJob]) -> Batch:
        """
        Add jobs to an already existing batch.

        Args:
            batch_ID: A unique identifier for the batch data.
            Jobs: a collection of CreateJob payloads

        Returns:
            An instance of a Batch model from the PCS database

        Raises:
            JobCreationError, which spawns from a HTTPError.
        """
        try:
            resp = self._client.add_jobs(batch_id, jobs)
        except HTTPError as e:
            raise JobCreationError(e)
        return Batch(**resp, _client=self._client)

    def complete_batch(self, batch_id: str) -> Batch:
        """
        Deprecated, use close_batch instead.
        """
        warn(
            "This method is deprecated, use close_batch instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.close_batch(batch_id)

    def close_batch(self, batch_id: str) -> Batch:
        """
        Set a batch 'open' field as False, indicating no more Jobs
        can be submitted.

        Args:
            batch_ID: A unique identifier for the batch data.

            Returns:
                An instance of a Batch model from the PCS database

        Raises:
            BatchClosingError which spawns from a HTTPError
        """
        try:
            resp = self._client.close_batch(batch_id)
        except HTTPError as e:
            raise BatchClosingError(e)

        return Batch(**resp, _client=self._client)

    def cancel_job(self, id: str) -> Job:
        """Cancel the given job on the PCS

        Args:
            id: ID of the job.

        Returns:
            Job: The job stored in the PCS database.
        """
        try:
            job_rsp = self._client.cancel_job(id)
        except HTTPError as e:
            raise JobCancellingError(e) from e

        return Job(**job_rsp, _client=self._client)

    def cancel_jobs(
        self,
        batch_id: Union[UUID, str],
        filters: Optional[CancelJobFilters] = None,
    ) -> JobCancellationResponse:
        """
        Cancel a group of jobs matching the filters in a selected batch.

        Args:
            batch_id: id of the batch
            filters: filters to be applied to find the jobs that will be cancelled

        Returns:
            JobCancellationResponse:
            a class containing the jobs that have been cancelled and the id of the jobs
            that could not be cancelled with the reason explained

        Raises:
            JobCancellingError which spawns from a HTTPError

        """
        if filters is None:
            filters = CancelJobFilters()
        elif not isinstance(filters, CancelJobFilters):
            raise ValueError(
                "Filters needs to be a CancelJobFilters instance, "
                f"not a {type(filters)}"
            )

        try:
            response = self._client.cancel_jobs(
                batch_id=batch_id,
                filters=filters,
            )
        except HTTPError as e:
            raise JobCancellingError(e) from e
        return JobCancellationResponse(
            jobs=[Job(**job, _client=self._client) for job in response["jobs"]],
            errors=response["errors"],
        )

    def _get_workload(self, id: str) -> Dict[str, Any]:
        try:
            return self._client.get_workload(id)
        except HTTPError as e:
            raise WorkloadFetchingError(e) from e

    def wait_for_workload(
        self, id: str, workload_rsp: Dict[str, Any]
    ) -> Dict[str, Any]:
        while workload_rsp["status"] in ["PENDING", "RUNNING"]:
            time.sleep(RESULT_POLLING_INTERVAL)
            workload_rsp = self._get_workload(id)
        return workload_rsp

    def create_workload(
        self,
        workload_type: str,
        backend: str,
        config: Dict[str, Any],
        wait: bool = False,
    ) -> Workload:
        """Create a workload to be scheduled for execution.

        Args:
            workload_type: The type of workload to create.
            backend: The backend to run the workload on.
            config: The config that defines the workload.
            wait: Whether to wait for completion to fetch results.

        Returns:
            workload: The created workload instance.

        Raises:
            WorkloadCreationError: If creation failed.

        """
        req = {
            "workload_type": workload_type,
            "backend": backend,
            "config": config,
        }
        try:
            workload_rsp = self._client.send_workload(req)
        except HTTPError as e:
            raise WorkloadCreationError(e) from e
        if wait:
            workload_rsp = self.wait_for_workload(workload_rsp["id"], workload_rsp)
        workload = Workload(**workload_rsp, _client=self._client)

        self.workloads[workload.id] = workload
        return workload

    def get_workload(self, id: str, wait: bool = False) -> Workload:
        """Retrieve a workload's data.

        Args:
            id: ID of the workload.
            wait: Whether to wait for the workload to be done.

        Returns:
            workload: The workload stored in the PCS database.

        Raises:
            WorkloadFetchingError: If fetching failed.
        """
        workload_rsp = self._get_workload(id)
        if wait:
            workload_rsp = self.wait_for_workload(id, workload_rsp)
        return Workload(**workload_rsp, _client=self._client)

    def cancel_workload(self, id: str) -> Workload:
        """Cancel the given workload on the PCS.

        Args:
            id: Workload id.

        Returns:
            workload: The canceled workload.

        Raises:
            WorkloadCancelingError: If cancelation failed.
        """
        try:
            workload_rsp = self._client.cancel_workload(id)
        except HTTPError as e:
            raise WorkloadCancellingError(e) from e
        return Workload(**workload_rsp, _client=self._client)

    def get_device_specs_dict(self) -> Dict[str, str]:
        """Retrieve the list of available device specifications.

        Returns:
            DeviceSpecs: The list of available device specifications.

        Raises:
            DeviceSpecsFetchingError: If fetching of specs failed.
        """

        try:
            return self._client.get_device_specs_dict()
        except HTTPError as e:
            raise DeviceSpecsFetchingError(e) from e
