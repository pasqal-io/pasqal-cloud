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
from __future__ import annotations

import time
from datetime import datetime
from getpass import getpass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

import requests
from requests.auth import AuthBase

from pasqal_cloud.authentication import (
    Auth0TokenProvider,
    HTTPBearerAuthenticator,
    TokenProvider,
)
from pasqal_cloud.endpoints import Auth0Conf, Endpoints
from pasqal_cloud.utils.jsend import JSendPayload

TIMEOUT = 30  # client http requests timeout after 30s


class EmptyFilter:
    pass


class Client:
    authenticator: AuthBase

    def __init__(
        self,
        project_id: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        token_provider: Optional[TokenProvider] = None,
        endpoints: Optional[Endpoints] = None,
        auth0: Optional[Auth0Conf] = None,
    ):
        if not username and not token_provider:
            raise ValueError(
                "At least a username or TokenProvider object should be provided."
            )
        if token_provider is not None:
            self._check_token_provider(token_provider)

        self.endpoints = self._make_endpoints(endpoints)

        if username:
            auth0 = self._make_auth0(auth0)
            token_provider = self._credential_login(username, password, auth0)

        self.authenticator = HTTPBearerAuthenticator(token_provider)
        self.project_id = project_id

    @staticmethod
    def _make_endpoints(endpoints: Optional[Endpoints]) -> Endpoints:
        if endpoints is None:
            return Endpoints()

        if not isinstance(endpoints, Endpoints):
            raise TypeError(f"endpoints must be a {Endpoints.__name__} instance")

        return endpoints

    @staticmethod
    def _make_auth0(auth0: Optional[Auth0Conf]) -> Auth0Conf:
        if auth0 is None:
            return Auth0Conf()

        if not isinstance(auth0, Auth0Conf):
            raise TypeError(f"auth0 parameter must be a {Auth0Conf.__name__} instance")

        return auth0

    @staticmethod
    def _check_token_provider(token_provider: TokenProvider) -> None:
        if not isinstance(token_provider, TokenProvider):
            raise TypeError("token_provider must be an instance of TokenProvider.")

    def _credential_login(
        self, username: str, password: Optional[str], auth0: Auth0Conf
    ) -> TokenProvider:
        if not password:
            password = getpass("Enter your password:")
            #   We want to allow an empty string at first, but then
            #   it results in an error
            if not password:
                raise ValueError("The prompted password should not be empty")

        token_provider: TokenProvider = Auth0TokenProvider(username, password, auth0)
        return token_provider

    def _request(
        self,
        method: str,
        url: str,
        payload: Optional[Union[Mapping, Sequence[Mapping]]] = None,
        params: Optional[Mapping[str, Any]] = None,
    ) -> JSendPayload:
        max_retries = (
            5  # HTTP client will raise an exception after too many consecutive fails
        )
        successful_request: bool = False
        iteration: int = 0
        while iteration <= max_retries and not successful_request:
            # time = (interval seconds * exponent rule) ^ retries
            delay = (1 * 2) ** iteration
            rsp = requests.request(
                method,
                url,
                json=payload,
                timeout=TIMEOUT,
                headers={"content-type": "application/json"},
                auth=self.authenticator,
                params=params,
            )
            try:
                rsp.raise_for_status()
                successful_request = True
            except Exception as e:
                if (
                    rsp.status_code not in {408, 425, 429, 500, 502, 503, 504}
                    or iteration == max_retries
                ):
                    raise e

            if successful_request:
                data: JSendPayload = rsp.json()
                return data

            time.sleep(delay)
            iteration += 1

        # There is no scenario where we want to reach this
        # so we can raise a generic Exception
        raise Exception(
            "HTTP Client has encountered an issue it is unable to recover from."
        )

    def send_batch(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        batch_data.update({"project_id": self.project_id})
        response: Dict[str, Any] = self._request(
            "POST",
            f"{self.endpoints.core}/api/v1/batches",
            batch_data,
        )["data"]
        return response

    def get_batch(self, batch_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._request(
            "GET", f"{self.endpoints.core}/api/v1/batches/{batch_id}"
        )["data"]
        return response

    def complete_batch(self, batch_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._request(
            "PUT", f"{self.endpoints.core}/api/v1/batches/{batch_id}/complete"
        )["data"]
        return response

    def cancel_batch(self, batch_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._request(
            "PUT", f"{self.endpoints.core}/api/v1/batches/{batch_id}/cancel"
        )["data"]
        return response

    def rebatch(
        self,
        batch_id: str,
        job_ids: Union[List[str], EmptyFilter],
        status: Union[List[str], EmptyFilter],
        min_runs: Union[int, EmptyFilter],
        max_runs: Union[int, EmptyFilter],
        start_date: Union[datetime, EmptyFilter],
        end_date: Union[datetime, EmptyFilter],
    ) -> Dict[str, Any]:
        query_params: dict[str, str | list[str]] = {}
        if not isinstance(job_ids, EmptyFilter):
            query_params["id"] = job_ids
        if not isinstance(status, EmptyFilter):
            query_params["status"] = status
        if not isinstance(min_runs, EmptyFilter):
            query_params["min_runs"] = str(min_runs)
        if not isinstance(max_runs, EmptyFilter):
            query_params["max_runs"] = str(max_runs)
        if not isinstance(start_date, EmptyFilter):
            query_params["start_date"] = start_date.isoformat()
        if not isinstance(end_date, EmptyFilter):
            query_params["end_date"] = end_date.isoformat()

        response: Dict[str, Any] = self._request(
            "POST",
            f"{self.endpoints.core}/api/v1/batches/{batch_id}/rebatch",
            params=query_params,
        )["data"]
        return response

    def add_jobs(
        self, batch_id: str, jobs_data: Sequence[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        response: Dict[str, Any] = self._request(
            "POST", f"{self.endpoints.core}/api/v1/batches/{batch_id}/jobs", jobs_data
        )["data"]
        return response

    def get_job(self, job_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._request(
            "GET", f"{self.endpoints.core}/api/v1/jobs/{job_id}"
        )["data"]
        return response

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._request(
            "PUT", f"{self.endpoints.core}/api/v1/jobs/{job_id}/cancel"
        )["data"]
        return response

    def send_workload(self, workload_data: Dict[str, Any]) -> Dict[str, Any]:
        workload_data.update({"project_id": self.project_id})
        response: Dict[str, Any] = self._request(
            "POST",
            f"{self.endpoints.core}/api/v1/workloads",
            workload_data,
        )["data"]
        return response

    def get_workload(self, workload_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._request(
            "GET", f"{self.endpoints.core}/api/v2/workloads/{workload_id}"
        )["data"]
        return response

    def cancel_workload(self, workload_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._request(
            "PUT", f"{self.endpoints.core}/api/v1/workloads/{workload_id}/cancel"
        )["data"]
        return response

    def get_device_specs_dict(self) -> Dict[str, str]:
        response: Dict[str, str] = self._request(
            "GET", f"{self.endpoints.core}/api/v1/devices/specs"
        )["data"]
        return response
