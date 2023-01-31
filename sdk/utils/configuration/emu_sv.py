from __future__ import annotations

from dataclasses import dataclass

from sdk.utils.configuration.base_config import BaseConfig, InvalidConfiguration

DT_VALUE_NOT_VALID = "dt must be larger than 0. Not {}."
PRECISION_NOT_VALID = "Precision {} not valid. Must be one of 'low', 'normal', 'high'"


@dataclass
class EmuSVConfig(BaseConfig):

    dt: float = 0.1
    precision: str = "normal"

    def _validate(self) -> None:
        if self.dt <= 0:
            raise InvalidConfiguration(DT_VALUE_NOT_VALID.format(self.dt))
        if self.precision not in ["low", "normal", "high"]:
            raise InvalidConfiguration(PRECISION_NOT_VALID.format(self.precision))
        super()._validate()
