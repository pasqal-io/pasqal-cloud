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

from pasqal_cloud.endpoints import check_url, DeploymentConf, URL_KEYS
from pasqal_cloud.settings import (
    activate_profile,
    check_editable_profile,
    check_new_profile_name,
    Config,
    CONFIG_PATH,
    delete_profile,
    load_config,
    PROFILE_KEYS,
    profile_names,
    resolve_pasqal_cloud_target,
    resolve_profile_name,
    save_config,
)


def login(args: argparse.Namespace, config: Config) -> int:
    target = resolve_pasqal_cloud_target(args.profile, config)
    flow = "device" if args.device else "pkce"
    sys.stderr.write(f"login ({flow}, {target.profile}): not implemented\n")
    return 1


def auth_status(args: argparse.Namespace, config: Config) -> int:
    target = resolve_pasqal_cloud_target(args.profile, config)
    sys.stderr.write(f"auth status ({target.profile}): not implemented\n")
    return 1


def logout(args: argparse.Namespace, config: Config) -> int:
    target = resolve_pasqal_cloud_target(args.profile, config)
    sys.stderr.write(f"logout ({target.profile}): not implemented\n")
    return 1


def config_show(args: argparse.Namespace, config: Config) -> int:
    target = resolve_pasqal_cloud_target(args.profile, config)
    lines = [f"# {CONFIG_PATH}", f"profile = {target.profile}"]
    lines += [f"{key} = {getattr(target.deployment, key)}" for key in PROFILE_KEYS]

    sys.stdout.write("\n".join(lines) + "\n")
    return 0


def profile_list(_args: argparse.Namespace, config: Config) -> int:
    active = resolve_profile_name(config)
    for name in profile_names(config):
        sys.stdout.write(f"{'*' if name == active else ' '} {name}\n")
    return 0


def _prompt_value(key: str, current: str | None) -> str:
    """Ask for `key` until the answer is valid, Enter keeping `current`."""
    label = f"{key} [{current}]: " if current else f"{key}: "
    while True:
        value = input(label).strip() or current
        if not value:
            sys.stderr.write(f"{key} is required\n")
            continue

        try:
            return check_url(key, value) if key in URL_KEYS else value
        except ValueError as e:
            sys.stderr.write(f"{e}\n")


def _prompt_deployment(current: DeploymentConf | None) -> DeploymentConf:
    # No prod defaults on creation: pressing Enter through the prompts would
    # silently send the profile's logins to prod.
    values = {
        key: _prompt_value(key, getattr(current, key) if current else None)
        for key in PROFILE_KEYS
    }
    extra = current.model_extra if current else None
    return DeploymentConf(**(extra or {}), **values)


def profile_create(args: argparse.Namespace, config: Config) -> int:
    check_new_profile_name(config, args.name)
    config.profiles[args.name] = _prompt_deployment(None)
    save_config(config)

    sys.stderr.write(
        f"Created profile {args.name!r}. "
        f"Activate it with: pasqal-cloud config profile activate {args.name}\n"
    )
    return 0


def profile_edit(args: argparse.Namespace, config: Config) -> int:
    current = check_editable_profile(config, args.name)
    config.profiles[args.name] = _prompt_deployment(current)
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


def _add_profile_option(parser: argparse.ArgumentParser) -> None:
    # Defaults to None so $PASQAL_CLOUD_PROFILE and the config apply.
    parser.add_argument(
        "--profile",
        help="Config profile (default: $PASQAL_CLOUD_PROFILE, active profile, "
        "or default-fr)",
    )


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

    for sub in auth_commands.choices.values():
        _add_profile_option(sub)

    config = commands.add_parser(
        "config", help=f"Show or change the config ({CONFIG_PATH})"
    )
    # `--profile` lives on `show` only: on `config` itself, the subcommand's
    # own `--profile` default would silently override it.
    config.set_defaults(func=config_show, profile=None)
    config_commands = config.add_subparsers(dest="config_command")

    show_parser = config_commands.add_parser(
        "show", help="Show a profile's values (default: active profile)"
    )
    _add_profile_option(show_parser)
    show_parser.set_defaults(func=config_show)

    profile = config_commands.add_parser("profile", help="Manage config profiles")
    profile_commands = profile.add_subparsers(dest="profile_command", required=True)
    profile_commands.add_parser(
        "list", help="List profiles, * marks the active one"
    ).set_defaults(func=profile_list)

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
