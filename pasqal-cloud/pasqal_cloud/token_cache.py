# Copyright 2026 Pasqal Cloud Services development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""On-disk cache of interactive logins: a single private JSON file,
`~/.pasqal/cloud-credentials.json`, with one entry per config profile."""

from __future__ import annotations

import json
import os
import socket
import stat
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, TypeAdapter

from pasqal_cloud import config, oidc
from pasqal_cloud.config import PasqalCloudProfile, ProfileConfig

# Seconds after which a lock is considered abandoned and taken over: well
# above the worst case of the network calls made under it.
LOCK_STALE_AFTER = 180


class TokenCacheError(Exception):
    pass


class CacheEntry(BaseModel):
    # Unknown keys are kept, so an entry written by a newer version survives
    # being loaded and saved by an older one.
    model_config = ConfigDict(extra="allow")

    # The login settings are kept so an entry stays usable (status, logout)
    # after they change in DEFAULT_PROFILES or the profile.
    issuer: str
    client_id: str
    # Auth0 issues access tokens for this API and keeps it on refresh. Keycloak
    # ignores it, its audience comes from the client's mappers.
    audience: str
    refresh_token: str
    access_token: str
    expires_at: int
    scope: str = ""
    # Only Keycloak returns the refresh token lifetime.
    refresh_expires_at: int | None = None
    # Decoded from the id_token without signature check: display only.
    id_claims: dict[str, Any] = {}

    def matches(self, profile_config: ProfileConfig) -> bool:
        """False once the login settings of the profile changed: not logged in."""
        return (self.issuer, self.client_id, self.audience) == (
            profile_config.issuer,
            profile_config.client_id,
            profile_config.audience,
        )

    @classmethod
    def from_tokens(
        cls, profile: PasqalCloudProfile, tokens: dict[str, Any]
    ) -> CacheEntry:
        """A new entry of `profile` holding the tokens of a token endpoint response.

        Raises KeyError, TypeError, ValueError or OIDCError on an invalid response.
        """
        empty = cls(
            issuer=profile.config.issuer,
            client_id=profile.config.client_id,
            audience=profile.config.audience,
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
        return self.model_copy(
            update={
                "access_token": str(tokens["access_token"]),
                "expires_at": now + int(tokens["expires_in"]),
                "refresh_token": str(tokens.get("refresh_token", self.refresh_token)),
                "scope": str(tokens.get("scope", self.scope)),
                "refresh_expires_at": (
                    now + int(tokens["refresh_expires_in"])
                    if tokens.get("refresh_expires_in")  # Keycloak: 0 means no expiry
                    else None
                ),
                "id_claims": (
                    oidc.id_claims(tokens["id_token"])
                    if "id_token" in tokens
                    else self.id_claims
                ),
            }
        )


_ENTRIES: TypeAdapter[dict[str, CacheEntry]] = TypeAdapter(dict[str, CacheEntry])


def cache_path() -> Path:
    return config.CONFIG_DIR / "cloud-credentials.json"


def lock_path() -> Path:
    return cache_path().with_name(cache_path().name + ".lock")


def entry_for(
    entries: dict[str, CacheEntry], profile: PasqalCloudProfile
) -> CacheEntry | None:
    """The login of `profile`, None if missing or made for another issuer or client."""
    entry = entries.get(profile.name)
    if entry is None or not entry.matches(profile.config):
        return None

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
    except OSError as e:
        raise TokenCacheError(f"{path} is unreadable: {e}") from e

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
            entries = _ENTRIES.validate_json(f.read())
        except ValueError as e:  # pydantic's ValidationError is a ValueError
            raise TokenCacheError(
                f"{path} is not a valid cache file: {e}. Delete it and log in again"
            ) from e

    return entries


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

    It replaces every entry: call it under lock(), with entries read in the
    same lock, or a concurrent login or logout is lost.

    The file is deleted when no entry is left.
    """
    path = cache_path()
    if not entries:
        path.unlink(missing_ok=True)
        return

    config.write_private_file(path, _ENTRIES.dump_json(entries).decode())
