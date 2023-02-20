from __future__ import annotations

import pytest

from sdk.device.configuration.base_config import (
    BaseConfig,
    InvalidConfiguration,
    INVALID_KEY_ERROR_MSG,
)
from sdk.device.configuration import EmuFreeConfig
from sdk.device.configuration.emu_tn import (
    EmuTNConfig,
    DT_VALUE_NOT_VALID,
    PRECISION_NOT_VALID,
)


@pytest.mark.parametrize(
    "config, expected",
    [
        (
            EmuTNConfig(
                dt=0.5,
                extra_config={"extra": "parameter", "extra_dict": {"key": "value"}},
            ),
            {
                "dt": 0.5,
                "precision": "normal",
                "max_bond_dim": 500,
                "extra": "parameter",
                "extra_dict": {"key": "value"},
            },
        ),
        (EmuTNConfig(), {"dt": 0.1, "precision": "normal", "max_bond_dim": 500}),
        (EmuFreeConfig(), {"with_noise": False}),
        (EmuFreeConfig(with_noise=True), {"with_noise": True}),
        (BaseConfig(), {}),
        (BaseConfig(extra_config={"extra": "parameter"}), {"extra": "parameter"}),
    ],
)
def test_configuration_to_dict(config: BaseConfig, expected: dict):
    assert config.to_dict() == expected


@pytest.mark.parametrize(
    "config_class, expected, config",
    [
        (
            EmuTNConfig,
            EmuTNConfig(
                dt=0.5,
                extra_config={"extra": "parameter", "extra_dict": {"key": "value"}},
            ),
            {
                "dt": 0.5,
                "precision": "normal",
                "extra": "parameter",
                "extra_dict": {"key": "value"},
            },
        ),
        (EmuTNConfig, EmuTNConfig(), {"dt": 0.1, "precision": "normal"}),
        (EmuFreeConfig, EmuFreeConfig(), {"with_noise": False}),
        (EmuFreeConfig, EmuFreeConfig(with_noise=True), {"with_noise": True}),
        (BaseConfig, BaseConfig(), {}),
        (
            BaseConfig,
            BaseConfig(extra_config={"extra": "parameter"}),
            {"extra": "parameter"},
        ),
    ],
)
def test_configuration_from_dict(
    config_class: type, expected: BaseConfig, config: dict
):
    assert config_class.from_dict(config) == expected


@pytest.mark.parametrize(
    "config, extra_config, expected",
    [
        (EmuTNConfig(), {"dt": 0.1}, INVALID_KEY_ERROR_MSG.format("dt")),
        (EmuTNConfig(dt=-1), None, DT_VALUE_NOT_VALID.format(-1)),
        (
            EmuTNConfig(precision="nonsense"),
            None,
            PRECISION_NOT_VALID.format("nonsense"),
        ),
    ],
)
def test_wrong_configuration(config, extra_config, expected):
    config.extra_config = extra_config
    with pytest.raises(InvalidConfiguration, match=expected):
        config.to_dict()
