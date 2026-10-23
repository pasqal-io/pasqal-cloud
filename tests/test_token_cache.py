import json
import os
import stat
import time

import pytest
from pasqal_cloud import token_cache
from pasqal_cloud.cli import _format_expiry, main
from pasqal_cloud.endpoints import DEPLOYMENTS


def make_entry(region="fr", env="prod", email="alice@example.com"):
    deployment = DEPLOYMENTS[(region, env)]
    return token_cache.CacheEntry(
        region=region,
        env=env,
        issuer=deployment.issuer,
        client_id=deployment.client_id,
        refresh_token="SECRET-REFRESH",
        access_token="SECRET-ACCESS",
        expires_at=int(time.time()) + 3600,
        id_claims={"sub": "auth0|1", "email": email},
    )


def write(region="fr", env="prod", **kwargs):
    entries = token_cache.read_entries()
    entry = make_entry(region, env, **kwargs)
    token_cache.write_entries({**entries, entry.key: entry})
    return token_cache.cache_path()


def test_round_trip_and_permissions():
    path = write()
    assert path.name == "cloud-credentials.json"
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert token_cache.read_entries() == {"fr/prod": make_entry()}
    assert os.listdir(path.parent) == [path.name]  # no temp file left


def test_one_entry_per_region_env():
    write("fr", "prod", email="alice@example.com")
    write("sa", "dev", email="bob@example.com")
    write("fr", "prod", email="carol@example.com")
    entries = token_cache.read_entries()
    assert sorted(entries) == ["fr/prod", "sa/dev"]
    assert entries["fr/prod"].id_claims["email"] == "carol@example.com"


def test_writing_no_entry_deletes_file():
    path = write()
    token_cache.write_entries({})
    assert not path.exists()
    token_cache.write_entries({})  # already gone


def test_missing_file():
    assert token_cache.read_entries() == {}


def test_matches_deployment():
    entry = make_entry()
    assert entry.matches(DEPLOYMENTS[("fr", "prod")])
    assert not entry.matches(DEPLOYMENTS[("sa", "prod")])


def test_rejects_permissive_file():
    path = write()
    path.chmod(0o644)
    with pytest.raises(token_cache.TokenCacheError, match=f"chmod 600 {path}"):
        token_cache.read_entries()
    assert stat.S_IMODE(path.stat().st_mode) == 0o644  # never repaired


def test_rejects_foreign_owner(monkeypatch):
    path = write()
    monkeypatch.setattr(os, "getuid", lambda: os.stat(path).st_uid + 1)
    with pytest.raises(token_cache.TokenCacheError, match="not owned"):
        token_cache.read_entries()


def test_rejects_corrupt_file():
    path = write()
    path.write_text("{")
    with pytest.raises(token_cache.TokenCacheError, match="not a valid cache file"):
        token_cache.read_entries()


def test_ignores_unknown_keys():
    path = write()
    data = json.loads(path.read_text())
    data["fr/prod"]["added_later"] = 1
    path.write_text(json.dumps(data))
    assert token_cache.read_entries() == {"fr/prod": make_entry()}


@pytest.mark.parametrize(
    ("key", "value"),
    [("expires_at", "soon"), ("id_claims", []), ("access_token", None)],
)
def test_rejects_wrong_types(key, value):
    path = write()
    data = json.loads(path.read_text())
    data["fr/prod"][key] = value
    path.write_text(json.dumps(data))
    with pytest.raises(token_cache.TokenCacheError, match=f"{key} has an invalid"):
        token_cache.read_entries()


def test_rejects_entry_under_wrong_key():
    path = write()
    data = json.loads(path.read_text())
    path.write_text(json.dumps({"sa/prod": data["fr/prod"]}))
    with pytest.raises(token_cache.TokenCacheError, match="entry is for fr/prod"):
        token_cache.read_entries()


@pytest.mark.parametrize("content", ["[]", "null", '{"fr/prod": []}'])
def test_rejects_non_object(content):
    path = write()
    path.write_text(content)
    with pytest.raises(token_cache.TokenCacheError, match="not a valid cache file"):
        token_cache.read_entries()


def test_status_not_logged_in(capsys):
    assert main(["auth", "status"]) == 1
    out, err = capsys.readouterr()
    assert f"Cache file: {token_cache.cache_path()}" in out
    assert "Region:     fr   (from default)\nEnv:        prod (from default)\n" in out
    assert "Not logged in to fr/prod" in err


def test_status_lists_entries_and_marks_active(monkeypatch, capsys):
    write("fr", "prod", email="alice@example.com")
    write("sa", "dev", email="bob@example.com")
    monkeypatch.setenv("PASQAL_CLOUD_ENV", "dev")
    assert main(["auth", "status", "--region", "sa"]) == 0
    out, _ = capsys.readouterr()
    assert "Region:     sa   (from --region)\n" in out
    assert "Env:        dev  (from PASQAL_CLOUD_ENV)\n" in out
    assert (
        "* sa/dev (active)\n"
        "    Region:         sa\n"
        "    Env:            dev\n"
        "    User:           bob@example.com\n"
    ) in out
    assert "  fr/prod\n    Region:         fr\n" in out
    assert "Access token:   expires " in out
    assert "Refresh token:  expiry unknown" in out
    assert "SECRET" not in out


@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (30, "(in less than 1 min)"),
        (2 * 3600 + 5, "(in 2 h)"),
        (86400 + 5, "(in 1 day)"),
        (13 * 86400 + 5, "(in 13 days)"),
        (-3 * 60 - 5, "(3 min ago)"),
    ],
)
def test_format_expiry(offset, expected):
    text = _format_expiry(int(time.time()) + offset)
    assert text.endswith(expected)
    assert text.startswith("expires" if offset > 0 else "expired")


def test_status_ignores_entry_for_another_client(capsys):
    path = write()
    data = json.loads(path.read_text())
    data["fr/prod"]["client_id"] = "old-client"
    path.write_text(json.dumps(data))
    assert main(["auth", "status"]) == 1
    out, err = capsys.readouterr()
    assert "  fr/prod\n" in out
    assert "(active)" not in out
    assert "Not logged in to fr/prod" in err


def test_status_reports_bad_file(capsys):
    write().chmod(0o644)
    assert main(["auth", "status"]) == 1
    assert "chmod 600" in capsys.readouterr().err


def test_save_login_writes_entry():
    from pasqal_cloud.cli import _save_login
    from pasqal_cloud.endpoints import resolve_pasqal_cloud_target

    tokens = {"refresh_token": "R", "access_token": "A", "expires_in": 60}
    entry = _save_login(resolve_pasqal_cloud_target("fr"), tokens)
    assert token_cache.read_entries() == {entry.key: entry}
