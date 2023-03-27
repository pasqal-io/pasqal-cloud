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

from abc import abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from jwt import decode, DecodeError
from requests import PreparedRequest
from requests.auth import AuthBase

from sdk.endpoints import Endpoints
from sdk.errors import HTTPError
from sdk.utils.jsend import JSendPayload

TIMEOUT = 30  # client http requests timeout after 30s


class HTTPBearerAuthenticator(AuthBase):
    def __init__(self, token_provider: Optional[TokenProvider]):
        if not token_provider:
            raise Exception("The authenticator needs a token provider.")
        self.token_provider = token_provider

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        r.headers["Authorization"] = f"Bearer {self.token_provider.get_token()}"
        return r


class TokenProviderError(Exception):
    pass


class TokenProvider:
    __token_cache: Optional[tuple[datetime, str]] = None
    expiry_window: timedelta = timedelta(minutes=1.0)

    @abstractmethod
    def _query_token(self) -> dict[str, Any]:
        raise NotImplementedError

    def get_token(self) -> str:
        if self.__token_cache:
            expiry, token = self.__token_cache
            if expiry - self.expiry_window > datetime.now(tz=timezone.utc):
                return token

        self.__token_cache = self._refresh_token_cache()
        return self.__token_cache[1]

    def _refresh_token_cache(self) -> tuple[datetime, str]:
        try:
            token_response = self._query_token()
            expiry = self._extract_expiry(token_response)

            if expiry is None:
                expiry = datetime.now(tz=timezone.utc)

            return (expiry, token_response["access_token"])
        except HTTPError as err:
            raise TokenProviderError(err)

    @staticmethod
    def _extract_expiry(token_response: dict[str, Any]) -> datetime | None:
        """Extracts the expiry datetime from the token response.

        Assumes that the actual token provided is correct, but might be in an
        unexpected format

        Args:
            token_response: A valid token response dictionary.

        Returns:
            The time the token will expire, or None if it can't be calculated
        """
        expires_in = token_response.get("expires_in", None)
        if expires_in:
            return datetime.now(tz=timezone.utc) + timedelta(seconds=float(expires_in))

        try:
            # We assume the token is valid, but might not be in an expected format
            token = token_response.get("access_token")

            if isinstance(token, str) and "." in token:
                token_timestamp = decode(
                    token,
                    algorithms=["HS256"],
                    options={"verify_signature": False},
                ).get("exp")
                if token_timestamp:
                    return datetime.fromtimestamp(token_timestamp, tz=timezone.utc)

        except DecodeError:
            # The token is not in a format that could be parsed as a JWT
            pass
        return None


class UsernamePasswordTokenProvider(TokenProvider):
    def __init__(self, username: str, password: str, login_url: str):
        self.username = username
        self.password = password
        self.login_url = login_url

    def _query_token(self) -> Dict[str, Any]:
        payload = {
            "email": self.username,
            "password": self.password,
            "type": "user",
        }

        rsp = requests.post(
            self.login_url,
            json=payload,
            timeout=TIMEOUT,
            headers={"content-type": "application/json"},
        )
        data = rsp.json()["data"]

        if rsp.status_code >= 400:
            raise HTTPError(data)

        return {"access_token": data["token"]}


class Client:
    authenticator: AuthBase

    def __init__(
        self,
        group_id: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        token_provider: Optional[TokenProvider] = None,
        endpoints: Optional[Endpoints] = None,
    ):
        if not (username and password) and not token_provider:
            raise Exception(
                "At least a username/password combination or"
                "TokenProvider object should be provided."
            )
        self.endpoints = endpoints or Endpoints()
        self.group_id = group_id

        if username and password:
            token_provider = UsernamePasswordTokenProvider(
                username, password, f"{self.endpoints.account}/api/v1/auth/login"
            )

        self.authenticator = HTTPBearerAuthenticator(token_provider)

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
