from sdk.utils.configuration.base_config import BaseConfig

from dataclasses import dataclass


@dataclass
class EmuFreeConfig(BaseConfig):

    with_noise: bool = False
