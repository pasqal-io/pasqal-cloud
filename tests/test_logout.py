import json
import os
import threading
import time
from urllib.parse import parse_qs

import pytest
from pasqal_cloud import cli, token_cache
from pasqal_cloud.endpoints import DEPLOYMENTS

from tests.test_token_cache import write

FR = DEPLOYMENTS[("fr", "prod")].issuer.rstrip("/")
SA_DEV = DEPLOYMENTS[("sa", "dev")].issuer.rstrip("/")


def config(issuer):
    return {
        "authorization_endpoint": f"{issuer}/authorize",
        "token_endpoint": f"{issuer}/token",
        "revocation_endpoint": f"{issuer}/revoke",
        "scopes_supported": ["openid", "offline_access"],
    }


@pytest.fixture
def idp(requests_mock):
    for issuer in (FR, SA_DEV):
        requests_mock.get(
            f"{issuer}/.well-known/openid-configuration", json=config(issuer)
        )
        requests_mock.post(f"{issuer}/revoke")
    return requests_mock


def revoked(idp):
    return [
        (r.url.rsplit("/", 1)[0], parse_qs(r.text)["token"][0])
        for r in idp.request_history
        if r.method == "POST"
    ]


def test_single_entry(idp, capsys):
    write("sa", "dev")
    assert cli.main(["auth", "logout"]) == 0
    assert revoked(idp) == [(SA_DEV, "SECRET-REFRESH")]
    assert not token_cache.cache_path().exists()
    assert not token_cache.lock_path().exists()
    assert "Logged out of sa/dev (alice@example.com)" in capsys.readouterr().err


def test_no_entry(idp, capsys):
    assert cli.main(["auth", "logout"]) == 0
    assert "Not logged in\n" in capsys.readouterr().err
    assert not idp.request_history


def test_several_entries_need_a_choice(idp, capsys):
    write("fr", "prod")
    write("sa", "dev")
    assert cli.main(["auth", "logout"]) == 1
    err = capsys.readouterr().err
    assert "  pasqal-cloud auth logout --region fr\n" in err
    assert "  PASQAL_CLOUD_ENV=dev pasqal-cloud auth logout --region sa\n" in err
    assert sorted(token_cache.read_entries()) == ["fr/prod", "sa/dev"]
    assert not idp.request_history


@pytest.mark.parametrize(
    ("argv", "env"),
    [
        (["--region", "sa"], {"PASQAL_CLOUD_ENV": "dev"}),
        ([], {"PASQAL_CLOUD_REGION": "sa", "PASQAL_CLOUD_ENV": "dev"}),
    ],
)
def test_explicit_entry(idp, monkeypatch, argv, env):
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    write("fr", "prod")
    write("sa", "dev")
    assert cli.main(["auth", "logout", *argv]) == 0
    assert revoked(idp) == [(SA_DEV, "SECRET-REFRESH")]
    assert sorted(token_cache.read_entries()) == ["fr/prod"]


@pytest.mark.usefixtures("idp")
def test_explicit_entry_not_logged_in(capsys):
    write("fr", "prod")
    assert cli.main(["auth", "logout", "--region", "sa"]) == 0
    assert "Not logged in to sa/prod" in capsys.readouterr().err
    assert sorted(token_cache.read_entries()) == ["fr/prod"]


def test_discovery_failure_only_skips_revocation(idp, capsys):
    idp.get(f"{FR}/.well-known/openid-configuration", status_code=503)
    write("fr", "prod")
    assert cli.main(["auth", "logout"]) == 0
    assert "could not revoke the login of fr/prod" in capsys.readouterr().err
    assert not token_cache.cache_path().exists()


def test_revocation_failure_is_a_warning(idp, capsys):
    idp.post(f"{FR}/revoke", status_code=400)
    write("fr", "prod")
    assert cli.main(["auth", "logout"]) == 0
    assert "could not revoke" in capsys.readouterr().err
    assert not token_cache.cache_path().exists()


@pytest.mark.usefixtures("idp")
def test_rejected_cache_file(capsys):
    write("fr", "prod").chmod(0o644)
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
