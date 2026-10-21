"""On-disk cache of interactive logins: a single private JSON file,
`~/.pasqal/cloud-credentials.json`, with one entry per region/env."""

from __future__ import annotations

import json
import os
import socket
import stat
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Optional

from pasqal_cloud import oidc
from pasqal_cloud.endpoints import DeploymentConf, PasqalCloudTarget

# Seconds after which a lock is considered abandoned and taken over: well
# above the worst case of the network calls made under it.
LOCK_STALE_AFTER = 180


class TokenCacheError(Exception):
    pass


@dataclass
class CacheEntry:
    region: str
    env: str
    # The deployment is kept so an entry stays usable (status, logout) after a
    # client ID or issuer changes in DEPLOYMENTS.
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

    def matches(self, deployment: DeploymentConf) -> bool:
        """False once the deployment changed (new client, issuer...): not logged in."""
        return (self.issuer, self.client_id) == (
            deployment.issuer,
            deployment.client_id,
        )

    @classmethod
    def from_tokens(
        cls, target: PasqalCloudTarget, tokens: dict[str, Any]
    ) -> CacheEntry:
        """A new entry of `target` holding the tokens of a token endpoint response.

        Raises KeyError, TypeError, ValueError or OIDCError on an invalid response.
        """
        empty = cls(
            region=target.region,
            env=target.env,
            issuer=target.deployment.issuer,
            client_id=target.deployment.client_id,
            refresh_token="",
            access_token="",
            expires_at=0,
        )
        return empty.updated(tokens)

    def updated(self, tokens: dict[str, Any]) -> CacheEntry:
        """Return a copy holding the tokens of a token endpoint response.

        The refresh token and id claims are kept when the response has none.
        Raises KeyError, TypeError, ValueError or OIDCError on an invalid response.
        """
        now = int(time.time())
        return replace(
            self,
            access_token=str(tokens["access_token"]),
            expires_at=now + int(tokens["expires_in"]),
            refresh_token=str(tokens.get("refresh_token", self.refresh_token)),
            scope=str(tokens.get("scope", self.scope)),
            refresh_expires_at=(
                now + int(tokens["refresh_expires_in"])
                if tokens.get("refresh_expires_in")  # Keycloak: 0 means no expiry
                else None
            ),
            id_claims=(
                oidc.id_claims(tokens["id_token"])
                if "id_token" in tokens
                else self.id_claims
            ),
        )


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


def lock_path() -> Path:
    return cache_path().with_name(cache_path().name + ".lock")


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
            raise TokenCacheError(
                f"{path} is not a valid cache file: {e}. Delete it and log in again"
            ) from e


@contextmanager
def lock() -> Iterator[None]:
    """Hold the cache lock file, to wrap every read-modify-write of the cache.

    `O_CREAT | O_EXCL` is atomic on local disks and NFS, so the lock also works
    across hosts. A lock older than LOCK_STALE_AFTER (by its mtime, set by the
    file server) is taken over; two processes taking over the same stale lock
    at once can both get it, accepted given how rare an abandoned lock is.
    """
    path = lock_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            pass

        try:
            age = time.time() - path.stat().st_mtime
        except FileNotFoundError:
            continue  # released meanwhile

        if age > LOCK_STALE_AFTER:
            path.unlink(missing_ok=True)
        else:
            time.sleep(0.1)

    try:
        # For whoever finds a stuck lock: who holds it, since when.
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "host": socket.gethostname(),
                    "pid": os.getpid(),
                    "timestamp": int(time.time()),
                },
                f,
            )
        yield
    finally:
        path.unlink(missing_ok=True)


def write_entries(entries: dict[str, CacheEntry]) -> None:
    """Atomically replace the cache file, readable by the current user only.

    Call it under lock(), after reading the entries in the same lock.

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
