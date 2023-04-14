from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from auth0.v3.authentication import GetToken  # type: ignore
from jwt import decode, DecodeError
from requests import PreparedRequest
from requests.auth import AuthBase

from pasqal_cloud.endpoints import Auth0Conf
from pasqal_cloud.errors import HTTPError


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
    def __init__(self, *args: list[Any], **kwargs: dict):
        ...

    @abstractmethod
    def get_token(self) -> str:
        raise NotImplementedError


class ExpiringTokenProvider(TokenProvider, ABC):
    __token_cache: Optional[tuple[datetime, str]] = None
    expiry_window: timedelta = timedelta(minutes=1.0)

    @abstractmethod
    def _query_token(self) -> dict[str, Any]:
        raise NotImplementedError

    def get_token(self) -> str:
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
        expires_in = token_response.get("expires_in", None)
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


class Auth0TokenProvider(ExpiringTokenProvider):
    def __init__(self, username: str, password: str, auth0: Auth0Conf):
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
            scope="openid profile email",
            realm=self.auth0.realm,
            grant_type="http://auth0.com/oauth/grant-type/password-realm",
        )
        return validated_token
