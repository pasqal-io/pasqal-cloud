import json
import os
import stat
import time

import pytest
from pasqal_cloud import config, token_cache
from pasqal_cloud.cli import _format_expiry, main
from pasqal_cloud.config import DEFAULT_PROFILES

from tests.utils import posix_only


@pytest.fixture(autouse=True)
def _home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / ".pasqal")


def make_entry(region="fr", email="alice@example.com"):
    profile_config = DEFAULT_PROFILES[f"default-{region}"]
    return token_cache.CacheEntry(
        issuer=profile_config.issuer,
        client_id=profile_config.client_id,
        audience=profile_config.audience,
        refresh_token="SECRET-REFRESH",
        access_token="SECRET-ACCESS",
        expires_at=int(time.time()) + 3600,
        id_claims={"sub": "auth0|1", "email": email},
    )


def write(region="fr", profile="default-fr", **kwargs):
    entries = token_cache.read_entries()
    entry = make_entry(region, **kwargs)
    token_cache.write_entries({**entries, profile: entry})
    return token_cache.cache_path()


def test_round_trip_and_permissions():
    path = write()
    assert path.name == "cloud-credentials.json"
    if os.name != "nt":
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert token_cache.read_entries() == {"default-fr": make_entry()}
    assert os.listdir(path.parent) == [path.name]  # no temp file left


def test_one_entry_per_profile():
    write("fr", "default-fr", email="alice@example.com")
    write("sa", "dev", email="bob@example.com")
    write("fr", "default-fr", email="carol@example.com")
    entries = token_cache.read_entries()
    assert sorted(entries) == ["default-fr", "dev"]
    assert entries["default-fr"].id_claims["email"] == "carol@example.com"


def test_writing_no_entry_deletes_file():
    path = write()
    token_cache.write_entries({})
    assert not path.exists()
    token_cache.write_entries({})  # already gone


def test_missing_file():
    assert token_cache.read_entries() == {}


def test_matches_profile_config():
    entry = make_entry()
    assert entry.matches(DEFAULT_PROFILES["default-fr"])
    assert not entry.matches(DEFAULT_PROFILES["default-sa"])

    for key in ("issuer", "client_id", "audience"):
        changed = DEFAULT_PROFILES["default-fr"].model_copy(update={key: "other"})
        assert not entry.matches(changed), key


@posix_only
def test_rejects_permissive_file():
    path = write()
    path.chmod(0o644)
    with pytest.raises(token_cache.TokenCacheError, match=f"chmod 600 {path}"):
        token_cache.read_entries()
    assert stat.S_IMODE(path.stat().st_mode) == 0o644  # never repaired


@posix_only
def test_rejects_foreign_owner(monkeypatch):
    path = write()
    monkeypatch.setattr(os, "getuid", lambda: os.stat(path).st_uid + 1)
    with pytest.raises(token_cache.TokenCacheError, match="not owned"):
        token_cache.read_entries()


def test_rejects_unreadable_file():
    token_cache.cache_path().mkdir(parents=True)
    with pytest.raises(token_cache.TokenCacheError, match="is unreadable"):
        token_cache.read_entries()


def test_rejects_corrupt_file():
    path = write()
    path.write_text("{")
    with pytest.raises(token_cache.TokenCacheError, match="not a valid cache file"):
        token_cache.read_entries()


def test_keeps_unknown_keys():
    path = write()
    data = json.loads(path.read_text())
    data["default-fr"]["added_later"] = 1
    path.write_text(json.dumps(data))

    entries = token_cache.read_entries()
    assert entries["default-fr"].model_extra == {"added_later": 1}

    write("sa", "dev")  # rewriting the file for another profile
    assert json.loads(path.read_text())["default-fr"]["added_later"] == 1


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("expires_at", "soon"),
        ("id_claims", []),
        ("access_token", None),
    ],
)
def test_rejects_wrong_types(key, value):
    path = write()
    data = json.loads(path.read_text())
    data["default-fr"][key] = value
    path.write_text(json.dumps(data))
    with pytest.raises(token_cache.TokenCacheError, match=f"default-fr.{key}"):
        token_cache.read_entries()


@pytest.mark.parametrize("content", ["[]", "null", '{"default-fr": []}'])
def test_rejects_non_object(content):
    path = write()
    path.write_text(content)
    with pytest.raises(token_cache.TokenCacheError, match="not a valid cache file"):
        token_cache.read_entries()


def test_status_not_logged_in(capsys):
    assert main(["auth", "status"]) == 1
    out, err = capsys.readouterr()
    assert f"Cache file: {token_cache.cache_path()}" in out
    assert (
        "Profile:    default-fr (from default)\n"
        "Issuer:     https://authenticate.pasqal.cloud/\n"
    ) in out
    assert "Not logged in to default-fr" in err


def test_status_lists_entries_and_marks_active(capsys):
    write("fr", "default-fr", email="alice@example.com")
    write("sa", "dev", email="bob@example.com")
    config.save_config(
        config.Config(
            active_profile="dev", profiles={"dev": DEFAULT_PROFILES["default-sa"]}
        )
    )
    assert main(["auth", "status"]) == 0
    out, _ = capsys.readouterr()
    assert (
        "Profile:    dev (from active profile)\n"
        "Issuer:     https://auth.sa.pasqal.cloud/realms/pasqal-cloud\n"
    ) in out
    assert (
        "* dev (active)\n"
        "    Issuer:         https://auth.sa.pasqal.cloud/realms/pasqal-cloud\n"
        "    User:           bob@example.com\n"
    ) in out
    assert (
        "  default-fr\n" "    Issuer:         https://authenticate.pasqal.cloud/\n"
    ) in out
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
    data["default-fr"]["client_id"] = "old-client"
    path.write_text(json.dumps(data))
    assert main(["auth", "status"]) == 1
    out, err = capsys.readouterr()
    assert "  default-fr\n" in out
    assert "(active)" not in out
    assert "Not logged in to default-fr" in err


@posix_only
def test_status_reports_bad_file(capsys):
    write().chmod(0o644)
    assert main(["auth", "status"]) == 1
    assert "chmod 600" in capsys.readouterr().err


def test_save_login_writes_entry():
    from pasqal_cloud.cli import _save_login
    from pasqal_cloud.config import resolve_profile

    tokens = {"refresh_token": "R", "access_token": "A", "expires_in": 60}
    entry = _save_login(resolve_profile(), tokens)
    assert token_cache.read_entries() == {"default-fr": entry}
