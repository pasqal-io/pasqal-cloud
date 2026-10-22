import time
from dataclasses import replace
from unittest.mock import Mock, patch
from urllib.parse import parse_qs

import pytest
from pasqal_cloud import authentication, oidc, token_cache
from pasqal_cloud.authentication import (
    LoginRequiredError,
    TokenProvider,
    TokenProviderError,
)
from pasqal_cloud.endpoints import DEPLOYMENTS, Endpoints
from pasqal_cloud.http_client import HTTPClient

from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess
from tests.test_token_cache import make_entry

ISSUER = DEPLOYMENTS[("fr", "prod")].issuer.rstrip("/")
DISCOVERY = f"{ISSUER}/.well-known/openid-configuration"
TOKEN = f"{ISSUER}/token"


@pytest.fixture(autouse=True)
def _no_sleep():
    with patch("pasqal_cloud.authentication.time.sleep"):
        yield


@pytest.fixture
def idp(requests_mock):
    requests_mock.get(
        DISCOVERY,
        json={
            "authorization_endpoint": f"{ISSUER}/authorize",
            "token_endpoint": TOKEN,
            "scopes_supported": ["openid", "offline_access"],
        },
    )
    requests_mock.post(
        TOKEN,
        json={
            "access_token": "NEW-ACCESS",
            "refresh_token": "NEW-REFRESH",
            "expires_in": 3600,
        },
    )
    return requests_mock


def save(**changes):
    entry = replace(make_entry(), **changes)
    token_cache.write_entries({entry.key: entry})
    return entry


def cached():
    return token_cache.read_entries()["fr/prod"]


def test_uses_cached_access_token(requests_mock):
    save()
    assert HTTPClient().user_token() == "SECRET-ACCESS"
    assert not requests_mock.request_history


def test_refreshes_expired_token_and_rotates_refresh_token(idp):
    # Still valid, but within the 1 min expiry window: treated as expired.
    save(expires_at=int(time.time()) + 30)

    # The second call reuses the in-memory token instead of refreshing again.
    client = HTTPClient()
    assert client.user_token() == "NEW-ACCESS"
    assert client.user_token() == "NEW-ACCESS"

    # A single refresh, exchanging the cached refresh token.
    token_requests = [r for r in idp.request_history if r.method == "POST"]
    assert len(token_requests) == 1
    assert parse_qs(token_requests[0].text) == {
        "grant_type": ["refresh_token"],
        "client_id": [DEPLOYMENTS[("fr", "prod")].client_id],
        "refresh_token": ["SECRET-REFRESH"],
    }

    # Refresh tokens are single-use: the new one must be saved for the next
    # process. The refresh response has no id token, so the claims are kept.
    entry = cached()
    assert (entry.access_token, entry.refresh_token) == ("NEW-ACCESS", "NEW-REFRESH")
    assert entry.id_claims["email"] == "alice@example.com"

    # A leaked lock would block other processes until it goes stale.
    assert not token_cache.lock_path().exists()


def test_uses_token_refreshed_by_another_process(idp):
    save(expires_at=0)
    client = HTTPClient()
    save(access_token="OTHER-ACCESS")  # another process refreshed meanwhile
    assert client.user_token() == "OTHER-ACCESS"
    assert not idp.request_history


def test_discovers_once_per_process(idp):
    for _ in range(2):
        save(expires_at=0)
        HTTPClient().user_token()
    assert [r.method for r in idp.request_history] == ["GET", "POST", "POST"]


def test_invalid_grant_requires_login(idp, monkeypatch):
    # On preprod, so the login hint must carry the PASQAL_CLOUD_ENV prefix.
    monkeypatch.setenv("PASQAL_CLOUD_ENV", "preprod")
    deployment = DEPLOYMENTS[("fr", "preprod")]

    # An expired preprod login, so the next token triggers a refresh.
    entry = replace(
        make_entry(),
        env="preprod",
        issuer=deployment.issuer,
        client_id=deployment.client_id,
        expires_at=0,
    )
    token_cache.write_entries({entry.key: entry})

    # The idp fixture only serves the prod issuer: serve the preprod one too,
    # with a token endpoint rejecting the refresh token as expired or revoked.
    issuer = deployment.issuer.rstrip("/")
    idp.get(
        f"{issuer}/.well-known/openid-configuration",
        json={
            "authorization_endpoint": f"{issuer}/authorize",
            "token_endpoint": f"{issuer}/token",
            "scopes_supported": ["offline_access"],
        },
    )
    idp.post(f"{issuer}/token", status_code=400, json={"error": "invalid_grant"})

    with pytest.raises(LoginRequiredError) as e:
        HTTPClient().user_token()
    assert "run: PASQAL_CLOUD_ENV=preprod pasqal-cloud auth login --region fr" in str(
        e.value
    )

    # The entry stays so `pasqal-cloud auth status` can still report it.
    assert token_cache.read_entries()["fr/preprod"] == entry


def test_expired_login_falls_back_to_public_device_specs(idp):
    save(expires_at=0)
    idp.post(TOKEN, status_code=400, json={"error": "invalid_grant"})
    client = HTTPClient()
    public_specs = idp.get(
        f"{client.endpoints.core}/api/v1/devices/public-specs",
        json={"data": [{"device_type": "FRESNEL", "specs": "{}"}]},
    )

    with pytest.warns(UserWarning, match="pasqal-cloud auth login --region fr"):
        assert client.get_device_specs_dict() == {"FRESNEL": "{}"}

    assert public_specs.called


def test_retries_transient_errors(idp):
    save(expires_at=0)
    idp.post(
        TOKEN,
        [
            {"status_code": 503},
            {"status_code": 429, "json": {"error": "slow_down"}},
            {"json": {"access_token": "NEW-ACCESS", "expires_in": 3600}},
        ],
    )
    assert HTTPClient().user_token() == "NEW-ACCESS"
    assert cached().refresh_token == "SECRET-REFRESH"  # not rotated


def test_gives_up_after_three_attempts(idp):
    save(expires_at=0)
    idp.post(TOKEN, status_code=503)
    with pytest.raises(TokenProviderError):
        HTTPClient().user_token()
    assert len([r for r in idp.request_history if r.method == "POST"]) == 3


def test_logged_out_meanwhile_requires_login():
    save(expires_at=0)
    client = HTTPClient()
    token_cache.write_entries({})
    with pytest.raises(LoginRequiredError, match="Not logged in to fr/prod"):
        client.user_token()


def test_not_logged_in_stays_unauthenticated():
    client = HTTPClient()
    assert client.authenticator is None
    with pytest.raises(ValueError, match="pasqal-cloud auth login --region fr"):
        client._authenticated_request("GET", "https://example.com")


def test_entry_of_another_client_is_ignored():
    save(client_id="old-client")
    assert HTTPClient().authenticator is None


def test_explicit_endpoints_ignore_the_cache():
    save()
    client = HTTPClient(endpoints=Endpoints(core="https://example.org/core"))
    assert client.authenticator is None


@patch("pasqal_cloud.http_client.PasswordGrantTokenProvider")
def test_explicit_credentials_win(password_provider):
    password_provider.return_value = FakeAuth0AuthenticationSuccess("u", "p", None)
    save()
    assert HTTPClient(username="u", password="p").user_token() == "some_token"


@patch("pasqal_cloud.http_client.PasswordGrantTokenProvider")
def test_password_wins_over_token_provider_with_a_warning(password_provider):
    password_provider.return_value = FakeAuth0AuthenticationSuccess("u", "p", None)
    token_provider = Mock(spec=TokenProvider)

    with pytest.warns(FutureWarning, match="token_provider and username/password"):
        client = HTTPClient(username="u", password="p", token_provider=token_provider)

    assert client.user_token() == "some_token"
    token_provider.get_token.assert_not_called()


def test_lock_outlives_the_slowest_refresh():
    # Per attempt: discovery and token requests, each up to TIMEOUT to connect
    # and as much to read; then the backoff between attempts.
    attempts = authentication.REFRESH_ATTEMPTS
    slowest = attempts * 2 * 2 * oidc.TIMEOUT + sum(2**i for i in range(attempts - 1))

    assert slowest < token_cache.LOCK_STALE_AFTER
