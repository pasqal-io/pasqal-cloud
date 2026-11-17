from unittest.mock import patch
from urllib.parse import parse_qs

import pytest
from pasqal_cloud.authentication import (
    ClientCredentialsTokenProvider,
    TokenProviderError,
)
from pasqal_cloud.config import DEFAULT_PROFILES
from pasqal_cloud.http_client import HTTPClient


@pytest.fixture(autouse=True)
def _no_sleep():
    with patch("time.sleep"):
        yield


def mock_idp(requests_mock, profile: str, **token_response):
    """Mock the discovery and token endpoints of `profile`'s issuer, return the
    token endpoint URL."""
    issuer = DEFAULT_PROFILES[profile].issuer.rstrip("/")
    token_endpoint = f"{issuer}/token"

    requests_mock.get(
        f"{issuer}/.well-known/openid-configuration",
        json={
            "authorization_endpoint": f"{issuer}/authorize",
            "token_endpoint": token_endpoint,
            "scopes_supported": ["openid", "offline_access"],
        },
    )
    requests_mock.post(
        token_endpoint,
        **(token_response or {"json": {"access_token": "SA-TOKEN", "expires_in": 300}}),
    )

    return token_endpoint


def token_requests(requests_mock, token_endpoint: str):
    return [
        parse_qs(r.text)
        for r in requests_mock.request_history
        if r.method == "POST" and r.url == token_endpoint
    ]


def provider():
    return ClientCredentialsTokenProvider("my-client", "my-secret")


@pytest.mark.parametrize("region", ["fr", "sa"])
def test_connection_requests_token_from_its_region(requests_mock, region):
    """The connection's region selects the issuer and audience of the client
    credentials grant, and its requests use the resulting token."""
    profile = f"default-{region}"
    token_endpoint = mock_idp(requests_mock, profile)

    client = HTTPClient(region=region, token_provider=provider())

    assert client.user_token() == "SA-TOKEN"
    assert token_requests(requests_mock, token_endpoint) == [
        {
            "grant_type": ["client_credentials"],
            "client_id": ["my-client"],
            "client_secret": ["my-secret"],
            "audience": [DEFAULT_PROFILES[profile].audience],
        }
    ]


def test_invalid_credentials_raise_token_provider_error(requests_mock):
    """Rejected credentials raise a TokenProviderError with the IdP's reason."""
    mock_idp(
        requests_mock,
        "default-sa",
        status_code=401,
        json={"error": "invalid_client", "error_description": "Bad secret"},
    )
    client = HTTPClient(region="sa", token_provider=provider())

    with pytest.raises(TokenProviderError, match="invalid_client.*Bad secret"):
        client.user_token()


def test_standalone_provider_uses_active_profile(requests_mock):
    """Outside a connection, the token comes from the active profile
    (default-fr here), requested on first use only."""
    token_endpoint = mock_idp(requests_mock, "default-fr")

    standalone = provider()
    assert not requests_mock.request_history

    assert standalone.get_token() == "SA-TOKEN"
    assert len(token_requests(requests_mock, token_endpoint)) == 1


def test_valid_token_is_reused(requests_mock):
    token_endpoint = mock_idp(requests_mock, "default-fr")

    client = HTTPClient(token_provider=provider())
    client.user_token()
    client.user_token()

    assert len(token_requests(requests_mock, token_endpoint)) == 1


def test_expiring_token_is_requested_again(requests_mock):
    """A token inside the 1 min expiry window is replaced by a new one."""
    token_endpoint = mock_idp(
        requests_mock, "default-fr", json={"access_token": "T", "expires_in": 30}
    )

    client = HTTPClient(token_provider=provider())
    client.user_token()
    client.user_token()

    assert len(token_requests(requests_mock, token_endpoint)) == 2


def test_transient_errors_are_retried(requests_mock):
    """A transient token endpoint error is retried."""
    token_endpoint = mock_idp(
        requests_mock,
        "default-fr",
        response_list=[
            {"status_code": 503, "text": "<html>Unavailable</html>"},
            {"json": {"access_token": "SA-TOKEN", "expires_in": 300}},
        ],
    )

    client = HTTPClient(token_provider=provider())

    assert client.user_token() == "SA-TOKEN"
    assert len(token_requests(requests_mock, token_endpoint)) == 2
