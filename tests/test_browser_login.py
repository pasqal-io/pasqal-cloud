import base64
import hashlib
import socket
import threading
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlencode, urlsplit

import jwt
import pytest
from pasqal_cloud import browser_login, cli, token_cache
from pasqal_cloud.endpoints import DEPLOYMENTS

DEPLOYMENT = DEPLOYMENTS[("fr", "prod")]
ISSUER = DEPLOYMENT.issuer.rstrip("/")
CONFIG = {
    "authorization_endpoint": f"{ISSUER}/authorize",
    "token_endpoint": f"{ISSUER}/oauth/token",
    "revocation_endpoint": f"{ISSUER}/oauth/revoke",
    "scopes_supported": ["openid", "profile", "email", "offline_access"],
}


def tokens(email="alice@example.com", refresh="REFRESH-1"):
    claims = {"sub": email, "email": email}
    return {
        "access_token": "ACCESS",
        "refresh_token": refresh,
        "expires_in": 3600,
        "scope": "openid offline_access",
        "id_token": jwt.encode(claims, "x" * 32, "HS256"),
    }


@pytest.fixture
def idp(requests_mock):
    requests_mock.get(f"{ISSUER}/.well-known/openid-configuration", json=CONFIG)
    requests_mock.post(CONFIG["token_endpoint"], json=tokens())
    requests_mock.post(CONFIG["revocation_endpoint"])
    return requests_mock


@pytest.fixture
def browser(monkeypatch):
    """Fake browser: sends a forged callback, then the real one, from a thread."""
    opened = []

    def run(url):
        query = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        redirect = query["redirect_uri"]
        forged = urlencode({"code": "forged", "state": "wrong"})
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(f"{redirect}?{forged}", timeout=5)
        real = urlencode({"code": "CODE", "state": query["state"]})
        urllib.request.urlopen(f"{redirect}?{real}", timeout=5)

    def fake_open(url):
        opened.append(url)
        threading.Thread(target=run, args=(url,), daemon=True).start()
        return True

    monkeypatch.setattr(browser_login.webbrowser, "open", fake_open)
    return opened


def test_login(idp, browser, capsys):
    assert cli.main(["auth", "login"]) == 0
    query = {k: v[0] for k, v in parse_qs(urlsplit(browser[0]).query).items()}
    assert query["scope"] == "openid profile email offline_access"
    assert query["audience"] == DEPLOYMENT.audience
    assert query["code_challenge_method"] == "S256"

    exchange = parse_qs(idp.request_history[-1].text)
    assert exchange["code"] == ["CODE"]  # forged callback ignored
    assert exchange["redirect_uri"] == [query["redirect_uri"]]
    digest = hashlib.sha256(exchange["code_verifier"][0].encode()).digest()
    assert (
        base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        == query["code_challenge"]
    )

    entry = token_cache.read_entries()["fr/prod"]
    assert entry.refresh_token == "REFRESH-1"
    assert entry.id_claims["email"] == "alice@example.com"
    assert entry.refresh_expires_at is None
    err = capsys.readouterr().err
    assert "Logged in to fr/prod as alice@example.com" in err
    assert "REFRESH" not in err


@pytest.mark.usefixtures("browser")
def test_login_revokes_previous_before_new_login(idp, capsys):
    assert cli.main(["auth", "login"]) == 0
    idp.post(CONFIG["token_endpoint"], json=tokens("bob@example.com", "REFRESH-2"))
    assert cli.main(["auth", "login"]) == 0
    entry = token_cache.read_entries()["fr/prod"]
    assert entry.refresh_token == "REFRESH-2"
    posts = [r for r in idp.request_history if r.method == "POST"]
    assert [r.path for r in posts[-2:]] == ["/oauth/revoke", "/oauth/token"]
    assert parse_qs(posts[-2].text)["token"] == ["REFRESH-1"]
    assert "replaced the login of alice@example.com with bob@example.com" in (
        capsys.readouterr().err
    )


@pytest.mark.usefixtures("browser")
def test_revocation_failure_is_a_warning(idp, capsys):
    assert cli.main(["auth", "login"]) == 0
    idp.post(CONFIG["revocation_endpoint"], status_code=503)
    assert cli.main(["auth", "login"]) == 0
    assert "could not revoke" in capsys.readouterr().err


def test_missing_offline_access(idp, capsys):
    config = {**CONFIG, "scopes_supported": ["openid", "profile", "email"]}
    idp.get(f"{ISSUER}/.well-known/openid-configuration", json=config)
    assert cli.main(["auth", "login"]) == 1
    assert "offline_access" in capsys.readouterr().err


def test_missing_token_endpoint(idp, capsys):
    config = {k: v for k, v in CONFIG.items() if k != "token_endpoint"}
    idp.get(f"{ISSUER}/.well-known/openid-configuration", json=config)
    assert cli.main(["auth", "login"]) == 1
    assert "has no token_endpoint" in capsys.readouterr().err


@pytest.mark.usefixtures("browser")
def test_login_refuses_rejected_cache_file(idp, capsys):
    assert cli.main(["auth", "login"]) == 0
    path = token_cache.cache_path()
    path.chmod(0o644)
    content = path.read_bytes()
    assert cli.main(["auth", "login"]) == 1
    assert "chmod 600" in capsys.readouterr().err
    assert path.read_bytes() == content  # never overwritten
    assert not [r for r in idp.request_history if r.path == "/oauth/revoke"]


@pytest.mark.usefixtures("browser")
def test_token_error_without_json(idp, capsys):
    idp.post(CONFIG["token_endpoint"], status_code=502, text="<html>Bad Gateway")
    assert cli.main(["auth", "login"]) == 1
    assert "HTTP 502" in capsys.readouterr().err


@pytest.mark.usefixtures("browser")
def test_token_error(idp, capsys):
    error = {"error": "invalid_grant", "error_description": "bad code"}
    idp.post(CONFIG["token_endpoint"], status_code=400, json=error)
    assert cli.main(["auth", "login"]) == 1
    assert "invalid_grant (bad code)" in capsys.readouterr().err
    assert not token_cache.cache_path().exists()


@pytest.mark.usefixtures("idp")
def test_no_browser(monkeypatch, capsys):
    monkeypatch.setattr(browser_login.webbrowser, "open", lambda _url: False)
    assert cli.main(["auth", "login"]) == 1
    assert "pasqal-cloud auth login --device" in capsys.readouterr().err


@pytest.mark.usefixtures("idp")
def test_no_free_port(monkeypatch, capsys):
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        monkeypatch.setattr(browser_login, "CALLBACK_PORTS", range(port, port + 1))
        assert cli.main(["auth", "login"]) == 1
    assert "pasqal-cloud auth login --device" in capsys.readouterr().err


@pytest.mark.usefixtures("idp")
def test_timeout(monkeypatch, capsys):
    monkeypatch.setattr(browser_login.webbrowser, "open", lambda _url: True)
    monkeypatch.setattr(browser_login, "CALLBACK_TIMEOUT", 0.1)
    assert cli.main(["auth", "login"]) == 1
    assert "Timed out" in capsys.readouterr().err
