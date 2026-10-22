"""Minimal OIDC client helpers shared by the CLI login flows: discovery, token
requests, revocation."""

from __future__ import annotations

import base64
import functools
import hashlib
import secrets
from typing import Any

import jwt
import requests

SCOPES = ("openid", "profile", "email", "offline_access")
TIMEOUT = 10  # seconds, per HTTP request


class OIDCError(Exception):
    def __init__(self, message: str, error: str | None = None, transient: bool = False):
        super().__init__(message)
        self.error = error  # OAuth error code of the response, if any
        # Network error, 5xx or 429: worth retrying.
        self.transient = transient


def _is_transient(status: int) -> bool:
    return status == 429 or status >= 500


class LoginError(Exception):
    """A login flow failed, the message tells the user what to do."""


@functools.lru_cache(maxsize=None)
def discover(issuer: str, device: bool = False) -> dict[str, Any]:
    """Fetch the issuer's OpenID configuration and check the scopes and
    endpoints we need, including the device flow one if `device`."""
    url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    try:
        response = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise OIDCError(f"OIDC discovery failed ({url}): {e}", transient=True) from e

    try:
        response.raise_for_status()
        config: dict[str, Any] = response.json()
    except (requests.HTTPError, ValueError) as e:
        raise OIDCError(
            f"OIDC discovery failed ({url}): {e}",
            transient=_is_transient(response.status_code),
        ) from e

    if "offline_access" not in config.get("scopes_supported", []):
        raise OIDCError(f"{issuer} does not support the offline_access scope")

    missing = {"authorization_endpoint", "token_endpoint"} - config.keys()
    if missing:
        raise OIDCError(f"{url} has no {', '.join(sorted(missing))}")

    if device and "device_authorization_endpoint" not in config:
        raise OIDCError(f"Device flow not enabled for this environment ({issuer})")

    return config


def pkce_pair() -> tuple[str, str]:
    """Return a PKCE (RFC 7636) code verifier and its S256 challenge."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    return verifier, challenge


def token_request(config: dict[str, Any], data: dict[str, str]) -> dict[str, Any]:
    """POST `data` to the token endpoint, raise OIDCError on any failure."""
    return post_form(config["token_endpoint"], data, "Token request")


def post_form(url: str, data: dict[str, str], what: str) -> dict[str, Any]:
    """POST `data` to `url`, return the JSON body, raise OIDCError on any failure."""
    try:
        response = requests.post(url, data=data, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise OIDCError(f"{what} failed: {e}", transient=True) from e

    try:
        body: dict[str, Any] = response.json()
    except ValueError:
        body = {}  # e.g. an HTML error page from a proxy: report the HTTP status

    if not response.ok or not body or "error" in body:
        error = body.get("error")
        description = body.get("error_description")
        raise OIDCError(
            f"{what} failed: {error or f'HTTP {response.status_code}'}"
            + (f" ({description})" if description else ""),
            error,
            _is_transient(response.status_code),
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
