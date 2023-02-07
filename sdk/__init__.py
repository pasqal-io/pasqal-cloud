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

from sdk.batch import Batch, RESULT_POLLING_INTERVAL
from sdk.client import Client
from sdk.endpoints import Endpoints
from sdk.job import Job
from sdk.device.configuration import BaseConfig
from sdk.device.device_types import DeviceType


class SDK:
    _client: Client

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        endpoints: Optional[Endpoints] = None,
        webhook: Optional[str] = None,
    ):
        self._client = Client(client_id, client_secret, endpoints)
        self.batches: Dict[str, Batch] = {}
        self.webhook = webhook

    def create_batch(
        self,
        serialized_sequence: str,
        jobs: List[Dict[str, Any]],
        device_type: DeviceType = DeviceType.QPU,
        configuration: Optional[BaseConfig] = None,
        wait: bool = False,
        fetch_results: bool = False,
    ) -> Batch:
        """Create a new batch and send it to the API.
        For Iroise MVP, the batch must contain at least one job and will be declared as complete immediately.

        Args:
            serialized_sequence: Serialized pulser sequence.
            jobs: List of jobs to be added to the batch at creation. (#TODO: Make optional after Iroise MVP)
            device_type: The type of device to use, either an emulator or a QPU
              If set to QPU, the device_type will be set to the one
              stored in the serialized sequence
            configuration: A dictionary with extra configuration for the emulators that accept it.
            wait: Whether to wait for the batch to be done
            fetch_results: Whether to download the results. Implies waiting for the batch.


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
        if device_type != DeviceType.QPU:
            req.update({"emulator": device_type})

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
        batch = Batch(**batch_rsp, _client=self._client)
        for job_rsp in jobs_rsp:
            batch.jobs[job_rsp["id"]] = Job(**job_rsp)

        self.batches[batch.id] = batch
        return batch

    def get_batch(self, id: str, fetch_results: bool = False) -> Batch:
        """Retrieve a batch's data and all its jobs.

        Args:
            id: Id of the batch.
            fetch_results: whether to download job results

        Returns:
            Batch: the batch stored in the PCS database.
        """

        batch_rsp, jobs_rsp = self._client._get_batch(id, fetch_results=fetch_results)
        batch = Batch(**batch_rsp, _client=self._client)
        for job_rsp in jobs_rsp:
            batch.jobs[job_rsp["id"]] = Job(**job_rsp)
        self.batches[batch.id] = batch
        return batch
