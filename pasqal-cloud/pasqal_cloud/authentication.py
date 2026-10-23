from __future__ import annotations

import time
import warnings
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests
from jwt import decode, DecodeError
from requests import PreparedRequest
from requests.auth import AuthBase
from requests.exceptions import HTTPError

from pasqal_cloud import oidc, token_cache
from pasqal_cloud.endpoints import (
    AUTH0_TOKEN_PROVIDER_GRANT_TYPE,
    Auth0Conf,
    KEYCLOAK_REALM,
    PasqalCloudTarget,
    REALM,
    TokenProviderConf,
)


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


class LoginRequiredError(TokenProviderError):
    """The cached login is missing, expired or revoked: run the command given
    in the message."""


class TokenProvider(ABC):
    def __init__(self, *args: list[Any], **kwargs: dict): ...

    @abstractmethod
    def get_token(self) -> str:
        raise NotImplementedError


class ExpiringTokenProvider(TokenProvider, ABC):
    """TokenProvider class which caches a token up to its expiry date.

    This is an abstract class. Create your custom TokenProvider by inheriting from
    this class and defining your own `_query_token` method. See
    PasswordGrantTokenProvider for an implementation example.
    """

    __token_cache: Optional[tuple[datetime, str]] = None
    expiry_window: timedelta = timedelta(minutes=1.0)

    @abstractmethod
    def _query_token(self) -> dict[str, Any]:
        """Return a dictionnary mapping the key 'access_token' to the token value.

        Optionally, your dictionnary may include an 'expires_in' key mapped to the
        duration before expiration of your token (in seconds).
        """
        raise NotImplementedError

    def get_token(self) -> str:
        """Returns the token stored in the cache. If token has expired, first refresh
        the cache by calling the _query_token method.
        """
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
        expires_in = token_response.get("expires_in")
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


AUTH0_TOKEN_PROVIDER_SCOPE = "openid profile email"


class PasswordGrantTokenProvider(ExpiringTokenProvider):
    def __init__(
        self,
        username: str,
        password: str,
        config: TokenProviderConf,
        verify: bool = True,
    ):
        """Initializes the token provider with user credentials and
        a configuration object

        Args:
            username: name of the user to log in as
            password: password of the user to log in as
            config: configuration of the auth client
        """
        self.username = username
        self.password = password
        self.config = config
        self.verify = verify
        self.get_token()

    def _query_token(self) -> Any:
        response = requests.post(
            self.config.token_endpoint,
            data={
                "client_id": self.config.public_client_id,
                "grant_type": self.config.grant_type,
                "realm": self.config.realm,
                "audience": self.config.audience,
                "username": self.username,
                "password": self.password,
            },
            verify=self.verify,
        )
        if response.status_code >= 400:
            error_description = self._get_error_message(response.json())
            raise HTTPError(
                f"{response.status_code}: {error_description}", response=response
            )
        return response.json()

    def _get_error_message(self, content: dict) -> Any:
        # error_description is standard and optional
        # error is standard and mandatory
        # source: https://datatracker.ietf.org/doc/html/rfc6749#section-4.1.2.1
        # auth0 note: message can be returned while non standard -> https://github.com/auth0/auth0-python/blob/master/src/auth0/authentication/rest.py#L338
        # kc note: ok wrt standard -> https://github.com/keycloak/keycloak/blob/26.5.3/core/src/main/java/org/keycloak/representations/idm/OAuth2ErrorRepresentation.java#L27
        return (
            content.get("error_description")
            if "error_description" in content
            else content.get("error", "")
        )


REFRESH_ATTEMPTS = 3


def login_command(target: PasqalCloudTarget) -> str:
    """The `pasqal-cloud auth login` command line for `target`."""
    env = "" if target.env == "prod" else f"PASQAL_CLOUD_ENV={target.env} "
    return f"{env}pasqal-cloud auth login --region {target.region}"


def password_grant_config(target: PasqalCloudTarget) -> TokenProviderConf:
    """The password login of `target`, with the client of the interactive logins."""
    deployment = target.deployment
    try:
        token_endpoint = oidc.discover(deployment.issuer)["token_endpoint"]
    except oidc.OIDCError as e:
        raise TokenProviderError(e) from e

    if target.region == "sa":
        realm, grant_type = KEYCLOAK_REALM, "password"
    else:
        realm, grant_type = REALM, AUTH0_TOKEN_PROVIDER_GRANT_TYPE

    return TokenProviderConf(
        token_endpoint=token_endpoint,
        public_client_id=deployment.client_id,
        audience=deployment.audience,
        realm=realm,
        grant_type=grant_type,
    )


class CachedLoginTokenProvider(ExpiringTokenProvider):
    """Token provider using the `pasqal-cloud auth login` entry of the token
    cache, refreshing its access and refresh tokens when needed.

    Refreshes are serialised across processes and hosts by the cache lock:
    refresh tokens rotate, so two processes refreshing the same one would
    invalidate each other.
    """

    def __init__(self, target: PasqalCloudTarget):
        self.target = target

    def _login_required(self, reason: str) -> LoginRequiredError:
        return LoginRequiredError(
            f"{reason}, run: {login_command(self.target)}"
            " (add --device if no browser is available)"
        )

    def _query_token(self) -> dict[str, Any]:
        key = token_cache.entry_key(self.target.region, self.target.env)

        # Another process may have refreshed the tokens since this one read them.
        with token_cache.lock():
            entries = token_cache.read_entries()
            entry = entries.get(key)
            if entry is None or not entry.matches(self.target.deployment):
                raise self._login_required(f"Not logged in to {key}")

            if entry.expires_at - time.time() <= self.expiry_window.total_seconds():
                entry = self._refresh(entry)
                token_cache.write_entries({**entries, key: entry})

        return {
            "access_token": entry.access_token,
            "expires_in": entry.expires_at - time.time(),
        }

    def _refresh(self, entry: token_cache.CacheEntry) -> token_cache.CacheEntry:
        """Exchange the refresh token, retrying transient errors."""
        last_error: oidc.OIDCError | None = None
        for attempt in range(REFRESH_ATTEMPTS):
            if attempt:
                time.sleep(2 ** (attempt - 1))

            try:
                tokens = oidc.token_request(
                    oidc.discover(entry.issuer),
                    {
                        "grant_type": "refresh_token",
                        "client_id": entry.client_id,
                        "refresh_token": entry.refresh_token,
                    },
                )
                return entry.updated(tokens)

            except oidc.OIDCError as e:
                # The entry is kept so `pasqal-cloud auth status` can report it.
                if e.error == "invalid_grant":
                    raise self._login_required(
                        f"The login to {entry.key} expired or was revoked"
                    ) from e
                if not e.transient:
                    raise TokenProviderError(e) from e
                last_error = e

            except (KeyError, TypeError, ValueError) as e:
                raise TokenProviderError(f"Invalid token response: {e!r}") from e

        raise TokenProviderError(last_error) from last_error


def _warn_deprecated_auth0_provider(name: str) -> None:
    warnings.warn(
        f"{name} is deprecated and will be removed in the next major version: pass"
        " username/password to PasqalCloudConnection, or log in with"
        " `pasqal-cloud auth login`.",
        FutureWarning,
        # The caller of the token provider, through its __init__.
        stacklevel=3,
    )


class Auth0TokenProvider(PasswordGrantTokenProvider):
    """ExpiringTokenProvider implementation which fetches a token from auth0."""

    def __init__(self, username: str, password: str, auth0: Auth0Conf):
        """Initializes the token provider with user credentials and
        an auth0 configuration object

        Args:
            username: name of the user to log in as
            password: password of the user to log in as
            auth0: auth0 configuration object to target the proper auth0 tenant and app
        """
        _warn_deprecated_auth0_provider(type(self).__name__)
        super().__init__(
            username, password, TokenProviderConf._from_auth0_config(auth0)
        )


class InsecureAuth0TokenProvider(PasswordGrantTokenProvider):
    """Token Provider for auth0 with SSL verification disabled

    Should be only used in testing environments.
    """

    def __init__(self, username: str, password: str, auth0: Auth0Conf):
        """Initializes the token provider with user credentials and
        an auth0 configuration object

        Args:
            username: name of the user to log in as
            password: password of the user to log in as
            auth0: auth0 configuration object to target the proper auth0 tenant and app
        """
        _warn_deprecated_auth0_provider(type(self).__name__)
        super().__init__(
            username,
            password,
            TokenProviderConf._from_auth0_config(auth0),
            verify=False,
        )
