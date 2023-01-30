from __future__ import annotations

from typing import Any

from sdk.utils.configuration.base_config import BaseConfig
from sdk.utils.device_types import DeviceType

from dataclasses import dataclass, fields


@dataclass
class EmuFreeConfig(BaseConfig):

    with_noise: bool = False
