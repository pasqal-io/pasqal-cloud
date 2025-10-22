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

import os
from getpass import getpass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union
from uuid import UUID

import requests
from requests.auth import AuthBase

from pasqal_cloud._version import __version__ as sdk_version
from pasqal_cloud.authentication import (
    Auth0TokenProvider,
    HTTPBearerAuthenticator,
    TokenProvider,
)
from pasqal_cloud.endpoints import Auth0Conf, Endpoints
from pasqal_cloud.utils.filters import (
    BatchFilters,
    CancelJobFilters,
    JobFilters,
    PaginationParams,
    RebatchFilters,
)
from pasqal_cloud.utils.jsend import JobResult, JSendPayload
from pasqal_cloud.utils.retry import retry_http_error

TIMEOUT = 30  # client http requests timeout after 30s


# Env variable to disable SSL verification. Should be used only in testing environement
def _skip_ssl_verify() -> bool:
    return bool(os.getenv("PASQAL_SKIP_SSL_VERIFY", False))


class Client:
    authenticator: AuthBase | None

    def __init__(
        self,
        project_id: str | None = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        token_provider: Optional[TokenProvider] = None,
        endpoints: Optional[Endpoints] = None,
        auth0: Optional[Auth0Conf] = None,
    ):
        self.endpoints = self._make_endpoints(endpoints)
        self._project_id = project_id
        self.user_agent = f"PasqalCloudSDK/{sdk_version}"

        if token_provider is not None:
            self._check_token_provider(token_provider)

        if username:
            auth0 = self._make_auth0(auth0)
            token_provider = self._credential_login(username, password, auth0)

        self.authenticator: Optional[HTTPBearerAuthenticator] = None
        if token_provider:
            self.authenticator = HTTPBearerAuthenticator(token_provider)

        self.session = requests.Session()
        self.session.verify = not _skip_ssl_verify()

    def _get_api_urls(self) -> Dict[str, str]:
        """Return a dictionary mapping API endpoint names to their URLs."""
        return {
            # Batch endpoints
            "send_batch": f"{self.endpoints.core}/api/v1/batches",
            "get_batch": f"{self.endpoints.core}/api/v2/batches/{{batch_id}}",
            "close_batch": f"{self.endpoints.core}/api/v2/"
            f"batches/{{batch_id}}/complete",
            "cancel_batch": f"{self.endpoints.core}/api/v2/"
            f"batches/{{batch_id}}/cancel",
            "cancel_batches": f"{self.endpoints.core}/api/v1/batches/cancel",
            "rebatch": f"{self.endpoints.core}/api/v1/batches/{{batch_id}}/rebatch",
            "get_batches": f"{self.endpoints.core}/api/v1/batches",
            "add_jobs": f"{self.endpoints.core}/api/v2/batches/{{batch_id}}/jobs",
            "set_batch_tags": f"{self.endpoints.core}/api/v1/batches/{{batch_id}}/tags",
            "cancel_jobs": f"{self.endpoints.core}/api/v2/batches/"
            f"{{batch_id}}/cancel/jobs",
            # Job endpoints
            "get_jobs": f"{self.endpoints.core}/api/v2/jobs",
            "get_job": f"{self.endpoints.core}/api/v2/jobs/{{job_id}}",
            "cancel_job": f"{self.endpoints.core}/api/v2/jobs/{{job_id}}/cancel",
            "get_job_results_link": f"{self.endpoints.core}/api/v1/"
            f"jobs/{{job_id}}/results_link",
            # Workload endpoints
            "send_workload": f"{self.endpoints.core}/api/v1/workloads",
            "get_workload": f"{self.endpoints.core}/api/v2/workloads/{{workload_id}}",
            "cancel_workload": f"{self.endpoints.core}/api/v1/"
            f"workloads/{{workload_id}}/cancel",
            # Device endpoints
            "get_devices_specs": f"{self.endpoints.core}/api/v1/devices/specs",
            "get_public_devices_specs": f"{self.endpoints.core}"
            f"/api/v1/devices/public-specs",
            # Project endpoints
            "get_all_active_projects": f"{self.endpoints.account}/api/v1/projects",
        }

    def _get_url(self, endpoint_name: str, **kwargs: Any) -> str:
        """Get the URL for a specific endpoint, with path parameters substituted.

        Args:
            endpoint_name: The name of the endpoint from _get_api_urls()
            **kwargs: Path parameters to substitute in the URL template
                      Possible parameters: batch_id, job_id, workload_id

        Returns:
            The formatted URL
        """
        urls = self._get_api_urls()
        if endpoint_name not in urls:
            raise ValueError(
                self.unknown_endpoint_message.format(endpoint=endpoint_name)
            )

        url_template = urls[endpoint_name]
        # Format the URL with any provided path parameters
        return url_template.format(**kwargs)

    @property
    def unknown_endpoint_message(self) -> str:
        return "Unknown endpoint: {endpoint}"

    def user_token(self) -> Union[str, None]:
        return (
            self.authenticator.token_provider.get_token()  # type: ignore[attr-defined]
            if self.authenticator
            else None
        )

    @property
    def project_id(self) -> str:
        if not self._project_id:
            raise ValueError("You need to set a project_id.")
        return self._project_id

    @project_id.setter
    def project_id(self, project_id: str) -> None:
        self._project_id = project_id

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

    def _request_with_status_check(self, *args: Any, **kwargs: Any):  # type: ignore
        resp = self.session.request(*args, **kwargs)
        resp.raise_for_status()
        return resp

    def _authenticated_request(
        self,
        method: str,
        url: str,
        payload: Optional[Union[Mapping, Sequence[Mapping], Sequence[str]]] = None,
        params: Optional[Mapping[str, Any]] = None,
    ) -> JSendPayload:
        if self.authenticator is None:
            raise ValueError(
                "Authentication required. Please provide your credentials when"
                " initializing the client."
            )

        headers = {
            "content-type": "application/json",
            "User-Agent": self.user_agent,
        }

        if method == "GET":
            request_with_retry = retry_http_error(
                max_retries=5,
                retry_status_code={408, 425, 429, 500, 502, 504},
                retry_exceptions=(requests.ConnectionError, requests.Timeout),  # type: ignore
            )(self._request_with_status_check)
        else:
            request_with_retry = retry_http_error(
                max_retries=5,
                retry_status_code={408, 425, 429, 500, 502, 504},
            )(self._request_with_status_check)

        resp = request_with_retry(
            method,
            url,
            json=payload,
            timeout=TIMEOUT,
            headers=headers,
            auth=self.authenticator,
            params=params,
        )
        data: JSendPayload = resp.json()
        return data

    def _request_all_pages(
        self,
        method: str,
        url: str,
        payload: Optional[Union[Mapping, Sequence[Mapping]]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Request all pages of a paginated endpoint and return a list of all items from
        the requested pages

        Args:
            method: HTTP method
            url: requested endpoint url
            payload: query payload
            params: query params

        Returns:
            A list of items from the requested pages.
        """

        if not params:
            params = {}
        first_page_response = self._authenticated_request(
            method=method, url=url, payload=payload, params=params
        )
        all_items: List[Dict] = first_page_response["data"]
        pagination_data = first_page_response.get("pagination")

        if not pagination_data:
            return all_items

        total_nb_items = pagination_data["total"]
        end = pagination_data["end"]
        while end < total_nb_items:
            params["offset"] = end
            response: JSendPayload = self._authenticated_request(
                method=method, url=url, payload=payload, params=params
            )

            all_items.extend(response["data"])
            pagination_data = response.get("pagination")

            # Added to make sure the type is correctly set for mypy
            # Should not happen
            if not pagination_data:
                break

            total_nb_items = pagination_data["total"]
            end = pagination_data["end"]
        return all_items

    def send_batch(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        batch_data.update({"project_id": self.project_id})
        response: Dict[str, Any] = self._authenticated_request(
            "POST",
            self._get_url("send_batch"),
            batch_data,
        )["data"]
        return response

    def get_batch(self, batch_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "GET", self._get_url("get_batch", batch_id=batch_id)
        )["data"]
        return response

    def get_batch_jobs(self, batch_id: str) -> list[Dict[str, Any]]:
        return self._request_all_pages(
            "GET",
            self._get_url("get_jobs"),
            params={
                "batch_id": batch_id,
                "order_by": "creation_order",
                "order_by_direction": "ASC",
            },
            # The order-by parameters are required to ensure that the jobs appear in
            # the same order as they do in the GET /batches/{id} response
        )

    @retry_http_error(max_retries=5, retry_exceptions=(requests.ConnectionError,))
    def _download_results(self, results_link: str) -> JobResult:
        response = self.session.request("GET", results_link)
        response.raise_for_status()
        data = response.json()
        return JobResult(
            raw=data.pop("raw", None),
            counter=data.pop("counter", None),
            serialised_results=data.pop("serialised_results", None),
            **data
        )

    def get_job_results(self, job_id: str) -> Optional[JobResult]:
        """
        Download job result from S3.

        This function request a presigned-url for a specific job_id from the core API.
        Once the presigned-url is obtained, it downloads the result from S3.
        """
        results_link = self._authenticated_request(
            "GET", self._get_url("get_job_results_link", job_id=job_id)
        )["data"]["results_link"]
        if results_link:
            return self._download_results(results_link)
        return None

    def close_batch(self, batch_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "PATCH", self._get_url("close_batch", batch_id=batch_id)
        )["data"]
        return response

    def cancel_batch(self, batch_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "PATCH", self._get_url("cancel_batch", batch_id=batch_id)
        )["data"]
        return response

    def cancel_batches(self, batch_ids: List[str]) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "PATCH",
            self._get_url("cancel_batches"),
            payload={"batch_ids": batch_ids},
        )["data"]
        return response

    def rebatch(
        self, batch_id: Union[UUID, str], filters: RebatchFilters
    ) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "POST",
            self._get_url("rebatch", batch_id=batch_id),
            params=filters.model_dump(exclude_unset=True),
        )["data"]
        return response

    def get_jobs(
        self, filters: JobFilters, pagination_params: PaginationParams
    ) -> JSendPayload:
        filters_params = filters.model_dump(exclude_unset=True)
        filters_params.update(pagination_params.model_dump())
        response: JSendPayload = self._authenticated_request(
            "GET",
            self._get_url("get_jobs"),
            params=filters_params,
        )
        return response

    def get_batches(
        self, filters: BatchFilters, pagination_params: PaginationParams
    ) -> JSendPayload:
        filters_params = filters.model_dump(exclude_unset=True)
        filters_params.update(pagination_params.model_dump())
        response: JSendPayload = self._authenticated_request(
            "GET",
            self._get_url("get_batches"),
            params=filters_params,
        )
        return response

    def add_jobs(
        self, batch_id: str, jobs_data: Sequence[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "POST", self._get_url("add_jobs", batch_id=batch_id), jobs_data
        )["data"]
        return response

    def get_job(self, job_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "GET", self._get_url("get_job", job_id=job_id)
        )["data"]
        return response

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "PATCH", self._get_url("cancel_job", job_id=job_id)
        )["data"]
        return response

    def cancel_jobs(
        self, batch_id: Union[UUID, str], filters: CancelJobFilters
    ) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "PATCH",
            self._get_url("cancel_jobs", batch_id=batch_id),
            params=filters.model_dump(exclude_unset=True),
        )["data"]
        return response

    def send_workload(self, workload_data: Dict[str, Any]) -> Dict[str, Any]:
        workload_data.update({"project_id": self.project_id})
        response: Dict[str, Any] = self._authenticated_request(
            "POST",
            self._get_url("send_workload"),
            workload_data,
        )["data"]
        return response

    def get_workload(self, workload_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "GET", self._get_url("get_workload", workload_id=workload_id)
        )["data"]
        return response

    def cancel_workload(self, workload_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "PUT", self._get_url("cancel_workload", workload_id=workload_id)
        )["data"]
        return response

    def get_device_specs_dict(self) -> Dict[str, str]:
        if self.authenticator is not None:
            response: Dict[str, str] = self._authenticated_request(
                "GET", self._get_url("get_devices_specs")
            )["data"]
            return response
        return self.get_public_device_specs()

    def get_public_device_specs(self) -> Dict[str, str]:
        response = self.session.request(
            "GET",
            self._get_url("get_public_devices_specs"),
        )
        response.raise_for_status()
        devices = response.json()["data"]
        return {device["device_type"]: device["specs"] for device in devices}

    def set_batch_tags(
        self,
        batch_id: str,
        tags: list[str],
    ) -> Dict[str, str]:
        response: Dict[str, Any] = self._authenticated_request(
            "PATCH",
            self._get_url("set_batch_tags", batch_id=batch_id),
            tags,
        )["data"]
        return response

    def get_all_active_projects(
        self,
    ) -> List[Dict[str, Any]]:
        response: List[Dict[str, Any]] = self._authenticated_request(
            "GET",
            self._get_url("get_all_active_projects"),
            params={"project_status": "ACTIVE"},
        )["data"]
        return response
