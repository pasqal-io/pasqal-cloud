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
from typing import Any, Dict, List, Optional
from warnings import warn

from pasqal_cloud.authentication import TokenProvider
from pasqal_cloud.batch import Batch, RESULT_POLLING_INTERVAL
from pasqal_cloud.client import Client
from pasqal_cloud.device import BaseConfig
from pasqal_cloud.device import EmulatorType
from pasqal_cloud.endpoints import Auth0Conf, Endpoints, PASQAL_ENDPOINTS, AUTH0_CONFIG
from pasqal_cloud.job import Job


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
            username: email of the user to login as.
            password: password of the user to login as.
            token_provider: The token provider is an alternative log-in method not for human users.
            webhook: Webhook where the job results are automatically sent to.
            endpoints: Endpoints targeted of the public apis.
            auth0: Auth0Config object to define the auth0 tenant to target.
            project_id: ID of the owner project of the batch.
            group_id (deprecated): Use project_id instead.
        """

        # Ticket (#622), to be removed, used to avoid a breaking change during the group to project renaming
        if not project_id:
            if not group_id:
                raise TypeError(
                    "Either a 'group_id' or 'project_id' has to be given as argument"
                )
            warn(
                (
                    "The parameter 'group_id' is deprecated, from now on use"
                    " 'project_id' instead"
                ),
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
        self.webhook = webhook

    def create_batch(
        self,
        serialized_sequence: str,
        jobs: List[Dict[str, Any]],
        emulator: Optional[EmulatorType] = None,
        configuration: Optional[BaseConfig] = None,
        wait: bool = False,
        fetch_results: bool = False,
    ) -> Batch:
        """Create a new batch and send it to the API.
        For Iroise MVP, the batch must contain at least one job and will be declared as
        complete immediately.

        Args:
            serialized_sequence: Serialized pulser sequence.
            jobs: List of jobs to be added to the batch at creation.
                (#TODO: Make optional after Iroise MVP)
            emulator: The type of emulator to use,
              If set to None, the device_type will be set to the one
              stored in the serialized sequence
            configuration: A dictionary with extra configuration for the emulators
                that accept it.
            wait: Whether to wait for the batch to be done
            fetch_results: Whether to download the results. Implies waiting
                for the batch.


        Returns:
            Batch: The new batch that has been created in the database.
        """

        req = {
            "sequence_builder": serialized_sequence,
            "webhook": self.webhook,
            "jobs": jobs,
        }

        # the emulator field is only added in the case
        # an emulator job is requested otherwise it's left empty
        if emulator:
            req.update({"emulator": emulator})

        # The configuration field is only added in the case
        # it's requested
        if configuration:
            req.update({"configuration": configuration.to_dict()})  # type: ignore

        batch_rsp, jobs_rsp = self._client._send_batch(req)
        batch_id = batch_rsp["id"]
        if wait or fetch_results:
            while batch_rsp["status"] in ["PENDING", "RUNNING"]:
                time.sleep(RESULT_POLLING_INTERVAL)
                batch_rsp, jobs_rsp = self._client._get_batch(batch_id)

            if fetch_results:
                batch_rsp, jobs_rsp = self._client._get_batch(
                    batch_id, fetch_results=True
                )
        batch = Batch(**batch_rsp, jobs=jobs_rsp, _client=self._client)

        self.batches[batch.id] = batch
        return batch

    def get_batch(self, id: str, fetch_results: bool = False) -> Batch:
        """Retrieve a batch's data and all its jobs.

        Args:
            id: ID of the batch.
            fetch_results: whether to download job results

        Returns:
            Batch: the batch stored in the PCS database.
        """

        batch_rsp, jobs_rsp = self._client._get_batch(id, fetch_results=fetch_results)
        batch = Batch(**batch_rsp, jobs=jobs_rsp, _client=self._client)
        self.batches[batch.id] = batch
        return batch

    def cancel_batch(self, id: str) -> Batch:
        """Cancel the given batch on the PCS

        Args:
            id: ID of the batch.
        """
        batch_rsp = self._client._cancel_batch(id)
        batch = Batch(**batch_rsp, _client=self._client)
        return batch

    def get_job(self, id: str, wait: bool = False) -> Job:
        """Retrieve a job's data.

        Args:
            id: ID of the job.
            wait: Whether to wait for the job to be done

        Returns:
            Job: the job stored in the PCS database.
        """
        job_rsp = self._client._get_job(id)
        if wait:
            while job_rsp["status"] in ["PENDING", "RUNNING"]:
                time.sleep(RESULT_POLLING_INTERVAL)
                job_rsp = self._client._get_job(id)
        job = Job(**job_rsp, _client=self._client)
        return job

    def cancel_job(self, id: str) -> Job:
        """Cancel the given job on the PCS

        Args:
            id: ID of the job.
        """
        job_rsp = self._client._cancel_job(id)
        job = Job(**job_rsp, _client=self._client)
        return job

    def get_device_specs_dict(self) -> Dict[str, str]:
        """Retrieve the list of available device specifications.

        Returns:
            DeviceSpecs: the list of available device specifications.
        """

        return self._client.get_device_specs_dict()
