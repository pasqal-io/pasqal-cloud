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
from requests.exceptions import HTTPError
from typing import Any, Dict, List, Optional
from warnings import warn

from pasqal_cloud.authentication import TokenProvider
from pasqal_cloud.batch import Batch, RESULT_POLLING_INTERVAL
from pasqal_cloud.client import Client
from pasqal_cloud.device import BaseConfig, EmulatorType
from pasqal_cloud.endpoints import (  # noqa: F401
    AUTH0_CONFIG,
    Auth0Conf,
    Endpoints,
    PASQAL_ENDPOINTS,
)
from pasqal_cloud.errors import (
    BatchCancellingError,
    BatchCreationError,
    BatchFetchingError,
    DeviceSpecsFetchingError,
    JobCancellingError,
    JobFetchingError,
    WorkloadCancellingError,
    WorkloadCreationError,
    WorkloadFetchingError,
)
from pasqal_cloud.job import CreateJob, Job
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
        group_id: Optional[str] = None,  # deprecated
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
            group_id (deprecated): Use project_id instead.
        """

        # Ticket (#622), to be removed,
        # used to avoid a breaking change during the group to project renaming
        if not project_id:
            if not group_id:
                raise TypeError(
                    "Either a 'group_id' or 'project_id' has to be given as argument"
                )
            warn(
                "The parameter 'group_id' is deprecated, from now on use"
                " 'project_id' instead",
                DeprecationWarning,
                stacklevel=2,
            )
            project_id = group_id

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
            return self._client._get_batch(id)
        except HTTPError as e:
            raise BatchFetchingError(e) from e

    def create_batch(
        self,
        serialized_sequence: str,
        jobs: List[CreateJob],
        complete: bool = True,
        emulator: Optional[EmulatorType] = None,
        configuration: Optional[BaseConfig] = None,
        wait: bool = False,
        fetch_results: bool = False,
    ) -> Batch:
        """Create a new batch and send it to the API.

        Args:
            serialized_sequence: Serialized pulser sequence.
            jobs: List of jobs to be added to the batch at creation.
            complete: True (default), if all jobs are sent at creation.
              If set to False, jobs can be added using the `Batch.add_jobs` method.
              Once all the jobs are sent, use the `Batch.declare_complete` method.
              Otherwise, the batch will be timed out if all jobs have already
              been terminated and no new jobs are sent.
            emulator: The type of emulator to use,
              If set to None, the device_type will be set to the one
              stored in the serialized sequence
            configuration: A dictionary with extra configuration for the emulators
             that accept it.
            wait: Whether to block on this statement until all the submitted jobs are terminated
            fetch_results (deprecated): Whether to wait for the batch to
              be done and fetch results


        Returns:
            Batch: The new batch that has been created in the database.

        Raises:
            BatchCreationError: If batch creation failed
            BatchFetchingError: If batch fetching failed
        """
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
            "complete": complete,
        }

        # the emulator field is only added in the case
        # an emulator job is requested otherwise it's left empty
        if emulator:
            req.update({"emulator": emulator})

        # The configuration field is only added in the case
        # it's requested
        if configuration:
            req.update({"configuration": configuration.to_dict()})  # type: ignore

        try:
            batch_rsp = self._client._send_batch(req)
        except HTTPError as e:
            raise BatchCreationError(e) from e

        batch = Batch(**batch_rsp, _client=self._client)

        if wait:
            while any(
                [job.status in {"PENDING", "RUNNING"} for job in batch.ordered_jobs]
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
            batch_rsp = self._client._cancel_batch(id)
        except HTTPError as e:
            raise BatchCancellingError(e) from e
        batch = Batch(**batch_rsp, _client=self._client)
        return batch

    def _get_job(self, id: str) -> Dict[str, Any]:
        try:
            return self._client._get_job(id)
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
        job = Job(**job_rsp, _client=self._client)
        return job

    def cancel_job(self, id: str) -> Job:
        """Cancel the given job on the PCS

        Args:
            id: ID of the job.
        """
        try:
            job_rsp = self._client._cancel_job(id)
        except HTTPError as e:
            raise JobCancellingError(e) from e

        job = Job(**job_rsp, _client=self._client)
        return job

    def _get_workload(self, id: str) -> Dict[str, Any]:
        try:
            return self._client._get_workload(id)
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
            workload_rsp = self._client._send_workload(req)
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
        workload = Workload(**workload_rsp, _client=self._client)
        return workload

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
            workload_rsp = self._client._cancel_workload(id)
        except HTTPError as e:
            raise WorkloadCancellingError(e) from e
        workload = Workload(**workload_rsp, _client=self._client)
        return workload

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
