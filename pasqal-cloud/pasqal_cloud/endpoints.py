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
import os
from dataclasses import dataclass
from sys import version_info
from typing import cast, get_args, Literal, Optional

if version_info[:2] >= (3, 8):
    from typing import Final
else:
    from typing_extensions import Final  # type: ignore[assignment]


Region = Literal["fr", "sa"]

# ---- Endpoints ----

# Region = France
# -- Prod --
CORE_API_URL: Final[str] = "https://apis.pasqal.cloud/core-fast"

ACCOUNT_API_URL: Final[str] = "https://apis.pasqal.cloud/account"

# -- Preprod --
PREPROD_CORE_API_URL: Final[str] = "https://apis.preprod.pasqal.cloud/core-fast"

PREPROD_ACCOUNT_API_URL: Final[str] = "https://apis.preprod.pasqal.cloud/account"

# -- Dev --
DEV_CORE_API_URL: Final[str] = "https://apis-127-0-0-1.nip.io/core-fast"

DEV_ACCOUNT_API_URL: Final[str] = "https://apis-127-0-0-1.nip.io/account"

# Region = Saudi-Arabia

# -- Prod --
KSA_CORE_API_URL: Final[str] = "https://apis.sa.pasqal.cloud/core-fast"

KSA_ACCOUNT_API_URL: Final[str] = "https://apis.sa.pasqal.cloud/account"

# -- Preprod --
KSA_PREPROD_CORE_API_URL: Final[str] = "https://apis.preprod.sa.pasqal.cloud/core-fast"

KSA_PREPROD_ACCOUNT_API_URL: Final[str] = "https://apis.preprod.sa.pasqal.cloud/account"

# -- Dev (local) --
KSA_DEV_CORE_API_URL: Final[str] = "https://apis-127-0-0-1.nip.io/core-fast"

KSA_DEV_ACCOUNT_API_URL: Final[str] = "https://apis-127-0-0-1.nip.io/account"


@dataclass
class Endpoints:
    core: str = CORE_API_URL
    account: str = ACCOUNT_API_URL

    @classmethod
    def from_region(cls, region: Optional[Region]) -> "Endpoints":
        if region == "sa":
            return Endpoints(core=KSA_CORE_API_URL, account=KSA_ACCOUNT_API_URL)
        return Endpoints()


# ---- Auth0 ----

AUTH0_TOKEN_PROVIDER_GRANT_TYPE = "http://auth0.com/oauth/grant-type/password-realm"

# Prod Auth0 configuration
AUTH0_DOMAIN: Final[str] = "authenticate.pasqal.cloud"
AUTH0_TOKEN_ENDPOINT: Final[str] = "https://pasqal.eu.auth0.com/oauth/token"
PUBLIC_CLIENT_ID: Final[str] = "PeZvo7Atx7IVv3iel59asJSb4Ig7vuSB"
AUDIENCE: Final[str] = "https://apis.pasqal.cloud/account/api/v1"

PREPROD_AUTH0_DOMAIN: Final[str] = "authenticate.preprod.pasqal.cloud"
PREPROD_AUTH0_TOKEN_ENDPOINT: Final[str] = (
    "https://pasqal-preprod.eu.auth0.com/oauth/token"
)
PREPROD_PUBLIC_CLIENT_ID: Final[str] = "dnbZLGCXp9TPioeBGCmuiPKjoPJ2ivpb"
PREPROD_AUDIENCE: Final[str] = "https://apis.preprod.pasqal.cloud/account/api/v1"

DEV_AUTH0_DOMAIN: Final[str] = "authenticate.dev.pasqal.cloud"
DEV_AUTH0_TOKEN_ENDPOINT: Final[str] = "https://pasqal-dev.eu.auth0.com/oauth/token"
DEV_PUBLIC_CLIENT_ID: Final[str] = "AvOi3cerijY8jPFVhLbGeUbVIGVcaKMv"
DEV_AUDIENCE: Final[str] = "https://apis.dev.pasqal.cloud/account/api/v1"

REALM: Final[str] = "pcs-users"

# ---- Keycloak ----
SA_KEYCLOAK_BASE_URL = "https://auth.sa.pasqal.cloud"
SA_KEYCLOAK_TOKEN_ENDPOINT = (
    "https://auth.sa.pasqal.cloud/realms/pasqal-cloud/protocol/openid-connect/token"
)

PREPROD_SA_KEYCLOAK_BASE_URL = "https://auth.preprod.sa.pasqal.cloud"
PREPROD_SA_KEYCLOAK_TOKEN_ENDPOINT = "https://auth.preprod.sa.pasqal.cloud/realms/pasqal-cloud/protocol/openid-connect/token"

KEYCLOAK_SDK_CLIENT_ID = "pasqal-cloud-python"
KEYCLOAK_REALM = "pasqal-cloud"


@dataclass
class Auth0Conf:
    domain: str = AUTH0_DOMAIN
    public_client_id: str = PUBLIC_CLIENT_ID
    audience: str = AUDIENCE
    realm: str = REALM


@dataclass
class TokenProviderConf:
    token_endpoint: str
    public_client_id: str
    audience: str
    realm: str
    grant_type: str

    @classmethod
    def from_auth0_config(cls, auth0: Auth0Conf) -> "TokenProviderConf":
        if not isinstance(auth0, Auth0Conf):
            raise TypeError(f"auth0 parameter must be a {Auth0Conf.__name__} instance")

        return TokenProviderConf(
            token_endpoint="https://{}/oauth/token".format(auth0.domain),
            public_client_id=auth0.public_client_id,
            audience=auth0.audience,
            realm=auth0.realm,
            grant_type=AUTH0_TOKEN_PROVIDER_GRANT_TYPE,
        )

    @classmethod
    def from_region(cls, region: Optional[Region]) -> "TokenProviderConf":
        if region == "sa":
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
            grant_type=AUTH0_TOKEN_PROVIDER_GRANT_TYPE,
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
        grant_type=AUTH0_TOKEN_PROVIDER_GRANT_TYPE,
    ),
    "fr-preprod": TokenProviderConf(
        token_endpoint=PREPROD_AUTH0_TOKEN_ENDPOINT,
        public_client_id=PREPROD_PUBLIC_CLIENT_ID,
        audience=PREPROD_AUDIENCE,
        realm=REALM,
        grant_type=AUTH0_TOKEN_PROVIDER_GRANT_TYPE,
    ),
    "fr-dev": TokenProviderConf(
        token_endpoint=DEV_AUTH0_TOKEN_ENDPOINT,
        public_client_id=DEV_PUBLIC_CLIENT_ID,
        audience=DEV_AUDIENCE,
        realm=REALM,
        grant_type=AUTH0_TOKEN_PROVIDER_GRANT_TYPE,
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


# ---- Region/env deployments (CLI login, SDK defaults) ----

Env = Literal["prod", "preprod", "dev"]

REGIONS: tuple[Region, ...] = get_args(Region)
ENVS: tuple[Env, ...] = get_args(Env)


@dataclass(frozen=True)
class DeploymentConf:
    issuer: str
    client_id: str
    audience: str
    # API URLs used when the SDK `endpoints` argument is not given.
    api: Endpoints


# TODO: replace Auth0 PROD client ID.
DEPLOYMENTS: dict[tuple[Region, Env], DeploymentConf] = {
    ("fr", "prod"): DeploymentConf(
        f"https://{AUTH0_DOMAIN}/",
        PUBLIC_CLIENT_ID,
        AUDIENCE,
        Endpoints(core=CORE_API_URL, account=ACCOUNT_API_URL),
    ),
    ("fr", "preprod"): DeploymentConf(
        f"https://{PREPROD_AUTH0_DOMAIN}/",
        PREPROD_PUBLIC_CLIENT_ID,
        PREPROD_AUDIENCE,
        Endpoints(core=PREPROD_CORE_API_URL, account=PREPROD_ACCOUNT_API_URL),
    ),
    ("fr", "dev"): DeploymentConf(
        f"https://{DEV_AUTH0_DOMAIN}/",
        DEV_PUBLIC_CLIENT_ID,
        DEV_AUDIENCE,
        Endpoints(core=DEV_CORE_API_URL, account=DEV_ACCOUNT_API_URL),
    ),
    ("sa", "prod"): DeploymentConf(
        f"{SA_KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}",
        KEYCLOAK_SDK_CLIENT_ID,
        AUDIENCE,
        Endpoints(core=KSA_CORE_API_URL, account=KSA_ACCOUNT_API_URL),
    ),
    ("sa", "preprod"): DeploymentConf(
        f"{PREPROD_SA_KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}",
        KEYCLOAK_SDK_CLIENT_ID,
        PREPROD_AUDIENCE,
        Endpoints(core=KSA_PREPROD_CORE_API_URL, account=KSA_PREPROD_ACCOUNT_API_URL),
    ),
    ("sa", "dev"): DeploymentConf(
        "https://keycloak-127-0-0-1.nip.io/realms/users",
        KEYCLOAK_SDK_CLIENT_ID,
        DEV_AUDIENCE,
        Endpoints(core=KSA_DEV_CORE_API_URL, account=KSA_DEV_ACCOUNT_API_URL),
    ),
}


Source = Literal["flag", "env var", "default"]


@dataclass(frozen=True)
class PasqalCloudTarget:
    region: Region
    env: Env
    deployment: DeploymentConf
    region_source: Source
    env_source: Source


def _from_env(var: str, default: str, valid: tuple[str, ...]) -> tuple[str, Source]:
    value = os.environ.get(var)
    if not value:
        return default, "default"
    if value not in valid:
        raise ValueError(
            f"Invalid ${var}={value!r}, expected one of: {', '.join(valid)}"
        )
    return value, "env var"


def resolve_pasqal_cloud_target(region: Region | None = None) -> PasqalCloudTarget:
    """Resolve region/env from the explicit argument, then env vars, then defaults.

    Raises ValueError on unknown env var values, never falls back to prod.
    """
    # _from_env validated the values, so the casts are safe.
    region_source: Source = "flag"
    if not region:
        value, region_source = _from_env("PASQAL_CLOUD_REGION", "fr", REGIONS)
        region = cast(Region, value)
    value, env_source = _from_env("PASQAL_CLOUD_ENV", "prod", ENVS)
    env = cast(Env, value)
    return PasqalCloudTarget(
        region, env, DEPLOYMENTS[(region, env)], region_source, env_source
    )
