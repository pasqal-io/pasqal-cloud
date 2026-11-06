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
"""User config of the `pasqal-cloud` CLI, stored in `~/.pasqal/config.json`.

The config holds named profiles, so devs can switch between environments. A
profile is one environment in one region, with every key of
`ProfileConfig` set. Layout:

    {
        "active_profile": "preprod-fr",
        "profiles": {
            "preprod-fr": {
                "issuer": "...",
                "client_id": "...",
                "audience": "...",
                "core_url": "...",
                "account_url": "..."
            }
        }
    }

The read-only `default-<region>` profiles always exist and hold the prod
presets built from `pasqal_cloud.endpoints`. Without an active profile, `default-fr`
is used.
"""

from __future__ import annotations

import os
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, get_args
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
    StringConstraints,
    ValidationError,
    ValidationInfo,
)

from pasqal_cloud.endpoints import (
    ACCOUNT_API_URL,
    AUDIENCE,
    AUTH0_DOMAIN,
    CORE_API_URL,
    KEYCLOAK_REALM,
    KEYCLOAK_SDK_CLIENT_ID,
    KSA_ACCOUNT_API_URL,
    KSA_CORE_API_URL,
    PUBLIC_CLIENT_ID,
    Region,
    SA_KEYCLOAK_BASE_URL,
)

REGIONS: tuple[Region, ...] = get_args(Region)
URL_KEYS = ("issuer", "core_url", "account_url")
LOOPBACK_HOSTS = ("localhost", "127.0.0.1")

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def check_url(key: str, value: str) -> str:
    """Reject non-http(s) URLs, and warn on plain HTTP outside loopback hosts:
    tokens sent there can be read on the network."""
    url = urlparse(value)
    if url.scheme not in ("http", "https") or not url.hostname:
        raise ValueError(f"Invalid {key} {value!r}: expected an https:// URL")

    if url.scheme == "http" and url.hostname not in LOOPBACK_HOSTS:
        warnings.warn(
            f"{key} {value!r} isn't https: tokens sent to it can be read on the "
            "network",
            stacklevel=2,
        )

    return value


class ProfileConfig(BaseModel):
    """Where to log in and which APIs to call. Each field is a key of a user
    config profile.

    Unknown keys are kept, so a config written by a newer version survives
    being loaded and saved by an older one."""

    model_config = ConfigDict(frozen=True, extra="allow")

    issuer: NonEmptyStr
    client_id: NonEmptyStr
    audience: NonEmptyStr
    core_url: NonEmptyStr
    account_url: NonEmptyStr

    @field_validator(*URL_KEYS)
    @classmethod
    def _check_url(cls, value: str, info: ValidationInfo) -> str:
        return check_url(str(info.field_name), value)


# Read-only prod profiles, one per region (`default-<region>`). Other
# environments are user config profiles.
# TODO: replace Auth0 PROD client ID.
DEFAULT_PROFILES: dict[str, ProfileConfig] = {
    "default-fr": ProfileConfig(
        issuer=f"https://{AUTH0_DOMAIN}/",
        client_id=PUBLIC_CLIENT_ID,
        audience=AUDIENCE,
        core_url=CORE_API_URL,
        account_url=ACCOUNT_API_URL,
    ),
    "default-sa": ProfileConfig(
        issuer=f"{SA_KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}",
        client_id=KEYCLOAK_SDK_CLIENT_ID,
        audience=AUDIENCE,
        core_url=KSA_CORE_API_URL,
        account_url=KSA_ACCOUNT_API_URL,
    ),
}

CONFIG_DIR = Path.home() / ".pasqal"

DEFAULT_PROFILE_NAME = "default-fr"
PROFILE_KEYS = tuple(ProfileConfig.model_fields)


class Config(BaseModel):
    # Unknown keys are kept, see `ProfileConfig`.
    model_config = ConfigDict(extra="allow")

    active_profile: str | None = None
    profiles: dict[str, ProfileConfig] = {}

    @field_validator("profiles")
    @classmethod
    def _no_builtin_names(
        cls, profiles: dict[str, ProfileConfig]
    ) -> dict[str, ProfileConfig]:
        clashes = sorted(DEFAULT_PROFILES.keys() & profiles.keys())
        if clashes:
            raise ValueError(f"built-in profiles can't be redefined: {clashes}")
        return profiles


@dataclass(frozen=True)
class PasqalCloudProfile:
    name: str
    config: ProfileConfig


def config_path() -> Path:
    return CONFIG_DIR / "config.json"


def load_config() -> Config:
    try:
        text = config_path().read_text()
    except FileNotFoundError:
        return Config()
    except OSError as e:
        raise ValueError(f"Can't read config {config_path()}: {e}") from e

    try:
        return Config.model_validate_json(text)
    except ValidationError as e:
        problems = [
            f"  {'.'.join(map(str, err['loc'])) or 'file'}: {err['msg']}"
            for err in e.errors(include_url=False)
        ]
        raise ValueError(
            f"Invalid config {config_path()}:\n"
            + "\n".join(problems)
            + "\nFix these entries in the file and retry."
        ) from e


def save_config(config: Config) -> None:
    write_private_file(
        config_path(), config.model_dump_json(indent=2, exclude_none=True) + "\n"
    )


def write_private_file(path: Path, text: str) -> None:
    """Atomically replace `path`, readable by the current user only."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    # mkstemp creates the file with 0600 under a unique name, so concurrent
    # writes never go into the same temp file.
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


# ---- Profiles ----


def profile_names(config: Config) -> list[str]:
    return sorted({*DEFAULT_PROFILES, *config.profiles})


def resolve_profile_name(config: Config, profile: str | None = None) -> str:
    """Resolve the profile from the explicit argument, then the config active
    profile, then `default-fr`.
    """
    return profile or config.active_profile or DEFAULT_PROFILE_NAME


def get_profile_config(config: Config, name: str) -> ProfileConfig:
    profile_config = config.profiles.get(name) or DEFAULT_PROFILES.get(name)
    if profile_config is None:
        raise ValueError(
            f"Unknown profile {name!r}, expected one of: "
            f"{', '.join(profile_names(config))}"
        )

    return profile_config


def check_new_profile_name(config: Config, name: str) -> None:
    if not name.strip():
        raise ValueError("Profile name can't be empty")
    if name in profile_names(config):
        raise ValueError(f"Profile {name!r} already exists")


def check_editable_profile(config: Config, name: str) -> ProfileConfig:
    """Return the profile, if it exists and isn't built-in."""
    profile_config = get_profile_config(config, name)
    if name in DEFAULT_PROFILES:
        raise ValueError(
            f"The built-in {name!r} profile holds the prod presets and can't be "
            "changed. For other values, create a profile: "
            "pasqal-cloud profile create <name>"
        )

    return profile_config


def activate_profile(config: Config, name: str) -> None:
    get_profile_config(config, name)
    config.active_profile = name


def delete_profile(config: Config, name: str) -> None:
    check_editable_profile(config, name)
    del config.profiles[name]
    if config.active_profile == name:
        config.active_profile = None


def resolve_profile(
    profile: str | None = None,
    config: Config | None = None,
    region: Region | None = None,
) -> PasqalCloudProfile:
    """Resolve the profile to its config: `region` selects the built-in
    `default-<region>` one, even over the active profile. Without it, see
    `resolve_profile_name`.

    Raises ValueError on an unknown profile or region, on both a profile and a
    region, or on an invalid or unreadable config."""
    if region is not None and region not in REGIONS:
        raise ValueError(f"Unknown region {region!r}, expected one of: {REGIONS}")
    if region is not None and profile is not None:
        raise ValueError("Pass either a profile or a region, not both")

    config = load_config() if config is None else config
    name = f"default-{region}" if region else resolve_profile_name(config, profile)

    return PasqalCloudProfile(name, get_profile_config(config, name))
