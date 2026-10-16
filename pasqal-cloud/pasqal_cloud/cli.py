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
"""`pasqal-cloud` command line interface: auth login/status/logout, profile."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

from pasqal_cloud import token_cache
from pasqal_cloud.config import (
    activate_profile,
    check_editable_profile,
    check_new_profile_name,
    check_url,
    Config,
    CONFIG_PATH,
    DEFAULT_PROFILE_NAME,
    DEFAULT_PROFILES,
    delete_profile,
    load_config,
    PROFILE_KEYS,
    profile_names,
    ProfileConfig,
    resolve_profile,
    resolve_profile_name,
    save_config,
    URL_KEYS,
)


def login(args: argparse.Namespace, config: Config) -> int:
    profile = resolve_profile(config=config)
    flow = "device" if args.device else "pkce"
    sys.stderr.write(f"login ({flow}, {profile.name}): not implemented\n")
    return 1


def _duration(seconds: float) -> str:
    for unit, size in (("day", 86400), ("h", 3600), ("min", 60)):
        if seconds >= size:
            count = int(seconds // size)
            return f"{count} {unit}{'s' if unit == 'day' and count > 1 else ''}"
    return "less than 1 min"


def _format_expiry(timestamp: int | None) -> str:
    if timestamp is None:
        return "expiry unknown"  # Auth0 does not return the refresh token lifetime
    text = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    delta = timestamp - time.time()
    if delta > 0:
        return f"expires {text} (in {_duration(delta)})"
    return f"expired {text} ({_duration(-delta)} ago)"


def auth_status(_args: argparse.Namespace, config: Config) -> int:
    """Offline: list the cached logins, never printing token material."""
    profile = resolve_profile(config=config)
    profile_from = "active profile" if config.active_profile else "default"
    sys.stdout.write(
        f"Cache file: {token_cache.cache_path()}\n"
        f"Profile:    {profile.name} (from {profile_from})\n"
        f"Issuer:     {profile.config.issuer}\n"
    )

    try:
        entries = token_cache.read_entries()
    except token_cache.TokenCacheError as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1

    active = entries.get(profile.name)
    active_found = active is not None and active.matches(profile.config)
    for key, entry in sorted(entries.items()):
        is_active = active_found and key == profile.name
        user = entry.id_claims.get("email") or entry.id_claims.get("sub", "unknown")
        sys.stdout.write(
            f"\n{'*' if is_active else ' '} {key}"
            f"{' (active)' if is_active else ''}\n"
            f"    Issuer:         {entry.issuer}\n"
            f"    User:           {user}\n"
            f"    Client:         {entry.client_id}\n"
            f"    Access token:   {_format_expiry(entry.expires_at)}\n"
            f"    Refresh token:  {_format_expiry(entry.refresh_expires_at)}\n"
        )

    if not active_found:
        sys.stderr.write(f"Not logged in to {profile.name}\n")
    return 0 if active_found else 1


def logout(_args: argparse.Namespace, config: Config) -> int:
    profile = resolve_profile(config=config)
    sys.stderr.write(f"logout ({profile.name}): not implemented\n")
    return 1


def profile_show(args: argparse.Namespace, config: Config) -> int:
    profile = resolve_profile(args.name, config)
    lines = [f"# {CONFIG_PATH}", f"profile = {profile.name}"]
    lines += [f"{key} = {getattr(profile.config, key)}" for key in PROFILE_KEYS]

    sys.stdout.write("\n".join(lines) + "\n")
    return 0


def profile_list(_args: argparse.Namespace, config: Config) -> int:
    active = resolve_profile_name(config)
    for name in profile_names(config):
        sys.stdout.write(f"{'*' if name == active else ' '} {name}\n")
    return 0


def _prompt_value(key: str, current: str | None, prod: str) -> str:
    """Ask for `key` until the answer is valid, Enter keeping `current`."""
    label = (
        f"{key} [{current}]: "
        if current
        else f"{key} ({DEFAULT_PROFILE_NAME}: {prod}): "
    )
    while True:
        value = input(label).strip() or current
        if not value:
            sys.stderr.write(f"{key} is required\n")
            continue

        try:
            return check_url(key, value) if key in URL_KEYS else value
        except ValueError as e:
            sys.stderr.write(f"{e}\n")


def _prompt_profile_config(current: ProfileConfig | None) -> ProfileConfig:
    # On creation, prod values are shown as examples but not used as defaults:
    # pressing Enter through the prompts would silently send the profile's
    # logins to prod.
    prod = DEFAULT_PROFILES[DEFAULT_PROFILE_NAME]
    values = {
        key: _prompt_value(
            key, getattr(current, key) if current else None, getattr(prod, key)
        )
        for key in PROFILE_KEYS
    }
    extra = current.model_extra if current else None
    return ProfileConfig(**(extra or {}), **values)


def profile_create(args: argparse.Namespace, config: Config) -> int:
    check_new_profile_name(config, args.name)
    config.profiles[args.name] = _prompt_profile_config(None)
    save_config(config)

    sys.stderr.write(
        f"Created profile {args.name!r}. "
        f"Activate it with: pasqal-cloud profile activate {args.name}\n"
    )
    return 0


def profile_edit(args: argparse.Namespace, config: Config) -> int:
    current = check_editable_profile(config, args.name)
    config.profiles[args.name] = _prompt_profile_config(current)
    save_config(config)
    return 0


def profile_activate(args: argparse.Namespace, config: Config) -> int:
    activate_profile(config, args.name)
    save_config(config)
    return 0


def profile_delete(args: argparse.Namespace, config: Config) -> int:
    delete_profile(config, args.name)
    save_config(config)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pasqal-cloud")
    commands = parser.add_subparsers(dest="command", required=True)

    auth = commands.add_parser("auth", help="Log in, inspect or log out")
    auth_commands = auth.add_subparsers(dest="auth_command", required=True)

    login_parser = auth_commands.add_parser("login", help="Log in to Pasqal Cloud")
    login_parser.add_argument(
        "--device",
        action="store_true",
        help="Use the device flow (no local browser needed)",
    )
    login_parser.set_defaults(func=login)

    auth_commands.add_parser("status", help="Show cached logins").set_defaults(
        func=auth_status
    )
    auth_commands.add_parser(
        "logout", help="Log out and delete the cached login"
    ).set_defaults(func=logout)

    profile = commands.add_parser(
        "profile", help=f"Manage config profiles ({CONFIG_PATH})"
    )
    profile_commands = profile.add_subparsers(dest="profile_command", required=True)
    profile_commands.add_parser(
        "list", help="List profiles, * marks the active one"
    ).set_defaults(func=profile_list)

    show_parser = profile_commands.add_parser(
        "show", help="Show a profile's values (default: active profile)"
    )
    show_parser.add_argument("name", nargs="?")
    show_parser.set_defaults(func=profile_show)

    for name, func, help_text in [
        ("create", profile_create, "Create a profile, prompting for its values"),
        ("edit", profile_edit, "Change a profile's values, prompting for each"),
        ("activate", profile_activate, "Make a profile the active one"),
        ("delete", profile_delete, "Delete a profile"),
    ]:
        sub = profile_commands.add_parser(name, help=help_text)
        sub.add_argument("name")
        sub.set_defaults(func=func)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args, load_config()))
    except (ValueError, OSError) as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1
    except (EOFError, KeyboardInterrupt):
        sys.stderr.write("\nAborted\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
