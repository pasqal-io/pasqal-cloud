from __future__ import annotations

from typing import Any

from auth0.v3.exceptions import Auth0Error

from pasqal_cloud.authentication import Auth0TokenProvider


class FakeAuth0AuthenticationSuccess(Auth0TokenProvider):
    def _query_token(self) -> dict[str, Any]:
        return {
            "access_token": "some_token",
            "id_token": "id_token",
            "scope": "openid profile email",
            "expires_in": 86400,
            "token_type": "Bearer",
        }


class FakeAuth0AuthenticationFailure(Auth0TokenProvider):
    def _query_token(self) -> dict[str, Any]:
        raise Auth0Error(
            status_code=403, error_code=403, message="Wrong email/password"
        )
