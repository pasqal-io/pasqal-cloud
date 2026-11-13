from __future__ import annotations

from typing import Any

from pasqal_cloud.authentication import PasswordGrantTokenProvider
from requests import HTTPError


class FakeAuth0AuthenticationSuccess(PasswordGrantTokenProvider):
    def _query_token(self) -> dict[str, Any]:
        return {
            "access_token": "some_token",
            "id_token": "id_token",
            "scope": "openid profile email",
            "expires_in": 86400,
            "token_type": "Bearer",
        }


class FakeAuth0AuthenticationFailure(PasswordGrantTokenProvider):
    def _query_token(self) -> dict[str, Any]:
        raise HTTPError("403: Wrong email/password")
