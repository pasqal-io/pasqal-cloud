"""`pasqal-cloud` command line interface: auth login, auth status, auth logout."""

from __future__ import annotations

import argparse
import sys

from pasqal_cloud.endpoints import LoginTarget, REGIONS, resolve_login_target


def login(args: argparse.Namespace, target: LoginTarget) -> int:
    flow = "device" if args.device else "pkce"
    sys.stderr.write(f"login ({flow}, {target.region}/{target.env}): not implemented\n")
    return 1


def auth_status(_args: argparse.Namespace, target: LoginTarget) -> int:
    sys.stderr.write(f"auth status ({target.region}/{target.env}): not implemented\n")
    return 1


def logout(_args: argparse.Namespace, target: LoginTarget) -> int:
    sys.stderr.write(f"logout ({target.region}/{target.env}): not implemented\n")
    return 1


def build_parser() -> argparse.ArgumentParser:
    # --region defaults to None so commands can tell flag / env var / default apart.
    region = argparse.ArgumentParser(add_help=False)
    region.add_argument(
        "--region",
        choices=REGIONS,
        help="Platform region (default: $PASQAL_CLOUD_REGION or fr)",
    )

    parser = argparse.ArgumentParser(prog="pasqal-cloud")
    commands = parser.add_subparsers(dest="command", required=True)

    auth = commands.add_parser("auth", help="Log in, inspect or log out")
    auth_commands = auth.add_subparsers(dest="auth_command", required=True)

    login_parser = auth_commands.add_parser(
        "login", parents=[region], help="Log in to Pasqal Cloud"
    )
    login_parser.add_argument(
        "--device",
        action="store_true",
        help="Use the device flow (no local browser needed)",
    )
    login_parser.set_defaults(func=login)

    auth_commands.add_parser(
        "status", parents=[region], help="Show cached logins"
    ).set_defaults(func=auth_status)

    auth_commands.add_parser(
        "logout", parents=[region], help="Log out and delete the cached login"
    ).set_defaults(func=logout)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        target = resolve_login_target(args.region)
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1
    return int(args.func(args, target))


if __name__ == "__main__":
    sys.exit(main())
