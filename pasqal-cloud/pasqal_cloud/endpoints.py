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
from dataclasses import dataclass
from sys import version_info
from typing import Literal

if version_info[:2] >= (3, 8):
    from typing import Final
else:
    from typing_extensions import Final  # type: ignore[assignment]


Region = Literal["france", "saudi-arabia"]

# ---- Endpoints ----

# Region = France
# -- Prod --
CORE_API_URL: Final[str] = "https://apis.pasqal.cloud/core-fast"

ACCOUNT_API_URL: Final[str] = "https://apis.pasqal.cloud/account"

# -- Preprod --
PREPROD_CORE_API_URL: Final[str] = "https://apis.preprod.pasqal.cloud/core-fast"

PREPROD_ACCOUNT_API_URL: Final[str] = "https://apis.preprod.pasqal.cloud/account"

# -- Dev --
DEV_CORE_API_URL: Final[str] = "https://apis.dev.pasqal.cloud/core-fast"

DEV_ACCOUNT_API_URL: Final[str] = "https://apis.dev.pasqal.cloud/account"

# Region = Saudi-Arabia

# -- Prod --
KSA_CORE_API_URL: Final[str] = "https://apis.sa.pasqal.cloud/core-fast"

KSA_ACCOUNT_API_URL: Final[str] = "https://apis.sa.pasqal.cloud/account"

# -- Preprod --
KSA_PREPROD_CORE_API_URL: Final[str] = "https://apis.preprod.sa.pasqal.cloud/core-fast"

KSA_PREPROD_ACCOUNT_API_URL: Final[str] = "https://apis.preprod.sa.pasqal.cloud/account"


@dataclass
class Endpoints:
    core: str = CORE_API_URL
    account: str = ACCOUNT_API_URL

    @classmethod
    def from_region(cls, region: Region) -> "Endpoints":
        if region == "saudi-arabia":
            return Endpoints(core=KSA_CORE_API_URL, account=KSA_ACCOUNT_API_URL)
        return Endpoints()


# ---- Auth0 ----

# Prod Auth0 configuration
AUTH0_DOMAIN: Final[str] = "authenticate.pasqal.cloud"
AUTH0_TOKEN_ENDPOINT: Final[str] = "https://pasqal.eu.auth0.com/oauth/token"
PUBLIC_CLIENT_ID: Final[str] = "PeZvo7Atx7IVv3iel59asJSb4Ig7vuSB"
AUDIENCE: Final[str] = "https://apis.pasqal.cloud/account/api/v1"

PREPROD_AUTH0_DOMAIN: Final[str] = "authenticate.preprod.pasqal.cloud"
PREPROD_AUTH0_TOKEN_ENDPOINT: Final[str] = (
    "https://pasqal-preprod.eu.auth0.com/oauth/token"
)
PREPROD_PUBLIC_CLIENT_ID: Final[str] = "2l6A2ldvwJE5sdkghu40BTYLm7sSUAv9"
PREPROD_AUDIENCE: Final[str] = "https://apis.preprod.pasqal.cloud/account/api/v1"

DEV_AUTH0_DOMAIN: Final[str] = "authenticate.dev.pasqal.cloud"
DEV_AUTH0_TOKEN_ENDPOINT: Final[str] = "https://pasqal-dev.eu.auth0.com/oauth/token"
DEV_PUBLIC_CLIENT_ID: Final[str] = "5QtfSu1UV118Iz6By6IJRSNoDrLbAiOv"
DEV_AUDIENCE: Final[str] = "https://apis.dev.pasqal.cloud/account/api/v1"

REALM: Final[str] = "pcs-users"

# ---- Keycloak ----
SA_KEYCLOAK_BASE_URL = "https://auth.sa.pasqal.cloud"
SA_KEYCLOAK_TOKEN_ENDPOINT = (
    "https://auth.sa.pasqal.cloud/realms/pasqal-cloud/protocol/openid-connect/token"
)

PREPROD_SA_KEYCLOAK_BASE_URL = "https://auth.preprod.sa.pasqal.cloud/"
PREPROD_SA_KEYCLOAK_TOKEN_ENDPOINT = "https://auth.preprod.sa.pasqal.cloud/realms/pasqal-cloud/protocol/openid-connect/token"

KEYCLOAK_SDK_CLIENT_ID = "cloud-sdk"
KEYCLOAK_REALM = "pasqal-cloud"


@dataclass
class Auth0Conf:
    domain: str = AUTH0_DOMAIN
    public_client_id: str = PUBLIC_CLIENT_ID
    audience: str = AUDIENCE
    realm: str = REALM


@dataclass
class KeycloakConf:
    base_url: str = SA_KEYCLOAK_BASE_URL
    public_client_id: str = KEYCLOAK_SDK_CLIENT_ID
    realm: str = KEYCLOAK_REALM


@dataclass
class TokenProviderConf:
    token_endpoint: str
    public_client_id: str
    audience: str
    realm: str
    grant_type: str

    @classmethod
    def from_region(cls, region: Region) -> "TokenProviderConf":
        if region == "saudi-arabia":
            return TokenProviderConf(
                token_endpoint=SA_KEYCLOAK_TOKEN_ENDPOINT,
                public_client_id=KEYCLOAK_SDK_CLIENT_ID,
                audience=AUDIENCE,
                realm=KEYCLOAK_REALM,
                grant_type="password",
            )
        return TokenProviderConf(
            token_endpoint=AUTH0_TOKEN_ENDPOINT,
            public_client_id=PUBLIC_CLIENT_ID,
            audience=AUDIENCE,
            realm=REALM,
            grant_type="http://auth0.com/oauth/grant-type/password-realm",
        )


# ---- Pre-filled environment configuration ----


PASQAL_ENDPOINTS = {
    "prod": Endpoints(core=CORE_API_URL, account=ACCOUNT_API_URL),
    "preprod": Endpoints(core=PREPROD_CORE_API_URL, account=PREPROD_ACCOUNT_API_URL),
    "dev": Endpoints(core=DEV_CORE_API_URL, account=DEV_ACCOUNT_API_URL),
    "sa-prod": Endpoints(core=KSA_CORE_API_URL, account=KSA_ACCOUNT_API_URL),
    "sa-preprod": Endpoints(
        core=KSA_PREPROD_CORE_API_URL, account=KSA_PREPROD_ACCOUNT_API_URL
    ),
}

AUTH0_CONFIG = {
    "prod": Auth0Conf(
        domain=AUTH0_DOMAIN,
        public_client_id=PUBLIC_CLIENT_ID,
        audience=AUDIENCE,
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

AUTH_CONFIG = {
    "fr-prod": TokenProviderConf(
        token_endpoint=AUTH0_TOKEN_ENDPOINT,
        public_client_id=PUBLIC_CLIENT_ID,
        audience=AUDIENCE,
        realm=REALM,
        grant_type="http://auth0.com/oauth/grant-type/password-realm",
    ),
    "fr-preprod": TokenProviderConf(
        token_endpoint=PREPROD_AUTH0_TOKEN_ENDPOINT,
        public_client_id=PREPROD_PUBLIC_CLIENT_ID,
        audience=PREPROD_AUDIENCE,
        realm=REALM,
        grant_type="http://auth0.com/oauth/grant-type/password-realm",
    ),
    "fr-dev": TokenProviderConf(
        token_endpoint=DEV_AUTH0_TOKEN_ENDPOINT,
        public_client_id=DEV_PUBLIC_CLIENT_ID,
        audience=DEV_AUDIENCE,
        realm=REALM,
        grant_type="http://auth0.com/oauth/grant-type/password-realm",
    ),
    "sa-prod": TokenProviderConf(
        token_endpoint=SA_KEYCLOAK_TOKEN_ENDPOINT,
        public_client_id=KEYCLOAK_SDK_CLIENT_ID,
        audience=AUDIENCE,
        realm=KEYCLOAK_REALM,
        grant_type="password",
    ),
    "sa-preprod": TokenProviderConf(
        token_endpoint=PREPROD_SA_KEYCLOAK_TOKEN_ENDPOINT,
        public_client_id=KEYCLOAK_SDK_CLIENT_ID,
        audience=PREPROD_AUDIENCE,
        realm=KEYCLOAK_REALM,
        grant_type="password",
    ),
}
