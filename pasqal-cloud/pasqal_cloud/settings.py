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

The config holds named profiles, so devs can switch between environments.
A missing file is the `default` profile on the prod presets of
`pasqal_cloud.endpoints`. Layout:

    {
        "active_profile": "preprod",
        "profiles": {
            "default": {"default_region": "sa"},
            "preprod": {
                "regions": {
                    "fr": {
                        "issuer": "...",
                        "client_id": "...",
                        "audience": "...",
                        "core_url": "...",
                        "account_url": "..."
                    }
                }
            }
        }
    }

The `default` profile always exists, even when absent from the file. It always
uses the prod presets and may only set `default_region`. Other profiles target
other environments, so each region they use must set every key: mixing in prod
values would silently send their logins to prod.
"""

from __future__ import annotations

import dataclasses
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from pasqal_cloud.endpoints import DeploymentConf, DEPLOYMENTS, Region, REGIONS

CONFIG_PATH = Path.home() / ".pasqal" / "config.json"

DEFAULT_PROFILE = "default"
DEFAULT_REGION: Region = "fr"
GLOBAL_KEYS = ("default_region",)
REGION_KEYS = tuple(f.name for f in dataclasses.fields(DeploymentConf))
URL_KEYS = ("issuer", "core_url", "account_url")
LOOPBACK_HOSTS = ("localhost", "127.0.0.1")
DEFAULT_PROFILE_READONLY_MSG = (
    f"The {DEFAULT_PROFILE!r} profile uses the prod presets and only holds "
    "default_region. For other values, create a profile: "
    "pasqal-cloud config profile create <name>"
)


@dataclass(frozen=True)
class PasqalCloudTarget:
    profile: str
    region: Region
    deployment: DeploymentConf


def _check_region(region: object) -> Region:
    if region not in REGIONS:
        raise ValueError(
            f"Invalid region {region!r} in {CONFIG_PATH}, "
            f"expected one of: {', '.join(REGIONS)}"
        )

    return cast(Region, region)


def _check_value(key: str, value: object) -> str:
    """Reject non-strings, and URLs that would send tokens over plain HTTP
    (loopback hosts excepted, for local dev stacks)."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"Invalid {key} {value!r}: expected a non-empty string")

    if key in URL_KEYS:
        url = urlparse(value)
        secure = url.scheme == "https" or (
            url.scheme == "http" and url.hostname in LOOPBACK_HOSTS
        )
        if not (secure and url.hostname):
            raise ValueError(
                f"Invalid {key} {value!r}: expected an https:// URL "
                f"(http:// only on {', '.join(LOOPBACK_HOSTS)})"
            )

    return value


def load_config() -> dict[str, Any]:
    """Load the config. Its shape isn't checked: the CLI writes it, and values
    are checked on use by `resolve_pasqal_cloud_target`."""
    try:
        config: dict[str, Any] = json.loads(CONFIG_PATH.read_text())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {CONFIG_PATH}: {e}") from e

    return config


def save_config(config: dict[str, Any]) -> None:
    write_private_file(CONFIG_PATH, json.dumps(config, indent=2) + "\n")


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


def profile_names(config: dict[str, Any]) -> list[str]:
    return sorted({DEFAULT_PROFILE, *config.get("profiles", {})})


def resolve_profile_name(config: dict[str, Any], profile: str | None = None) -> str:
    """Resolve the profile from the explicit argument, then $PASQAL_CLOUD_PROFILE,
    then the config active profile, then `default`.
    """
    return (
        profile
        or os.environ.get("PASQAL_CLOUD_PROFILE")
        or config.get("active_profile")
        or DEFAULT_PROFILE
    )


def get_profile(config: dict[str, Any], name: str) -> dict[str, Any]:
    """Return the profile, stored in `config` so callers can edit it in place."""
    if name not in profile_names(config):
        raise ValueError(
            f"Unknown profile {name!r}, expected one of: "
            f"{', '.join(profile_names(config))}"
        )
    profile: dict[str, Any] = config.setdefault("profiles", {}).setdefault(name, {})
    return profile


def create_profile(config: dict[str, Any], name: str) -> None:
    if not name.strip():
        raise ValueError("Profile name can't be empty")
    if name in profile_names(config):
        raise ValueError(f"Profile {name!r} already exists")
    config.setdefault("profiles", {})[name] = {}


def activate_profile(config: dict[str, Any], name: str) -> None:
    get_profile(config, name)
    config["active_profile"] = name


def delete_profile(config: dict[str, Any], name: str) -> None:
    if name == DEFAULT_PROFILE:
        raise ValueError(f"The {DEFAULT_PROFILE!r} profile can't be deleted")

    get_profile(config, name)
    del config["profiles"][name]
    if config.get("active_profile") == name:
        del config["active_profile"]


# ---- Profile values ----


def set_value(
    profile: dict[str, Any], key: str, value: str, region: Region | None
) -> None:
    if key in GLOBAL_KEYS:
        profile[key] = _check_region(value)
    else:
        overrides = profile.setdefault("regions", {}).setdefault(region, {})
        overrides[key] = _check_value(key, value)


def unset_value(profile: dict[str, Any], key: str, region: Region | None) -> None:
    if key in GLOBAL_KEYS:
        profile.pop(key, None)
        return

    overrides = profile.get("regions", {}).get(region, {})
    overrides.pop(key, None)
    if not overrides:
        profile.get("regions", {}).pop(region, None)


def resolve_region(profile: dict[str, Any], region: Region | None) -> Region:
    """Resolve the region from the explicit argument, then the profile default
    region, then `fr`."""
    return region or _check_region(profile.get("default_region", DEFAULT_REGION))


def resolve_pasqal_cloud_target(
    region: Region | None = None,
    profile: str | None = None,
    config: dict[str, Any] | None = None,
) -> PasqalCloudTarget:
    """Resolve the profile (see `resolve_profile_name`), then the region (see
    `resolve_region`).

    The `default` profile uses the region's prod preset, other profiles their
    own values. Raises ValueError on an unknown profile, invalid config values,
    or a region that a non-default profile doesn't fully set.
    """
    config = load_config() if config is None else config

    name = resolve_profile_name(config, profile)
    profile_values = get_profile(config, name)
    region = resolve_region(profile_values, region)

    if name == DEFAULT_PROFILE:
        return PasqalCloudTarget(name, region, DEPLOYMENTS[region])

    region_values = profile_values.get("regions", {}).get(region, {})
    missing = [key for key in REGION_KEYS if key not in region_values]
    if missing:
        fix = (
            f"pasqal-cloud config set <key> <value> "
            f"--profile {name} --region {region}"
        )
        if not region_values:
            raise ValueError(
                f"Profile {name!r} has no config for region {region!r}, "
                f"set {', '.join(REGION_KEYS)} with: {fix}"
            )
        raise ValueError(
            f"Profile {name!r} is missing {', '.join(missing)} for region "
            f"{region!r}, set them with: {fix}"
        )

    # Checked here too, not only by `config set`: tokens must never go over
    # plain HTTP, even from a hand-edited config.
    checked = {key: _check_value(key, region_values[key]) for key in REGION_KEYS}
    return PasqalCloudTarget(name, region, DeploymentConf(**checked))
