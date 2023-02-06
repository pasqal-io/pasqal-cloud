from sdk.device.configuration.base_config import BaseConfig

from dataclasses import dataclass


@dataclass
class EmuFreeConfig(BaseConfig):
    """Configuration for the EmuFree device type.

    Args:
        with_noise (bool): Whether to add noise to the simulation. Defaults to False.
    """

    with_noise: bool = False
