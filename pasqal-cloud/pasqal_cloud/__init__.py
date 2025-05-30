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
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from warnings import simplefilter, warn

from requests.exceptions import HTTPError

from pasqal_cloud.authentication import TokenProvider
from pasqal_cloud.batch import Batch, RESULT_POLLING_INTERVAL
from pasqal_cloud.client import Client
from pasqal_cloud.device import BaseConfig as BaseConfig
from pasqal_cloud.device import DeviceTypeName as DeviceTypeName
from pasqal_cloud.device import EmulatorType as EmulatorType
from pasqal_cloud.endpoints import (
    AUTH0_CONFIG,  # noqa: F401
    Auth0Conf,
    PASQAL_ENDPOINTS,  # noqa: F401
)
from pasqal_cloud.endpoints import (
    Endpoints as Endpoints,
)
from pasqal_cloud.errors import (
    BatchCancellingError,
    BatchClosingError,
    BatchCreationError,
    BatchFetchingError,
    BatchSetTagsError,
    DeviceSpecsFetchingError,
    InvalidDeviceTypeSet,
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
from pasqal_cloud.utils.constants import (  # noqa: F401
    BatchStatus,
    JobStatus,
    QueuePriority,
)
from pasqal_cloud.utils.filters import (
    BatchFilters,
    CancelJobFilters,
    JobFilters,
    PaginationParams,
    RebatchFilters,
)
from pasqal_cloud.utils.responses import (
    BatchCancellationResponse,
    JobCancellationResponse,
    PaginatedResponse,
)
from pasqal_cloud.workload import Workload

from ._version import __version__, deprecation_date

DEPRECATION_WARNING_PERIOD = timedelta(days=30)

# Ensure DeprecationWarnings are not filtered out at runtime
simplefilter("always", DeprecationWarning)


def _check_sdk_version() -> None:
    # Compare current date to deprecation date to check whether
    # current version has fallen out of maintenance window.
    current_date = datetime.now(tz=timezone.utc)
    deprecation_datetime = datetime.strptime(deprecation_date, "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )
    warning_start = deprecation_datetime - DEPRECATION_WARNING_PERIOD

    upgrade_instruction = (
        "Please upgrade to the latest version using the following command:\n"
        "`pip install --upgrade pasqal-cloud`"
    )

    if current_date >= warning_start and current_date < deprecation_datetime:
        warn(
            f"SDK version {__version__} will be deprecated on {deprecation_datetime}. "
            + upgrade_instruction,
            DeprecationWarning,
        )
    elif current_date >= deprecation_datetime:
        warn(
            f"SDK version {__version__} is no longer supported. " + upgrade_instruction,
            DeprecationWarning,
        )


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
        This class provides helper methods to call the Pasqal Cloud endpoints.

        To authenticate to Pasqal Cloud, you have to provide either an
        email/password combination or a TokenProvider instance.
        You may omit the password, you will then be prompted to enter one.


        The SDK can be initialized with several authentication options:
            - Option 1: No arguments -> Allows unauthenticated access to public
                features.
            - Option 2: `username` and `password` -> Authenticated access using a
                username and password.
            - Option 3: `username` only -> Prompts for password during initialization.
            - Option 4 (for developers): Provide a custom `token_provider` for
                token-based authentication.

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
        _check_sdk_version()

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

    def user_token(self) -> Union[str, None]:
        return self._client.user_token()

    def _get_batch(
        self,
        id: str,
    ) -> Dict[str, Any]:
        try:
            return self._client.get_batch(id)
        except HTTPError as e:
            raise BatchFetchingError(e) from e

    def _validate_device_type(
        self,
        emulator: Optional[EmulatorType],
        device_type: Optional[DeviceTypeName],
    ) -> DeviceTypeName:
        if emulator is not None and device_type is not None:
            raise InvalidDeviceTypeSet
        if emulator is not None:
            warn(
                "Argument `emulator` is deprecated and will be removed in a"
                " future version. Please use argument `device_type` instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return DeviceTypeName(str(emulator))
        if emulator is None and device_type is None:
            return DeviceTypeName.FRESNEL
        return device_type

    def _validate_open(
        self,
        complete: Optional[bool],
        open: Optional[bool],
    ) -> bool:
        if complete is not None and open is not None:
            raise OnlyCompleteOrOpenCanBeSet
        if complete is not None:
            warn(
                "Argument `complete` is deprecated and will be removed in a"
                " future version. Please use argument `open` instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return not complete
        if complete is None and open is None:
            return False
        return open

    def create_batch(
        self,
        serialized_sequence: str,
        jobs: List[CreateJob],
        complete: Optional[bool] = None,
        open: Optional[bool] = None,
        emulator: Optional[EmulatorType] = None,
        device_type: Optional[DeviceTypeName] = None,
        configuration: Optional[BaseConfig] = None,
        backend_configuration: Optional[str] = None,
        wait: bool = False,
        fetch_results: bool = False,
        tags: Optional[list[str]] = None,
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
            tags: List of keywords that can be used to refine the Batch search

        Returns:
            Batch: The new batch that has been created in the database.

        Raises:
            BatchCreationError: If batch creation failed
            BatchFetchingError: If batch fetching failed
        """
        device_type = self._validate_device_type(emulator, device_type)
        open = self._validate_open(complete, open)

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
            "device_type": device_type,
        }
        # The configuration field is only added in the case
        # it's requested
        if configuration:
            req.update({"configuration": configuration.to_dict()})  # type: ignore[dict-item]

        if tags:
            req.update({"tags": tags})  # type: ignore[dict-item]

        # The backend_configuration is only added if
        # a value is provided
        if backend_configuration:
            req.update({"backend_configuration": backend_configuration})

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

    def get_batches(
        self,
        filters: Optional[BatchFilters] = None,
        pagination_params: Optional[PaginationParams] = None,
    ) -> PaginatedResponse:
        """
        Retrieve a list of batches matching filters using a pagination system.

        Batches are sorted by their creation date in descending order.

        If no 'pagination_params' are provided, the first 100 batches
        matching the query will be returned by default.

        Args:
            filters: Filters to be applied to the batches.
            pagination_params: Pagination to be applied to the query.

        Examples:
        >>> get_batches(filters=BatchFilters(status=BatchStatus.ERROR))
        Returns the first 100 batches with an ERROR status.

        >>> Get_batches(filters=BatchFilters(status=BatchStatus.ERROR),
                     pagination_params=PaginationParams(offset=100))
        Returns batches 101-200 with an ERROR status.

        >>> Get_batches(filters=BatchFilters(status=BatchStatus.ERROR),
                     pagination_params=PaginationParams(offset=200))
        Returns batches 201-300 with an ERROR status.

        Returns:
            PaginatedResponse: Includes the results of the API and some
                pagination information.

        Raises:
            BatchFetchingError: If fetching batches call failed.
            TypeError: If `filters` is not an instance of BatchFilters,
                or if `pagination_params` is not an instance of PaginationParams.
        """

        if pagination_params is None:
            pagination_params = PaginationParams()
        elif not isinstance(pagination_params, PaginationParams):
            raise TypeError(
                f"Pagination parameters needs to be a PaginationParams instance, "
                f"not a {type(pagination_params)}"
            )

        if filters is None:
            filters = BatchFilters()
        elif not isinstance(filters, BatchFilters):
            raise TypeError(
                f"Filters needs to be a BatchFilters instance, not a {type(filters)}"
            )

        try:
            response = self._client.get_batches(
                filters=filters, pagination_params=pagination_params
            )
            batches = response["data"]
            pagination_response = response.get("pagination")
            # It should return a pagination all the time
            total_nb_batches = (
                pagination_response["total"] if pagination_response else 0
            )
        except HTTPError as e:
            raise BatchFetchingError(e) from e
        return PaginatedResponse(
            total=total_nb_batches,
            offset=pagination_params.offset,
            results=[Batch(**batch, _client=self._client) for batch in batches],
        )

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

    def cancel_batches(self, batch_ids: List[str]) -> BatchCancellationResponse:
        """
        Cancel a group of batches by their ids.

        Args:
            batch_ids: batch ids to cancel.

        Returns:
            BatchCancellationResponse:
            a class containing the batches that have been cancelled and the id of
            the batches that could not be cancelled with the reason explained

        Raises:
            BatchCancellingError: spawns from a HTTPError

        """

        try:
            response = self._client.cancel_batches(
                batch_ids=batch_ids,
            )
        except HTTPError as e:
            raise BatchCancellingError(e) from e
        return BatchCancellationResponse(
            batches=[
                Batch(**batch, _client=self._client) for batch in response["batches"]
            ],
            errors=response["errors"],
        )

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
            RebatchError: if rebatch call failed.
        """
        if filters is None:
            filters = RebatchFilters()
        elif not isinstance(filters, RebatchFilters):
            raise TypeError(
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
            PaginatedResponse: Includes the results of the API and some
                pagination information.

        Raises:
            JobFetchingError: If fetching jobs call failed.
            TypeError: If `filters` is not an instance of JobFilters
                    or if `pagination_params` is not an instance of PaginationParams.
        """

        if pagination_params is None:
            pagination_params = PaginationParams()
        elif not isinstance(pagination_params, PaginationParams):
            raise TypeError(
                "Pagination parameters needs to be a PaginationParams instance, "
                f"not a {type(pagination_params)}"
            )

        if filters is None:
            filters = JobFilters()
        elif not isinstance(filters, JobFilters):
            raise TypeError(
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
            batch_id: A unique identifier for the batch data.
            jobs: a collection of CreateJob payloads

        Returns:
            An instance of a Batch model from the PCS database

        Raises:
            JobCreationError: spawns from a HTTPError.
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
            batch_id: A unique identifier for the batch data.

        Returns:
            An instance of a Batch model from the PCS database

        Raises:
            BatchClosingError: spawns from a HTTPError
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
            JobCancellingError: spawns from a HTTPError

        """
        if filters is None:
            filters = CancelJobFilters()
        elif not isinstance(filters, CancelJobFilters):
            raise TypeError(
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

    def set_batch_tags(
        self,
        batch_id: str,
        tags: list[str],
    ) -> Batch:
        """Set tags to an existing batch, overwriting previous ones already set.

        Args:
            batch_id: Batch id.
            tags: the tags defining the batch

        Returns:
            batch: The updated batch with newly set tags.

        Raises:
            BatchSetTagsError: If setting tags to a batch failed.
        """

        try:
            resp = self._client.set_batch_tags(batch_id, tags)
        except HTTPError as e:
            raise BatchSetTagsError(e)

        return Batch(**resp, _client=self._client)
