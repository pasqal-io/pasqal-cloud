import urllib.parse
from datetime import datetime, timedelta, timezone

import pytest
from pasqal_cloud.authentication import AccessTokenProvider, TokenProviderConf


def make_token_response(
    access="AT1",
    refresh="RT1",
    expires_in=120,
    refresh_expires_in=300,
):
    return {
        "access_token": access,
        "refresh_token": refresh,
        "expires_in": expires_in,
        "refresh_expires_in": refresh_expires_in,
    }


@pytest.fixture
def config():
    return TokenProviderConf(
        token_endpoint="http://keycloak/realms/myrealm/protocol/openid-connect/token",
        realm="myrealm",
        public_client_id="myclient",
        grant_type="password",
        audience="",
    )


@pytest.fixture
def now(monkeypatch):
    """Patch datetime.now() to a fixed deterministic timestamp."""
    fixed_now = datetime(2024, 1, 1, tzinfo=timezone.utc)

    class MockDT:
        @staticmethod
        def now(tz=None):
            return fixed_now

    monkeypatch.setattr("pasqal_cloud.authentication.datetime", MockDT)
    return fixed_now


def test_get_token_success(requests_mock, config):
    """Assert that one can get an access token using the token provider

    Two requests should be made to keycloak:
        - one password grant to get a refresh token.
        - one refresh token grant to get the access token
    """
    requests_mock.post(
        config.token_endpoint,
        json=make_token_response(access="AT1", refresh="RT1"),
    )

    provider = AccessTokenProvider("user", "pwd", config)
    token = provider.get_token()

    # Validate returned token
    assert token == "AT1"
    assert provider.refresh_token == "RT1"

    # Validate the grant_type used
    history = requests_mock.request_history
    assert len(history) == 2
    assert history[0].method == "POST"
    parsed = urllib.parse.parse_qs(history[0]._request.body)
    assert parsed["grant_type"][0] == "password"
    assert history[1].method == "POST"
    parsed = urllib.parse.parse_qs(history[1]._request.body)
    assert parsed["grant_type"][0] == "refresh_token"


def test_refresh_access_token_after_access_expiry(
    requests_mock, config, now, monkeypatch
):
    """Assert that the access token can be refreshed after it expires
    (case where refresh token is not yet expired.)

    Three requests are made to Keycloak:
        - Initial password grant to get the first refresh token (triggered in class init)
        - Refresh token grant to get the initial access token (triggered in class init)
        - refresh token grant to get a new access token when calling get_token

    """
    requests_mock.post(
        config.token_endpoint,
        [
            {"json": make_token_response("AT_INIT", "RT_INIT")},  # password grant
            {
                "json": make_token_response("AT_FIRST", "RT_FIRST")
            },  # refresh for first access token
            {
                "json": make_token_response("AT_REFRESHED", "RT_NEW")
            },  # refresh after access token expired
        ],
    )

    provider = AccessTokenProvider("user", "pwd", config)

    # Advance time to expire the access token
    # Refresh token did not expire however
    new_now = now + timedelta(minutes=2)

    class MockDT:
        @staticmethod
        def now(tz=None):
            return new_now

    monkeypatch.setattr("pasqal_cloud.authentication.datetime", MockDT)

    token = provider.get_token()

    assert token == "AT_REFRESHED"
    assert provider.refresh_token == "RT_NEW"

    # Validate sequence of grant_types
    history = requests_mock.request_history
    assert len(history) == 3

    parsed = urllib.parse.parse_qs(history[0]._request.body)
    assert parsed["grant_type"][0] == "password"

    parsed = urllib.parse.parse_qs(history[1]._request.body)
    assert parsed["grant_type"][0] == "refresh_token"

    parsed = urllib.parse.parse_qs(history[2]._request.body)
    assert parsed["grant_type"][0] == "refresh_token"


def test_refresh_access_token_after_refresh_token_expiry(
    requests_mock, config, now, monkeypatch
):
    """Assert that the access token can be refreshed even when the refresh token expires

    Four requests are made to Keycloak:

        - Initial password grant to get the first refresh token (triggered in __init__)
        - Refresh token grant to get the first access token (triggered in __init__)
        - Password grant because the refresh token has expired when calling get_token
        - Refresh token grant to get the final access token when calling get_token
    """
    requests_mock.post(
        config.token_endpoint,
        [
            {
                "json": make_token_response("AT1", "RT1", refresh_expires_in=1)
            },  # initial password grant
            {
                "json": make_token_response("AT_FIRST", "RT_FIRST")
            },  # refresh first access token
            {
                "json": make_token_response("AT2", "RT2")
            },  # password grant due to expired refresh
            {
                "json": make_token_response("AT_FINAL", "RT_FINAL")
            },  # final access token refresh
        ],
    )

    provider = AccessTokenProvider("user", "pwd", config)

    # Advance time so refresh token has expired
    new_now = now + timedelta(hours=2)

    class MockDT:
        @staticmethod
        def now(tz=None):
            return new_now

    monkeypatch.setattr("pasqal_cloud.authentication.datetime", MockDT)

    token = provider.get_token()

    assert token == "AT_FINAL"
    assert provider.refresh_token == "RT_FINAL"

    # Validate sequence of grant_types
    history = requests_mock.request_history
    assert len(history) == 4

    parsed = urllib.parse.parse_qs(history[0]._request.body)
    assert parsed["grant_type"][0] == "password"

    parsed = urllib.parse.parse_qs(history[1]._request.body)
    assert parsed["grant_type"][0] == "refresh_token"

    parsed = urllib.parse.parse_qs(history[2]._request.body)
    assert parsed["grant_type"][0] == "password"

    parsed = urllib.parse.parse_qs(history[3]._request.body)
    assert parsed["grant_type"][0] == "refresh_token"
