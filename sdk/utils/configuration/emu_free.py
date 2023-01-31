from sdk.utils.configuration.base_config import BaseConfig

from dataclasses import dataclass


@dataclass
class EmuFreeConfig(BaseConfig):
    """Configuration for the EmuFree device type.

    Args:
        with_noise (bool): Whether to add noise to the measurements. Defaults to False.
    """

    with_noise: bool = False
