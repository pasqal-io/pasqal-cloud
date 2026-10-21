import base64
import hashlib
from urllib.parse import parse_qs

import jwt
import pytest
from pasqal_cloud import cli, device_login, token_cache
from pasqal_cloud.endpoints import DEPLOYMENTS

DEPLOYMENT = DEPLOYMENTS[("fr", "prod")]
ISSUER = DEPLOYMENT.issuer.rstrip("/")
CONFIG = {
    "authorization_endpoint": f"{ISSUER}/authorize",
    "token_endpoint": f"{ISSUER}/oauth/token",
    "revocation_endpoint": f"{ISSUER}/oauth/revoke",
    "device_authorization_endpoint": f"{ISSUER}/oauth/device/code",
    "scopes_supported": ["openid", "profile", "email", "offline_access"],
}
DEVICE_CODE = {
    "device_code": "DEVICE",
    "user_code": "W7KD-PQL9",
    "verification_uri": f"{ISSUER}/activate",
    "expires_in": 60,
    "interval": 2,
}
TOKENS = {
    "access_token": "ACCESS",
    "refresh_token": "REFRESH",
    "expires_in": 3600,
    "id_token": jwt.encode({"sub": "alice", "email": "alice@example.com"}, "x" * 32),
}


def error(code, status=400):
    return {"json": {"error": code}, "status_code": status}


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(device_login, "time", fake)
    return fake


@pytest.fixture
def idp(requests_mock):
    requests_mock.get(f"{ISSUER}/.well-known/openid-configuration", json=CONFIG)
    requests_mock.post(CONFIG["device_authorization_endpoint"], json=DEVICE_CODE)
    requests_mock.post(CONFIG["revocation_endpoint"])
    return requests_mock


def test_device_login(idp, clock, capsys):
    idp.post(
        CONFIG["token_endpoint"],
        [
            error("authorization_pending", 403),  # Auth0 status
            error("slow_down", 429),
            {"json": TOKENS},
        ],
    )

    assert cli.main(["auth", "login", "--device"]) == 0
    assert clock.sleeps == [2, 2, 7]  # interval, then +5 after slow_down

    posts = [parse_qs(r.text) for r in idp.request_history if r.method == "POST"]
    assert posts[0]["scope"] == ["openid profile email offline_access"]
    assert posts[0]["audience"] == [DEPLOYMENT.audience]
    assert posts[0]["client_id"] == [DEPLOYMENT.client_id]
    assert posts[-1]["grant_type"] == [device_login.GRANT_TYPE]
    assert posts[-1]["device_code"] == ["DEVICE"]

    digest = hashlib.sha256(posts[-1]["code_verifier"][0].encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    assert posts[0]["code_challenge"] == [challenge]
    assert posts[0]["code_challenge_method"] == ["S256"]

    assert token_cache.read_entries()["fr/prod"].refresh_token == "REFRESH"

    err = capsys.readouterr().err
    assert f"Open {ISSUER}/activate on another device" in err
    assert "enter code: W7KD-PQL9" in err
    assert "Logged in to fr/prod as alice@example.com" in err


def test_device_flow_not_enabled(idp, capsys):
    config = {k: v for k, v in CONFIG.items() if k != "device_authorization_endpoint"}
    idp.get(f"{ISSUER}/.well-known/openid-configuration", json=config)

    assert cli.main(["auth", "login", "--device"]) == 1
    assert "Device flow not enabled for this environment" in capsys.readouterr().err
    assert [r.method for r in idp.request_history] == ["GET"]


def test_device_code_expires(idp, clock, capsys):
    idp.post(CONFIG["token_endpoint"], **error("authorization_pending"))

    assert cli.main(["auth", "login", "--device"]) == 1
    assert "device code expired" in capsys.readouterr().err
    assert clock.now == 60
    assert not token_cache.cache_path().exists()


@pytest.mark.usefixtures("clock")
def test_access_denied(idp, capsys):
    idp.post(CONFIG["token_endpoint"], **error("access_denied", 403))

    assert cli.main(["auth", "login", "--device"]) == 1
    assert "access_denied" in capsys.readouterr().err
    assert not token_cache.cache_path().exists()


def test_invalid_device_authorization_response(idp, capsys):
    idp.post(CONFIG["device_authorization_endpoint"], json={"device_code": "X"})

    assert cli.main(["auth", "login", "--device"]) == 1
    assert "Invalid device authorization response" in capsys.readouterr().err
