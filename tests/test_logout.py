import json
import os
import threading
import time
from urllib.parse import parse_qs

import pytest
from pasqal_cloud import cli, config, token_cache
from pasqal_cloud.config import DEFAULT_PROFILES

from tests.test_token_cache import write

FR = DEFAULT_PROFILES["default-fr"].issuer.rstrip("/")
SA = DEFAULT_PROFILES["default-sa"].issuer.rstrip("/")


def oidc_config(issuer):
    return {
        "authorization_endpoint": f"{issuer}/authorize",
        "token_endpoint": f"{issuer}/token",
        "revocation_endpoint": f"{issuer}/revoke",
        "scopes_supported": ["openid", "offline_access"],
    }


@pytest.fixture(autouse=True)
def _home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / ".pasqal")


@pytest.fixture
def idp(requests_mock):
    for issuer in (FR, SA):
        requests_mock.get(
            f"{issuer}/.well-known/openid-configuration", json=oidc_config(issuer)
        )
        requests_mock.post(f"{issuer}/revoke")
    return requests_mock


def revoked(idp):
    return [
        (r.url.rsplit("/", 1)[0], parse_qs(r.text)["token"][0])
        for r in idp.request_history
        if r.method == "POST"
    ]


def test_logs_out_of_the_profile(idp, capsys):
    write("fr")
    write("sa", "default-sa")
    config.save_config(config.Config(active_profile="default-sa"))
    assert cli.main(["auth", "logout"]) == 0
    assert revoked(idp) == [(SA, "SECRET-REFRESH")]
    assert sorted(token_cache.read_entries()) == ["default-fr"]
    assert not token_cache.lock_path().exists()
    assert "Logged out of default-sa (alice@example.com)" in capsys.readouterr().err


def test_last_entry_deletes_the_file(idp):
    write("fr")
    assert cli.main(["auth", "logout"]) == 0
    assert revoked(idp) == [(FR, "SECRET-REFRESH")]
    assert not token_cache.cache_path().exists()


def test_not_logged_in(idp, capsys):
    write("sa", "dev")
    assert cli.main(["auth", "logout"]) == 0
    assert "Not logged in to default-fr\n" in capsys.readouterr().err
    assert sorted(token_cache.read_entries()) == ["dev"]
    assert not idp.request_history


def test_profile_gone_from_the_config(idp):
    write("fr")
    write("sa", "dev")
    config.save_config(config.Config(active_profile="dev"))
    assert cli.main(["auth", "logout"]) == 0
    assert revoked(idp) == [(SA, "SECRET-REFRESH")]
    assert sorted(token_cache.read_entries()) == ["default-fr"]


def test_discovery_failure_only_skips_revocation(idp, capsys):
    idp.get(f"{FR}/.well-known/openid-configuration", status_code=503)
    write("fr")
    assert cli.main(["auth", "logout"]) == 0
    assert "could not revoke the login of default-fr" in capsys.readouterr().err
    assert not token_cache.cache_path().exists()


def test_revocation_failure_is_a_warning(idp, capsys):
    idp.post(f"{FR}/revoke", status_code=400)
    write("fr")
    assert cli.main(["auth", "logout"]) == 0
    assert "could not revoke" in capsys.readouterr().err
    assert not token_cache.cache_path().exists()


@pytest.mark.usefixtures("idp")
def test_rejected_cache_file(capsys):
    write("fr").chmod(0o644)
    assert cli.main(["auth", "logout"]) == 1
    assert "chmod 600" in capsys.readouterr().err
    assert token_cache.cache_path().exists()
    assert not token_cache.lock_path().exists()


def test_lock_content_and_release():
    with token_cache.lock():
        data = json.loads(token_cache.lock_path().read_text())
        assert data["pid"] == os.getpid()
        assert set(data) == {"host", "pid", "timestamp"}
    assert not token_cache.lock_path().exists()


def test_lock_waits_for_holder():
    order = []

    def waiter():
        with token_cache.lock():
            order.append("waiter")

    with token_cache.lock():
        thread = threading.Thread(target=waiter)
        thread.start()
        time.sleep(0.3)
        order.append("holder")
    thread.join(timeout=5)
    assert order == ["holder", "waiter"]


def test_lock_takes_over_stale_lock():
    path = token_cache.lock_path()
    path.parent.mkdir(mode=0o700)
    path.write_text("{}")
    stale = time.time() - token_cache.LOCK_STALE_AFTER - 1
    os.utime(path, (stale, stale))
    with token_cache.lock():
        assert json.loads(path.read_text())["pid"] == os.getpid()
