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

from pasqal_cloud.authentication import (
    TokenProvider,
)
from pasqal_cloud.client import Client
from pasqal_cloud.endpoints import Auth0Conf, Endpoints

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
    def batch_endpoint_url(self) -> str:
        return f"{self.endpoints.core}/api/v1/third-party-access/ovh/batches"

    def send_batch(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        response: Dict[str, Any] = self._authenticated_request(
            "POST",
            self.batch_endpoint_url,
            batch_data,
        )["data"]
        return response
