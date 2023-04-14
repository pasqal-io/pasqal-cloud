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

from getpass import getpass
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.auth import AuthBase

from pasqal_cloud.authentication import (
    TokenProvider,
    Auth0TokenProvider,
    HTTPBearerAuthenticator,
)
from pasqal_cloud.endpoints import Endpoints, Auth0Conf
from pasqal_cloud.errors import HTTPError
from pasqal_cloud.utils.jsend import JSendPayload

TIMEOUT = 30  # client http requests timeout after 30s


class Client:
    authenticator: AuthBase

    def __init__(
        self,
        group_id: str,
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
        self.group_id = group_id

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
        self, method: str, url: str, payload: Optional[Dict[str, Any]] = None
    ) -> JSendPayload:
        rsp = requests.request(
            method,
            url,
            json=payload,
            timeout=TIMEOUT,
            headers={"content-type": "application/json"},
            auth=self.authenticator,
        )
        data: JSendPayload = rsp.json()
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

    def get_device_specs_dict(self) -> Dict[str, str]:
        device_specs: Dict[str, str] = self._request(
            "GET", f"{self.endpoints.core}/api/v1/devices/specs"
        )["data"]
        return device_specs
