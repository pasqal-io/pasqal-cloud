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

from typing import Dict

import requests

from sdk.endpoints import Endpoints
from sdk.errors import HTTPError

TIMEOUT = 30  # client http requests timeout after 30s


class Client:
    client_id: str
    client_secret: str

    _token: str

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        endpoints: Endpoints = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.endpoints = endpoints or Endpoints()

    def _login(self):
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

        self._token = data["data"]["token"]

    def _request(self, method: str, url: str, payload: Dict = None):
        headers = (
            {
                "content-type": "application/json",
                "authorization": f"Bearer {self._token}",
            },
        )

        rsp = requests.request(
            method,
            url,
            json=payload,
            timeout=TIMEOUT,
            headers=headers,
        ).json()
        # If account returns unauthorized we attempt to login and retry request
        if rsp.status_code == 401:
            self._login()
            rsp = requests.request(
                method,
                url,
                json=payload,
                headers=self._headers(),
                timeout=TIMEOUT,
            ).json

        if rsp.status_code >= 400:
            raise HTTPError(rsp)

        return rsp.json()
