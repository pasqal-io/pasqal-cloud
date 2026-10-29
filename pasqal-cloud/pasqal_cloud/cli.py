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
"""`pasqal-cloud` command line interface: auth login/status/logout, config."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from pasqal_cloud.endpoints import Region, REGIONS
from pasqal_cloud.settings import (
    activate_profile,
    CONFIG_PATH,
    create_profile,
    DEFAULT_PROFILE,
    DEFAULT_PROFILE_READONLY_MSG,
    DEFAULT_REGION,
    delete_profile,
    get_profile,
    GLOBAL_KEYS,
    load_config,
    profile_names,
    REGION_KEYS,
    resolve_pasqal_cloud_target,
    resolve_profile_name,
    resolve_region,
    save_config,
    set_value,
    unset_value,
)


def login(args: argparse.Namespace, config: dict[str, Any]) -> int:
    target = resolve_pasqal_cloud_target(args.region, args.profile, config)
    flow = "device" if args.device else "pkce"
    sys.stderr.write(
        f"login ({flow}, {target.profile}/{target.region}): not implemented\n"
    )
    return 1


def auth_status(args: argparse.Namespace, config: dict[str, Any]) -> int:
    target = resolve_pasqal_cloud_target(args.region, args.profile, config)
    sys.stderr.write(
        f"auth status ({target.profile}/{target.region}): not implemented\n"
    )
    return 1


def logout(args: argparse.Namespace, config: dict[str, Any]) -> int:
    target = resolve_pasqal_cloud_target(args.region, args.profile, config)
    sys.stderr.write(f"logout ({target.profile}/{target.region}): not implemented\n")
    return 1


def config_show(args: argparse.Namespace, config: dict[str, Any]) -> int:
    name = resolve_profile_name(config, args.profile)
    lines = [
        f"# {CONFIG_PATH}",
        f"profile = {name}",
        f"default_region = {resolve_region(get_profile(config, name), None)}",
    ]

    for region in REGIONS:
        lines.append(f"\n[{region}]")
        try:
            deployment = resolve_pasqal_cloud_target(region, name, config).deployment
        except ValueError as e:
            lines.append(f"# {e}")
            continue
        lines += [f"{key} = {getattr(deployment, key)}" for key in REGION_KEYS]

    sys.stdout.write("\n".join(lines) + "\n")
    return 0


def _editable_region(args: argparse.Namespace, config: dict[str, Any]) -> Region | None:
    if args.key in GLOBAL_KEYS:
        return None

    name = resolve_profile_name(config, args.profile)
    if name == DEFAULT_PROFILE:
        raise ValueError(DEFAULT_PROFILE_READONLY_MSG)

    # Only the region, not the full target: `config set` is how an incomplete
    # region gets completed.
    return resolve_region(get_profile(config, name), args.region)


def config_set_or_unset(args: argparse.Namespace, config: dict[str, Any]) -> int:
    """Set the key, or unset it when `args.value` is None (`config unset`)."""
    profile = get_profile(config, resolve_profile_name(config, args.profile))
    region = _editable_region(args, config)

    if args.value is None:
        unset_value(profile, args.key, region)
    else:
        set_value(profile, args.key, args.value, region)

    save_config(config)
    return 0


def profile_list(_args: argparse.Namespace, config: dict[str, Any]) -> int:
    active = resolve_profile_name(config)
    for name in profile_names(config):
        sys.stdout.write(f"{'*' if name == active else ' '} {name}\n")
    return 0


def _prompt(label: str, default: str) -> str:
    return input(f"{label} [{default}]: ").strip() or default


def _require(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        sys.stderr.write(f"{label} is required\n")


def profile_create(args: argparse.Namespace, config: dict[str, Any]) -> int:
    create_profile(config, args.name)
    profile = get_profile(config, args.name)

    answer = _prompt("default_region", DEFAULT_REGION)
    if answer != DEFAULT_REGION:
        set_value(profile, "default_region", answer, None)
    default_region = resolve_region(profile, None)

    # No prod defaults: pressing Enter through the prompts would build a
    # profile that is mostly prod. A configured region stores every key, see
    # `pasqal_cloud.settings`. The default region comes first and can't be
    # skipped, so the profile always resolves.
    others = [region for region in REGIONS if region != default_region]
    sys.stderr.write(
        f"Leave the {', '.join(others)} issuer empty to skip that region.\n"
    )
    for region in [default_region, *others]:
        if region == default_region:
            issuer = _require(f"{region} issuer")
        else:
            issuer = input(f"{region} issuer: ").strip()
            if not issuer:
                continue

        set_value(profile, "issuer", issuer, region)
        for key in REGION_KEYS:
            if key != "issuer":
                set_value(profile, key, _require(f"{region} {key}"), region)

    resolve_pasqal_cloud_target(None, args.name, config)
    save_config(config)

    sys.stderr.write(
        f"Created profile {args.name!r}. "
        f"Activate it with: pasqal-cloud config profile activate {args.name}\n"
    )
    return 0


def profile_activate(args: argparse.Namespace, config: dict[str, Any]) -> int:
    activate_profile(config, args.name)
    save_config(config)
    return 0


def profile_delete(args: argparse.Namespace, config: dict[str, Any]) -> int:
    delete_profile(config, args.name)
    save_config(config)
    return 0


def build_parser() -> argparse.ArgumentParser:
    # Both default to None so $PASQAL_CLOUD_PROFILE and the config apply.
    target = argparse.ArgumentParser(add_help=False)
    target.add_argument(
        "--region",
        choices=REGIONS,
        help="Platform region (default: profile default_region, or fr)",
    )
    target.add_argument(
        "--profile",
        help="Config profile (default: $PASQAL_CLOUD_PROFILE, active profile, "
        "or default)",
    )

    parser = argparse.ArgumentParser(prog="pasqal-cloud")
    commands = parser.add_subparsers(dest="command", required=True)

    auth = commands.add_parser("auth", help="Log in, inspect or log out")
    auth_commands = auth.add_subparsers(dest="auth_command", required=True)

    login_parser = auth_commands.add_parser(
        "login", parents=[target], help="Log in to Pasqal Cloud"
    )
    login_parser.add_argument(
        "--device",
        action="store_true",
        help="Use the device flow (no local browser needed)",
    )
    login_parser.set_defaults(func=login)

    auth_commands.add_parser(
        "status", parents=[target], help="Show cached logins"
    ).set_defaults(func=auth_status)

    auth_commands.add_parser(
        "logout", parents=[target], help="Log out and delete the cached login"
    ).set_defaults(func=logout)

    config = commands.add_parser(
        "config", help=f"Show or change the config ({CONFIG_PATH})"
    )
    # `--profile` lives on the subcommands only: on `config` itself, a
    # subcommand's own `--profile` default would silently override it.
    config.set_defaults(func=config_show, profile=None)
    config_commands = config.add_subparsers(dest="config_command")

    show_parser = config_commands.add_parser(
        "show", help="Show a profile's values (default: active profile)"
    )
    show_parser.add_argument("--profile")
    show_parser.set_defaults(func=config_show)

    keys = GLOBAL_KEYS + REGION_KEYS
    set_parser = config_commands.add_parser(
        "set", parents=[target], help="Set a value (region keys apply to --region)"
    )
    set_parser.add_argument("key", choices=keys)
    set_parser.add_argument("value")
    set_parser.set_defaults(func=config_set_or_unset)

    unset_parser = config_commands.add_parser(
        "unset", parents=[target], help="Reset a value to its default"
    )
    unset_parser.add_argument("key", choices=keys)
    unset_parser.set_defaults(func=config_set_or_unset, value=None)

    profile = config_commands.add_parser("profile", help="Manage config profiles")
    profile_commands = profile.add_subparsers(dest="profile_command", required=True)
    profile_commands.add_parser(
        "list", help="List profiles, * marks the active one"
    ).set_defaults(func=profile_list)

    for name, func, help_text in [
        ("create", profile_create, "Create a profile, prompting for its values"),
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
