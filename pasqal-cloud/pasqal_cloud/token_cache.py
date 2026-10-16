"""On-disk cache of interactive logins: a single private JSON file,
`~/.pasqal/cloud-credentials.json`, with one entry per region/env."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Optional

from pasqal_cloud.endpoints import LoginPreset


class TokenCacheError(Exception):
    pass


@dataclass
class CacheEntry:
    region: str
    env: str
    # The preset is kept so an entry stays usable (status, logout) after a
    # client ID or issuer changes in LOGIN_PRESETS.
    issuer: str
    client_id: str
    refresh_token: str
    access_token: str
    expires_at: int
    scope: str = ""
    # Only Keycloak returns the refresh token lifetime.
    refresh_expires_at: Optional[int] = None
    # Decoded from the id_token without signature check: display only.
    id_claims: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return entry_key(self.region, self.env)

    def matches(self, preset: LoginPreset) -> bool:
        """False once the preset changed (new client, issuer...): not logged in."""
        return (self.issuer, self.client_id) == (preset.issuer, preset.client_id)


# Expected JSON types of CacheEntry fields, str when not listed.
_TYPES: dict[str, Any] = {
    "expires_at": int,
    "refresh_expires_at": (int, type(None)),
    "id_claims": dict,
}


def cache_dir() -> Path:
    return Path.home() / ".pasqal"


def cache_path() -> Path:
    return cache_dir() / "cloud-credentials.json"


def entry_key(region: str, env: str) -> str:
    return f"{region}/{env}"


def _parse_entry(key: str, data: Any) -> CacheEntry:
    # Unknown keys are dropped so files written by newer versions still load.
    names = {fld.name for fld in fields(CacheEntry)}
    entry = CacheEntry(**{k: v for k, v in data.items() if k in names})
    for name in names:
        if not isinstance(getattr(entry, name), _TYPES.get(name, str)):
            raise TypeError(f"{key}: {name} has an invalid type")
    if entry.key != key:
        raise ValueError(f"{key}: entry is for {entry.key}")
    return entry


def read_entries() -> dict[str, CacheEntry]:
    """Return the cached entries by key, empty if there is no cache file.

    Raises TokenCacheError if the file is too permissive, not owned by the
    current user, or unreadable. It is never repaired: it may already have leaked.
    """
    path = cache_path()
    try:
        f = open(path, encoding="utf-8")
    except FileNotFoundError:
        return {}
    with f:
        st = os.fstat(f.fileno())
        # POSIX only, Windows has no uid/mode bits to check.
        if hasattr(os, "getuid"):
            if st.st_uid != os.getuid():
                raise TokenCacheError(
                    f"{path} is not owned by the current user, refusing to use it"
                )
            if st.st_mode & 0o077:
                raise TokenCacheError(
                    f"{path} has permissions {stat.filemode(st.st_mode)}, refusing "
                    "to use it. If no one else could have read it, run: "
                    f"chmod 600 {path}"
                )
        try:
            data = json.load(f)
            return {key: _parse_entry(key, value) for key, value in data.items()}
        except (ValueError, TypeError, AttributeError) as e:
            raise TokenCacheError(f"{path} is not a valid cache file: {e}") from e


def write_entries(entries: dict[str, CacheEntry]) -> None:
    """Atomically replace the cache file, readable by the current user only.

    The file is deleted when no entry is left.
    """
    path = cache_path()
    if not entries:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # mkstemp creates the file with mode 0600.
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({key: asdict(entry) for key, entry in entries.items()}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise
