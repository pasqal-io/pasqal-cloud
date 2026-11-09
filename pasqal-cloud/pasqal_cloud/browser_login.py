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
"""Browser login: Authorization Code + PKCE (RFC 7636) with a loopback redirect
(RFC 8252)."""

from __future__ import annotations

import contextlib
import secrets
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

from pasqal_cloud import oidc
from pasqal_cloud.config import ProfileConfig
from pasqal_cloud.oidc import LoginError

# Registered as callback URLs on both providers, on 127.0.0.1 and localhost.
CALLBACK_PORTS = range(8404, 8409)
CALLBACK_TIMEOUT = 300  # seconds

_DONE_PAGE = (
    b"<html><body><p>Pasqal Cloud login complete, you can close this tab.</p>"
    b"</body></html>"
)
_ERROR_PAGE = (
    b"<html><body><p>Pasqal Cloud login failed, see your terminal for details."
    b"</p></body></html>"
)


class _CallbackServer(HTTPServer):
    # POSIX needs SO_REUSEADDR to rebind a port left in TIME_WAIT by the
    # previous login. On Windows it would bind a port another process listens
    # on, so a busy port would not be skipped.
    allow_reuse_address = sys.platform != "win32"

    state: str
    params: dict[str, str] | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    server: _CallbackServer
    timeout = 10  # a silent connection must not block the login timeout

    def do_GET(self) -> None:
        url = urlsplit(self.path)
        params = {k: v[0] for k, v in parse_qs(url.query).items()}
        # Ignore stray requests (favicon, wrong state from another tab or page)
        # rather than abort the login.
        if url.path != "/callback" or params.get("state") != self.server.state:
            self.send_error(400)
            return
        self.server.params = params
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(_ERROR_PAGE if "error" in params else _DONE_PAGE)

    def log_message(self, *_args: Any) -> None:
        pass


def _listen() -> _CallbackServer:
    for port in CALLBACK_PORTS:
        with contextlib.suppress(OSError):  # port in use: try the next one
            return _CallbackServer(("127.0.0.1", port), _CallbackHandler)
    raise LoginError(
        f"No free port in {CALLBACK_PORTS.start}-{CALLBACK_PORTS.stop - 1} "
        "for the login callback, use: pasqal-cloud auth login --device"
    )


def _wait_for_callback(server: _CallbackServer) -> dict[str, str]:
    deadline = time.monotonic() + CALLBACK_TIMEOUT
    while server.params is None:
        server.timeout = deadline - time.monotonic()
        if server.timeout <= 0:
            raise LoginError("Timed out waiting for the browser login")
        server.handle_request()
    return server.params


def login(profile_config: ProfileConfig, config: dict[str, Any]) -> dict[str, Any]:
    """Run the browser login and return the token endpoint response."""
    verifier, challenge = oidc.pkce_pair()
    with _listen() as server:
        server.state = secrets.token_urlsafe(32)
        redirect_uri = f"http://127.0.0.1:{server.server_port}/callback"
        url = (
            config["authorization_endpoint"]
            + "?"
            + urlencode(
                {
                    "response_type": "code",
                    "client_id": profile_config.client_id,
                    "redirect_uri": redirect_uri,
                    "scope": " ".join(oidc.SCOPES),
                    "audience": profile_config.audience,
                    "state": server.state,
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                }
            )
        )
        if not webbrowser.open(url):
            raise LoginError(
                "Could not open a browser, use: pasqal-cloud auth login --device"
            )
        sys.stderr.write(
            f"If the browser did not open, visit:\n{url}\n\nWaiting for login...\n"
        )
        params = _wait_for_callback(server)
    if "error" in params:
        raise LoginError(
            f"Login failed: {params['error']} {params.get('error_description', '')}"
        )
    if "code" not in params:
        raise LoginError("Login failed: no authorization code in the callback")
    return oidc.token_request(
        config,
        {
            "grant_type": "authorization_code",
            "client_id": profile_config.client_id,
            "code": params["code"],
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        },
    )
