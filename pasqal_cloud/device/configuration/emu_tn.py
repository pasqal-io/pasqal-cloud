from __future__ import annotations

from dataclasses import dataclass

from pasqal_cloud.device.configuration.base_config import BaseConfig, InvalidConfiguration

DT_VALUE_NOT_VALID = "dt must be larger than 0. Not {}."
PRECISION_NOT_VALID = "Precision {} not valid. Must be one of 'low', 'normal', 'high'"
MAX_BOND_DIM_NOT_VALID = "Max bond dimension {} must be larger than 0. Not {}."


@dataclass
class EmuTNConfig(BaseConfig):
    """Configuration for the EmuTN device type.

    Args:
        dt (float): The time step in nanoseconds of the simulation. Defaults to 10.0.
        precision (str): The precision of the simulation. Defaults to "normal".
        max_bond_dim (int): The maximum bond dimension of the Matrix Product State (MPS). Defaults to 500.
    """

    dt: float = 10.0
    precision: str = "normal"
    max_bond_dim: int = 500

    def _validate(self) -> None:
        if self.dt <= 0:
            raise InvalidConfiguration(DT_VALUE_NOT_VALID.format(self.dt))
        if self.precision not in ["low", "normal", "high"]:
            raise InvalidConfiguration(PRECISION_NOT_VALID.format(self.precision))
        if self.max_bond_dim <= 0:
            raise InvalidConfiguration(MAX_BOND_DIM_NOT_VALID.format(self.max_bond_dim))
        super()._validate()
