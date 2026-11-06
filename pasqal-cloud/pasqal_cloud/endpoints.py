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
import warnings
from dataclasses import dataclass
from sys import version_info
from typing import Any, Literal, Optional

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
    def from_region(cls, region: Optional[Region]) -> "Endpoints":
        warnings.warn(
            "Endpoints.from_region() is deprecated and will be removed in the next"
            " major version: the SDK selects the endpoints from the region.",
            FutureWarning,
            stacklevel=2,
        )

        if region == "sa":
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

PREPROD_SA_KEYCLOAK_BASE_URL = "https://auth.preprod.sa.pasqal.cloud/"
PREPROD_SA_KEYCLOAK_TOKEN_ENDPOINT = "https://auth.preprod.sa.pasqal.cloud/realms/pasqal-cloud/protocol/openid-connect/token"

KEYCLOAK_SDK_CLIENT_ID = "pasqal-cloud-python"
KEYCLOAK_REALM = "pasqal-cloud"


@dataclass
class Auth0Conf:
    domain: str = AUTH0_DOMAIN
    public_client_id: str = PUBLIC_CLIENT_ID
    audience: str = AUDIENCE
    # Ignored: logins use the standard password grant, which has no realm.
    realm: str = REALM


@dataclass
class TokenProviderConf:
    token_endpoint: str
    public_client_id: str
    audience: str
    # Only sent when set: the standard password grant has no realm.
    realm: Optional[str]
    grant_type: str

    @classmethod
    def from_auth0_config(cls, auth0: Auth0Conf) -> "TokenProviderConf":
        warnings.warn(
            "TokenProviderConf.from_auth0_config() is deprecated and will be removed"
            " in the next major version: the SDK selects the auth configuration from"
            " the region.",
            FutureWarning,
            stacklevel=2,
        )

        return cls._from_auth0_config(auth0)

    @classmethod
    def _from_auth0_config(cls, auth0: Auth0Conf) -> "TokenProviderConf":
        if not isinstance(auth0, Auth0Conf):
            raise TypeError(f"auth0 parameter must be a {Auth0Conf.__name__} instance")

        return TokenProviderConf(
            token_endpoint="https://{}/oauth/token".format(auth0.domain),
            public_client_id=auth0.public_client_id,
            audience=auth0.audience,
            realm=None,
            grant_type="password",
        )

    @classmethod
    def from_region(cls, region: Optional[Region]) -> "TokenProviderConf":
        warnings.warn(
            "TokenProviderConf.from_region() is deprecated and will be removed in"
            " the next major version: the SDK selects the auth configuration from"
            " the region.",
            FutureWarning,
            stacklevel=2,
        )

        if region == "sa":
            return TokenProviderConf(
                token_endpoint=SA_KEYCLOAK_TOKEN_ENDPOINT,
                public_client_id=KEYCLOAK_SDK_CLIENT_ID,
                audience=AUDIENCE,
                realm=None,
                grant_type="password",
            )
        return TokenProviderConf(
            token_endpoint=AUTH0_TOKEN_ENDPOINT,
            public_client_id=PUBLIC_CLIENT_ID,
            audience=AUDIENCE,
            realm=None,
            grant_type="password",
        )


# ---- Pre-filled environment configuration ----


_PASQAL_ENDPOINTS = {
    "prod": Endpoints(core=CORE_API_URL, account=ACCOUNT_API_URL),
    "preprod": Endpoints(core=PREPROD_CORE_API_URL, account=PREPROD_ACCOUNT_API_URL),
    "dev": Endpoints(core=DEV_CORE_API_URL, account=DEV_ACCOUNT_API_URL),
    "sa-prod": Endpoints(core=KSA_CORE_API_URL, account=KSA_ACCOUNT_API_URL),
    "sa-preprod": Endpoints(
        core=KSA_PREPROD_CORE_API_URL, account=KSA_PREPROD_ACCOUNT_API_URL
    ),
}

_AUTH0_CONFIG = {
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

_AUTH_CONFIG = {
    "fr-prod": TokenProviderConf(
        token_endpoint=AUTH0_TOKEN_ENDPOINT,
        public_client_id=PUBLIC_CLIENT_ID,
        audience=AUDIENCE,
        realm=None,
        grant_type="password",
    ),
    "fr-preprod": TokenProviderConf(
        token_endpoint=PREPROD_AUTH0_TOKEN_ENDPOINT,
        public_client_id=PREPROD_PUBLIC_CLIENT_ID,
        audience=PREPROD_AUDIENCE,
        realm=None,
        grant_type="password",
    ),
    "fr-dev": TokenProviderConf(
        token_endpoint=DEV_AUTH0_TOKEN_ENDPOINT,
        public_client_id=DEV_PUBLIC_CLIENT_ID,
        audience=DEV_AUDIENCE,
        realm=None,
        grant_type="password",
    ),
    "sa-prod": TokenProviderConf(
        token_endpoint=SA_KEYCLOAK_TOKEN_ENDPOINT,
        public_client_id=KEYCLOAK_SDK_CLIENT_ID,
        audience=AUDIENCE,
        realm=None,
        grant_type="password",
    ),
    "sa-preprod": TokenProviderConf(
        token_endpoint=PREPROD_SA_KEYCLOAK_TOKEN_ENDPOINT,
        public_client_id=KEYCLOAK_SDK_CLIENT_ID,
        audience=PREPROD_AUDIENCE,
        realm=None,
        grant_type="password",
    ),
}

# Only meant for the deprecated `endpoints`, `auth0` and `auth_config` arguments.
_DEPRECATED_CONFIGS = {
    "PASQAL_ENDPOINTS": _PASQAL_ENDPOINTS,
    "AUTH0_CONFIG": _AUTH0_CONFIG,
    "AUTH_CONFIG": _AUTH_CONFIG,
}


def __getattr__(name: str) -> Any:
    if name in _DEPRECATED_CONFIGS:
        warnings.warn(
            f"`{name}` is deprecated and will be removed in the next major version:"
            " select the region with the `region` argument, and other environments"
            " with a `pasqal-cloud profile`.",
            FutureWarning,
            stacklevel=2,
        )
        return _DEPRECATED_CONFIGS[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# `import *` skips __getattr__: list the deprecated names so they are still
# exported (with their warning), next to every public name exported until now.
__all__ = [name for name in globals() if not name.startswith("_")]
__all__ += list(_DEPRECATED_CONFIGS)
