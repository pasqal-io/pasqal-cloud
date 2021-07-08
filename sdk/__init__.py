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

from sdk.client import Client
from sdk.endpoints import Endpoints


class SDK:
    _client: Client

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        endpoints: Endpoints = None,
    ):
        self._client = Client(client_id, client_secret, endpoints)
