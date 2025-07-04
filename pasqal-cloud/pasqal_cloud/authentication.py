from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests
from auth0.v3.authentication import GetToken  # type: ignore[import-untyped]
from jwt import decode, DecodeError
from requests import PreparedRequest
from requests.auth import AuthBase
from requests.exceptions import HTTPError

from pasqal_cloud.endpoints import Auth0Conf


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


class TokenProvider(ABC):
    def __init__(self, *args: list[Any], **kwargs: dict): ...

    @abstractmethod
    def get_token(self) -> str:
        raise NotImplementedError


class ExpiringTokenProvider(TokenProvider, ABC):
    """TokenProvider class which caches a token up to its expiry date.

    This is an abstract class. Create your custom TokenProvider by inheriting from
    this class and defining your own `_query_token` method. See Auth0TokenProvider for
    an implementation example.
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
AUTH0_TOKEN_PROVIDER_GRANT_TYPE = "http://auth0.com/oauth/grant-type/password-realm"


class Auth0TokenProvider(ExpiringTokenProvider):
    """ExpiringTokenProvider implementation which fetches a token from auth0."""

    def __init__(self, username: str, password: str, auth0: Auth0Conf):
        """Initializes the token provider with user credentials and
        an auth0 configuration object

        Args:
            username: name of the user to log in as
            password: password of the user to log in as
            auth0: auth0 configuration object to target the proper auth0 tenant and app
        """
        self.username = username
        self.password = password
        self.auth0 = auth0

        # Makes a call in order to check the credentials at creation
        self.get_token()

    def _query_token(self) -> dict[str, Any]:
        token = GetToken(self.auth0.domain)

        # No client secret required for this Application since
        # "Token Endpoint Authentication Method" set to None
        validated_token: dict[str, Any] = token.login(
            client_id=self.auth0.public_client_id,
            client_secret="",
            username=self.username,
            password=self.password,
            audience=self.auth0.audience,
            scope=AUTH0_TOKEN_PROVIDER_SCOPE,
            realm=self.auth0.realm,
            grant_type=AUTH0_TOKEN_PROVIDER_GRANT_TYPE,
        )
        return validated_token


class InsecureAuth0TokenProvider(Auth0TokenProvider):
    """Token Provider for auth0 with SSL verification disabled

    Should be only used in testing environments.
    """

    def _query_token(self) -> Any:
        response = requests.post(
            "https://{}/oauth/token".format(self.auth0.domain),
            data={
                "client_id": self.auth0.public_client_id,
                "username": self.username,
                "password": self.password,
                "realm": self.auth0.realm,
                "client_secret": "",
                "scope": AUTH0_TOKEN_PROVIDER_SCOPE,
                "audience": self.auth0.audience,
                "grant_type": AUTH0_TOKEN_PROVIDER_GRANT_TYPE,
            },
            verify=False,
        )
        response.raise_for_status()
        return response.json()
