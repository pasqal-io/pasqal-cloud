"""`pasqal-cloud` command line interface: auth login, auth status, auth logout."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

from pasqal_cloud import token_cache
from pasqal_cloud.endpoints import LoginTarget, REGIONS, resolve_login_target


def login(args: argparse.Namespace, target: LoginTarget) -> int:
    flow = "device" if args.device else "pkce"
    sys.stderr.write(f"login ({flow}, {target.region}/{target.env}): not implemented\n")
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


def auth_status(_args: argparse.Namespace, target: LoginTarget) -> int:
    """Offline: list cached logins, never printing token material."""
    active_key = token_cache.entry_key(target.region, target.env)
    region_from = {"flag": "--region", "env var": "PASQAL_CLOUD_REGION"}
    env_from = {"env var": "PASQAL_CLOUD_ENV"}
    sys.stdout.write(
        f"Cache file: {token_cache.cache_path()}\n"
        f"Region:     {target.region:<4} "
        f"(from {region_from.get(target.region_source, 'default')})\n"
        f"Env:        {target.env:<4} "
        f"(from {env_from.get(target.env_source, 'default')})\n"
    )
    try:
        entries = token_cache.read_entries()
    except token_cache.TokenCacheError as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1
    active = entries.get(active_key)
    active_found = active is not None and active.matches(target.preset)
    for key, entry in sorted(entries.items()):
        is_active = active_found and key == active_key
        user = entry.id_claims.get("email") or entry.id_claims.get("sub", "unknown")
        sys.stdout.write(
            f"\n{'*' if is_active else ' '} {key}"
            f"{' (active)' if is_active else ''}\n"
            f"    Region:         {entry.region}\n"
            f"    Env:            {entry.env}\n"
            f"    User:           {user}\n"
            f"    Client:         {entry.client_id}\n"
            f"    Access token:   {_format_expiry(entry.expires_at)}\n"
            f"    Refresh token:  {_format_expiry(entry.refresh_expires_at)}\n"
        )
    if not active_found:
        sys.stderr.write(f"Not logged in to {target.region}/{target.env}\n")
    return 0 if active_found else 1


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
