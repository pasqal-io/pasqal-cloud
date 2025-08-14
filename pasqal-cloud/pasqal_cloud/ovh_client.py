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

from typing import Any, Dict, Optional

from requests.auth import AuthBase

from pasqal_cloud import JobFilters, PaginationParams
from pasqal_cloud.authentication import (
    TokenProvider,
)
from pasqal_cloud.client import Client
from pasqal_cloud.endpoints import Auth0Conf, Endpoints
from pasqal_cloud.utils.jsend import JobResult, JSendPayload

TIMEOUT = 30  # client http requests timeout after 30s


class EmptyFilter:
    pass


class OvhClient(Client):
    authenticator: AuthBase | None

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        token_provider: Optional[TokenProvider] = None,
        endpoints: Optional[Endpoints] = None,
        auth0: Optional[Auth0Conf] = None,
        project_id: Optional[str] = None,
    ):
        super().__init__(
            project_id=project_id,
            username=username,
            password=password,
            token_provider=token_provider,
            endpoints=endpoints,
            auth0=auth0,
        )

    @property
    def project_id(self) -> str:
        """
        Override property of class Client to prevent
        ValueError to be raised as OVH does not need
        a project_id
        """
        return ""

    @project_id.setter
    def project_id(self, _project_id: str) -> None:
        self._project_id = ""

    @property
    def ovh_endpoint_url(self) -> str:
        return f"{self.endpoints.core}/api/v1/third-party-access/ovh"

    def send_batch(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "POST",
            f"{self.ovh_endpoint_url}/batches",
            batch_data,
        )["data"]
        return response

    def get_batch(self, batch_id: str) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "GET", f"{self.ovh_endpoint_url}/batches/{batch_id}"
        )["data"]
        return response

    def get_batch_jobs(self, batch_id: str) -> list[Dict[str, Any]]:
        return self._request_all_pages(
            "GET",
            f"{self.ovh_endpoint_url}/jobs",
            params={
                "batch_id": batch_id,
                "order_by": "created_at",
                "order_by_direction": "ASC",
            },
        )

    def get_jobs(
        self, filters: JobFilters, pagination_params: PaginationParams
    ) -> JSendPayload:
        filters_params = filters.model_dump(exclude_unset=True)
        filters_params.update(pagination_params.model_dump())
        response: JSendPayload = self._authenticated_request(
            "GET",
            f"{self.ovh_endpoint_url}/jobs",
            params=filters_params,
        )
        return response

    def get_job_results(self, job_id: str) -> Optional[JobResult]:
        results_link = self._authenticated_request(
            "GET", f"{self.ovh_endpoint_url}/jobs/{job_id}/results_link"
        )["data"]["results_link"]
        if results_link:
            return self._download_results(results_link)
        return None

    def get_device_specs_dict(self) -> Dict[str, str]:
        return self.get_public_device_specs()
