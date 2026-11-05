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
presets of `pasqal_cloud.endpoints`. Without an active profile, `default-fr`
is used.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator, ValidationError

from pasqal_cloud.endpoints import DEFAULT_PROFILES, ProfileConfig

CONFIG_PATH = Path.home() / ".pasqal" / "config.json"

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


def load_config() -> Config:
    try:
        text = CONFIG_PATH.read_text()
    except FileNotFoundError:
        return Config()

    try:
        return Config.model_validate_json(text)
    except ValidationError as e:
        problems = [
            f"  {'.'.join(map(str, err['loc'])) or 'file'}: {err['msg']}"
            for err in e.errors(include_url=False)
        ]
        raise ValueError(
            f"Invalid config {CONFIG_PATH}:\n"
            + "\n".join(problems)
            + "\nFix these entries in the file and retry."
        ) from e


def save_config(config: Config) -> None:
    write_private_file(
        CONFIG_PATH, config.model_dump_json(indent=2, exclude_none=True) + "\n"
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
    profile: str | None = None, config: Config | None = None
) -> PasqalCloudProfile:
    """Resolve the profile (see `resolve_profile_name`) to its config.
    Raises ValueError on an unknown profile or an invalid config."""
    config = load_config() if config is None else config
    name = resolve_profile_name(config, profile)
    return PasqalCloudProfile(name, get_profile_config(config, name))
