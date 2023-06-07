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
from sys import version_info

from dataclasses import dataclass

if version_info[:2] >= (3, 8):
    from typing import Final
else:
    from typing_extensions import Final  # type: ignore


# ---- Endpoints ----

PROD_CORE_API_URL: Final[str] = "https://apis.pasqal.cloud/core-fast"
PREPROD_CORE_API_URL: Final[str] = "https://apis.preprod.pasqal.cloud/core-fast"
DEV_CORE_API_URL: Final[str] = "https://apis.dev.pasqal.cloud/core-fast"


@dataclass
class Endpoints:
    core: str = PROD_CORE_API_URL


# ---- Auth0 ----

PROD_AUTH0_DOMAIN: Final[str] = "pasqal.eu.auth0.com"
PROD_PUBLIC_CLIENT_ID: Final[str] = "PeZvo7Atx7IVv3iel59asJSb4Ig7vuSB"
PROD_AUDIENCE: Final[str] = "https://apis.pasqal.cloud/account/api/v1"

PREPROD_AUTH0_DOMAIN: Final[str] = "pasqal-preprod.eu.auth0.com"
PREPROD_PUBLIC_CLIENT_ID: Final[str] = "2l6A2ldvwJE5sdkghu40BTYLm7sSUAv9"
PREPROD_AUDIENCE: Final[str] = "https://apis.preprod.pasqal.cloud/account/api/v1"

DEV_AUTH0_DOMAIN: Final[str] = "pasqal-dev.eu.auth0.com"
DEV_PUBLIC_CLIENT_ID: Final[str] = "5QtfSu1UV118Iz6By6IJRSNoDrLbAiOv"
DEV_AUDIENCE: Final[str] = "https://apis.dev.pasqal.cloud/account/api/v1"

REALM: Final[str] = "pcs-users"


@dataclass
class Auth0Conf:
    domain: str = PROD_AUTH0_DOMAIN
    public_client_id: str = PROD_PUBLIC_CLIENT_ID
    audience: str = PROD_AUDIENCE
    realm: str = REALM


# ---- Pre-made environment configuration ----


PASQAL_ENDPOINTS = {
    "prod": Endpoints(core=PROD_CORE_API_URL),
    "preprod": Endpoints(core=PREPROD_CORE_API_URL),
    "dev": Endpoints(core=DEV_CORE_API_URL),
}

AUTH0_CONFIG = {
    "prod": Auth0Conf(
        domain=PROD_AUTH0_DOMAIN,
        public_client_id=PROD_PUBLIC_CLIENT_ID,
        audience=PROD_AUDIENCE,
        realm=REALM,
    ),
    "preprod": Auth0Conf(
        domain=PREPROD_AUTH0_DOMAIN,
        public_client_id=PREPROD_PUBLIC_CLIENT_ID,
        audience=PREPROD_AUDIENCE,
        realm=REALM,
    ),
    "dev": Auth0Conf(
        domain=DEV_AUTH0_DOMAIN,
        public_client_id=DEV_PUBLIC_CLIENT_ID,
        audience=DEV_AUDIENCE,
        realm=REALM,
    ),
}
