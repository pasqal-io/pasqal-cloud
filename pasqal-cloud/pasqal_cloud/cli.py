"""`pasqal-cloud` command line interface: auth login, auth status, auth logout."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from typing import Any

from pasqal_cloud import browser_login, device_login, oidc, token_cache
from pasqal_cloud.endpoints import (
    PasqalCloudTarget,
    REGIONS,
    resolve_pasqal_cloud_target,
)


def _save_login(
    target: PasqalCloudTarget, tokens: dict[str, Any]
) -> token_cache.CacheEntry:
    """Replace the cache entry for `target`."""
    if "refresh_token" not in tokens:
        raise oidc.LoginError("The provider returned no refresh token (offline_access)")
    try:
        entry = token_cache.CacheEntry.from_tokens(target, tokens)
    except (KeyError, TypeError, ValueError) as e:
        raise oidc.LoginError(f"Invalid token response: {e!r}") from e
    with token_cache.lock():
        entries = token_cache.read_entries()
        previous = entries.get(entry.key)
        token_cache.write_entries({**entries, entry.key: entry})
    if previous and previous.id_claims.get("sub") != entry.id_claims.get("sub"):
        sys.stderr.write(
            f"Note: replaced the login of {_user(previous)} with {_user(entry)}\n"
        )
    return entry


def _user(entry: token_cache.CacheEntry) -> str:
    return str(entry.id_claims.get("email") or entry.id_claims.get("sub", "unknown"))


def _revoke(
    entry: token_cache.CacheEntry, config: dict[str, Any] | None = None
) -> None:
    """Best effort revocation of the entry's refresh token, warn on failure.

    Discovers the entry's issuer when `config` is not given: a discovery
    failure only skips the revocation.
    """
    try:
        oidc.revoke(
            config or oidc.discover(entry.issuer), entry.client_id, entry.refresh_token
        )
    except oidc.OIDCError as e:
        sys.stderr.write(f"Warning: could not revoke the login of {entry.key}: {e}\n")


def _revoke_previous(target: PasqalCloudTarget, config: dict[str, Any]) -> None:
    """Best effort revocation of the cached refresh token, before a new login.

    Must run before the new tokens are issued: with SSO they can share the old
    token's session (Keycloak) or grant (Auth0), and revoking the old token
    afterwards could revoke them too.
    """
    previous = token_cache.read_entries().get(
        token_cache.entry_key(target.region, target.env)
    )
    if previous is None or not previous.matches(target.deployment):
        return  # issued by another client: cannot be revoked here
    _revoke(previous, config)


def login(args: argparse.Namespace, target: PasqalCloudTarget) -> int:
    flow = device_login if args.device else browser_login

    try:
        config = oidc.discover(target.deployment.issuer, device=args.device)
        _revoke_previous(target, config)
        entry = _save_login(target, flow.login(target.deployment, config))

    # A rejected cache file fails the login before the browser opens: it is
    # never overwritten, it may already have leaked.
    except (oidc.LoginError, oidc.OIDCError, token_cache.TokenCacheError, OSError) as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1

    sys.stderr.write(f"Logged in to {target.region}/{target.env} as {_user(entry)}\n")
    return 0


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


def auth_status(_args: argparse.Namespace, target: PasqalCloudTarget) -> int:
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
    active_found = active is not None and active.matches(target.deployment)
    for key, entry in sorted(entries.items()):
        is_active = active_found and key == active_key
        sys.stdout.write(
            f"\n{'*' if is_active else ' '} {key}"
            f"{' (active)' if is_active else ''}\n"
            f"    Region:         {entry.region}\n"
            f"    Env:            {entry.env}\n"
            f"    User:           {_user(entry)}\n"
            f"    Client:         {entry.client_id}\n"
            f"    Access token:   {_format_expiry(entry.expires_at)}\n"
            f"    Refresh token:  {_format_expiry(entry.refresh_expires_at)}\n"
        )
    if not active_found:
        sys.stderr.write(f"Not logged in to {target.region}/{target.env}\n")
    return 0 if active_found else 1


def _logout_command(entry: token_cache.CacheEntry) -> str:
    env = "" if entry.env == "prod" else f"PASQAL_CLOUD_ENV={entry.env} "
    return f"{env}pasqal-cloud auth logout --region {entry.region}"


def logout(_args: argparse.Namespace, target: PasqalCloudTarget) -> int:
    """Never interactive: an explicit region/env selects the entry, otherwise
    the only entry is logged out, and several entries are an error."""
    explicit = (target.region_source, target.env_source) != ("default", "default")
    active_key = token_cache.entry_key(target.region, target.env)

    try:
        with token_cache.lock():
            entries = token_cache.read_entries()

            if not explicit and len(entries) > 1:
                sys.stderr.write(
                    "Error: logged in to several environments, log out of one with:\n"
                    + "".join(
                        f"  {_logout_command(e)}\n" for _, e in sorted(entries.items())
                    )
                )
                return 1

            key = active_key if explicit else next(iter(entries), "")
            entry = entries.pop(key, None)
            if entry is None:
                sys.stderr.write(
                    f"Not logged in{f' to {active_key}' if explicit else ''}\n"
                )
                return 0

            # Even an entry for another client than the deployment is revoked,
            # with the issuer and client it was issued by.
            _revoke(entry)
            token_cache.write_entries(entries)

    except (token_cache.TokenCacheError, OSError) as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1

    sys.stderr.write(f"Logged out of {entry.key} ({_user(entry)})\n")
    return 0


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
        target = resolve_pasqal_cloud_target(args.region)
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1
    return int(args.func(args, target))


if __name__ == "__main__":
    sys.exit(main())
