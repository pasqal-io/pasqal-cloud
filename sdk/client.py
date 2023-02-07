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

from typing import Any, Dict, List, Optional, Tuple

import requests

from sdk.endpoints import Endpoints
from sdk.errors import HTTPError
from sdk.utils.jsend import JSendPayload

TIMEOUT = 30  # client http requests timeout after 30s


class Client:
    client_id: str
    client_secret: str

    _token: str

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        endpoints: Optional[Endpoints] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.endpoints = endpoints or Endpoints()
        self.group_id = None
        self._token = ""
        self._fetch_group_id()

    def _fetch_group_id(self) -> None:
        url = f"{self.endpoints.account}/api/v1/auth/info"
        data = self._request(
            "GET",
            url,
        )
        self.group_id = data["data"]["group_id"]

    def _login(self) -> None:
        url = f"{self.endpoints.account}/api/v1/auth/login"
        payload = {
            "type": "api_key",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        rsp = requests.post(
            url,
            json=payload,
            timeout=TIMEOUT,
            headers={"content-type": "application/json"},
        )
        data = rsp.json()

        if rsp.status_code >= 400:
            raise HTTPError(data)

        self._token = data["token"]

    def _headers(self) -> Dict[str, str]:
        return {
            "content-type": "application/json",
            "authorization": f"Bearer {self._token}",
        }

    def _request(
        self, method: str, url: str, payload: Optional[Dict[str, Any]] = None
    ) -> JSendPayload:
        rsp = requests.request(
            method,
            url,
            json=payload,
            timeout=TIMEOUT,
            headers=self._headers(),
        )
        data: JSendPayload = rsp.json()
        # If account returns unauthorized we attempt to login and retry request
        if rsp.status_code == 401:
            self._login()
            rsp = requests.request(
                method,
                url,
                json=payload,
                headers=self._headers(),
                timeout=TIMEOUT,
            )
            data = rsp.json()

        if rsp.status_code >= 400:
            raise HTTPError(data)

        return data

    def _send_batch(
        self, batch_data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        batch_data.update({"group_id": self.group_id})
        batch_data = self._request(
            "POST",
            f"{self.endpoints.core}/api/v1/batches",
            batch_data,
        )["data"]
        jobs_data = batch_data.pop("jobs", [])
        return batch_data, jobs_data

    def _complete_batch(self, batch_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._request(
            "PUT", f"{self.endpoints.core}/api/v1/batches/{batch_id}/complete"
        )["data"]
        return response

    def _send_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        response: Dict[str, Any] = self._request(
            "POST", f"{self.endpoints.core}/api/v1/jobs", job_data
        )["data"]
        return response

    def _get_batch(
        self, id: str, fetch_results: bool = False
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        batch_data: Dict[str, Any] = self._request(
            "GET", f"{self.endpoints.core}/api/v1/batches/{id}"
        )["data"]
        jobs_data = batch_data.pop("jobs", [])
        if fetch_results:
            results = self._request(
                "GET", f"{self.endpoints.core}/api/v1/batches/{id}/results"
            )["data"]
            for job_data in jobs_data:
                job_data["result"] = results.get(str(job_data["id"]), None)
        return batch_data, jobs_data

    def _get_job(self, job_id: str) -> Dict[str, Any]:
        job: Dict[str, Any] = self._request(
            "GET", f"{self.endpoints.core}/api/v1/jobs/{job_id}"
        )["data"]
        return job
