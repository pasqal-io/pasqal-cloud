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

import os
import stat
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, TypeAdapter

from pasqal_cloud import config
from pasqal_cloud.config import ProfileConfig


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


_ENTRIES: TypeAdapter[dict[str, CacheEntry]] = TypeAdapter(dict[str, CacheEntry])


def cache_path() -> Path:
    return config.CONFIG_DIR / "cloud-credentials.json"


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
            raise TokenCacheError(f"{path} is not a valid cache file: {e}") from e

    return entries


def write_entries(entries: dict[str, CacheEntry]) -> None:
    """Atomically replace the cache file, readable by the current user only.

    The file is deleted when no entry is left.
    """
    path = cache_path()
    if not entries:
        path.unlink(missing_ok=True)
        return

    config.write_private_file(path, _ENTRIES.dump_json(entries).decode())
