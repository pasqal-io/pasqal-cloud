# Copyright 2025 Pasqal Cloud Services development team
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
import os
import warnings
from enum import Enum
from pathlib import Path

# Holds the config profiles and the login token cache.
CONFIG_DIR = Path(
    os.getenv("PASQAL_CLOUD_CONFIG_DIR") or Path.home() / ".pasqal"
).expanduser()

# Seconds, per HTTP request.
HTTP_TIMEOUT = float(os.getenv("PASQAL_CLOUD_HTTP_TIMEOUT") or 30)


def skip_ssl_verify() -> bool:
    """Disable SSL verification, for users behind a TLS-intercepting proxy whose
    certificate they can't trust. Never set it otherwise."""
    value = os.getenv("PASQAL_CLOUD_SKIP_SSL_VERIFY")
    if value is None and "PASQAL_SKIP_SSL_VERIFY" in os.environ:
        warnings.warn(
            "PASQAL_SKIP_SSL_VERIFY is deprecated and will be removed in the next "
            "major version: use PASQAL_CLOUD_SKIP_SSL_VERIFY.",
            FutureWarning,
            stacklevel=2,
        )
        value = os.environ["PASQAL_SKIP_SSL_VERIFY"]

    return bool(value)


def skip_gzip_request_body() -> bool:
    """Send request bodies uncompressed."""
    value = os.getenv("PASQAL_CLOUD_SKIP_GZIP_REQUEST_BODY")
    if value is None and "PASQAL_SKIP_GZIP_REQUEST_BODY" in os.environ:
        warnings.warn(
            "PASQAL_SKIP_GZIP_REQUEST_BODY is deprecated and will be removed in the "
            "next major version: use PASQAL_CLOUD_SKIP_GZIP_REQUEST_BODY.",
            FutureWarning,
            stacklevel=2,
        )
        value = os.environ["PASQAL_SKIP_GZIP_REQUEST_BODY"]

    return bool(value)


class BatchStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"
    CANCELED = "CANCELED"
    TIMED_OUT = "TIMED_OUT"


class JobStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"
    CANCELED = "CANCELED"


class QueuePriority(Enum):
    """
    Values represent the queue a value will be written to, each priority
    represents the order of preference batches will be executed.

    HIGH being the quickest
    MEDIUM being a lower tier
    LOW being the lowest tier
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
