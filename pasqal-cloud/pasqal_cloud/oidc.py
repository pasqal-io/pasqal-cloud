"""Minimal OIDC client helpers shared by the CLI login flows: discovery, token
requests, revocation."""

from __future__ import annotations

from typing import Any

import jwt
import requests

SCOPES = ("openid", "profile", "email", "offline_access")
TIMEOUT = 10  # seconds, per HTTP request


class OIDCError(Exception):
    pass


class LoginError(Exception):
    """A login flow failed, the message tells the user what to do."""


def discover(issuer: str) -> dict[str, Any]:
    """Fetch the issuer's OpenID configuration and check the scopes we need."""
    url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        config: dict[str, Any] = response.json()
    except (requests.RequestException, ValueError) as e:
        raise OIDCError(f"OIDC discovery failed ({url}): {e}") from e
    missing = set(SCOPES) - set(config.get("scopes_supported", []))
    if missing:
        raise OIDCError(
            f"{issuer} does not support the scopes: {', '.join(sorted(missing))}"
        )
    return config


def token_request(config: dict[str, Any], data: dict[str, str]) -> dict[str, Any]:
    """POST `data` to the token endpoint, raise OIDCError on any failure."""
    try:
        response = requests.post(config["token_endpoint"], data=data, timeout=TIMEOUT)
        body: dict[str, Any] = response.json()
    except (requests.RequestException, ValueError) as e:
        raise OIDCError(f"Token request failed: {e}") from e
    if not response.ok or "error" in body:
        error = body.get("error", f"HTTP {response.status_code}")
        description = body.get("error_description")
        raise OIDCError(
            f"Token request failed: {error}"
            + (f" ({description})" if description else "")
        )
    return body


def revoke(config: dict[str, Any], client_id: str, refresh_token: str) -> None:
    """Revoke `refresh_token` (RFC 7009), raise OIDCError on failure."""
    endpoint = config.get("revocation_endpoint")
    if not endpoint:
        raise OIDCError("the provider has no revocation endpoint")
    try:
        requests.post(
            endpoint,
            data={
                "client_id": client_id,
                "token": refresh_token,
                "token_type_hint": "refresh_token",
            },
            timeout=TIMEOUT,
        ).raise_for_status()
    except requests.RequestException as e:
        raise OIDCError(f"Token revocation failed: {e}") from e


def id_claims(id_token: str) -> dict[str, Any]:
    """Decode id_token claims without signature check.

    Display only: the token comes straight from the token endpoint over TLS
    (OIDC Core 3.1.3.7), and its claims never drive authorization decisions.
    """
    try:
        claims: dict[str, Any] = jwt.decode(
            id_token, options={"verify_signature": False}
        )
    except jwt.InvalidTokenError as e:
        raise OIDCError(f"Invalid id_token: {e}") from e
    return claims
