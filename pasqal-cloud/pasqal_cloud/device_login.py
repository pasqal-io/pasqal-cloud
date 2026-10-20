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
"""Device login: OAuth 2.0 Device Authorization Grant (RFC 8628)."""

from __future__ import annotations

import sys
import time
from typing import Any

from pasqal_cloud import oidc
from pasqal_cloud.config import ProfileConfig
from pasqal_cloud.oidc import LoginError

GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"
DEFAULT_INTERVAL = 5  # seconds, RFC 8628 3.2
SLOW_DOWN_STEP = 5  # seconds added to the interval on slow_down, RFC 8628 3.5


def login(profile_config: ProfileConfig, config: dict[str, Any]) -> dict[str, Any]:
    """Run the device login and return the token endpoint response.

    `config` must have a `device_authorization_endpoint`.
    """
    # Not in RFC 8628, but Keycloak enforces the client's "PKCE required"
    # setting on the device flow too.
    verifier, challenge = oidc.pkce_pair()

    response = oidc.post_form(
        config["device_authorization_endpoint"],
        {
            "client_id": profile_config.client_id,
            "scope": " ".join(oidc.SCOPES),
            "audience": profile_config.audience,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
        "Device authorization request",
    )

    try:
        device_code = str(response["device_code"])
        user_code = str(response["user_code"])
        verification_uri = str(response["verification_uri"])
        deadline = time.monotonic() + int(response["expires_in"])
        interval = int(response.get("interval", DEFAULT_INTERVAL))
    except (KeyError, TypeError, ValueError) as e:
        raise LoginError(f"Invalid device authorization response: {e!r}") from e

    sys.stderr.write(
        f"Open {verification_uri} on another device\n"
        f"and enter code: {user_code}\n\n"
        "Waiting for authorization...\n"
    )

    # A network error while polling aborts the login: add a retry if long
    # waits on flaky networks (HPC login nodes) turn out to need it.
    while True:
        time.sleep(interval)

        if time.monotonic() >= deadline:
            raise LoginError("The device code expired, run the login again")

        try:
            return oidc.token_request(
                config,
                {
                    "grant_type": GRANT_TYPE,
                    "client_id": profile_config.client_id,
                    "device_code": device_code,
                    "code_verifier": verifier,
                },
            )
        except oidc.OIDCError as e:
            if e.error == "slow_down":
                interval += SLOW_DOWN_STEP
            elif e.error != "authorization_pending":
                raise
