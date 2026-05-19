# Copyright 2020 Pasqal Cloud Services development team
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
from typing import Any

from pasqal_cloud.pasqal_cloud_connection import PasqalCloudConnection
from pasqal_cloud.ovh import OVHConnection
from pasqal_cloud.backends import EmuMPSBackend, EmuSVBackend, EmuFreeBackend

# Public API — only these two are the intended top-level exports.
__all__ = [
    "PasqalCloudConnection",
    "OVHConnection",
    "EmuMPSBackend",
    "EmuSVBackend",
    "EmuFreeBackend",
]


def __getattr__(name: str) -> Any:
    """Lazily re-export deprecated names via ``_deprecations``.

    Any symbol that used to live in ``pasqal_cloud.*`` and was re-exported here
    is still accessible (``from pasqal_cloud import Batch``, etc.) but will
    emit a ``DeprecationWarning`` telling users where to import it from.

    These re-exports **will be removed in a future release**.
    """
    from pasqal_cloud._deprecations import __getattr__ as _dep_getattr

    return _dep_getattr(name)
