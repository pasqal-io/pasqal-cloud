from __future__ import annotations

import re

import pytest

from pasqal_cloud.device import EmuFreeConfig
from pasqal_cloud.device.configuration.base_config import (
    BaseConfig,
    INVALID_KEY_ERROR_MSG,
    INVALID_RESULT_TYPES,
    InvalidConfiguration,
)
from pasqal_cloud.device.configuration.emu_tn import (
    DT_VALUE_NOT_VALID,
    EmuTNConfig,
    PRECISION_NOT_VALID,
)
from pasqal_cloud.device.configuration.result_type import ResultType


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        (
            EmuTNConfig(
                dt=10.0,
                extra_config={
                    "extra": "parameter",
                    "extra_dict": {"key": "value"},
                },
            ),
            {
                "strict_validation": False,
                "dt": 10.0,
                "precision": "normal",
                "max_bond_dim": 500,
                "extra": "parameter",
                "extra_dict": {"key": "value"},
                "result_types": None,
            },
        ),
        (
            EmuTNConfig(result_types=[ResultType.COUNTER]),
            {
                "strict_validation": False,
                "dt": 10.0,
                "precision": "normal",
                "max_bond_dim": 500,
                "result_types": [ResultType.COUNTER],
            },
        ),
        (
            EmuFreeConfig(),
            {
                "strict_validation": False,
                "with_noise": False,
                "result_types": None,
            },
        ),
        (
            EmuFreeConfig(with_noise=True),
            {
                "strict_validation": False,
                "with_noise": True,
                "result_types": None,
            },
        ),
        (
            BaseConfig(),
            {
                "strict_validation": False,
                "result_types": None,
            },
        ),
        (
            BaseConfig(strict_validation=True),
            {
                "strict_validation": True,
                "result_types": None,
            },
        ),
        (
            BaseConfig(extra_config={"extra": "parameter"}),
            {
                "strict_validation": False,
                "extra": "parameter",
                "result_types": None,
            },
        ),
    ],
)
def test_configuration_to_dict(config: BaseConfig, expected: dict):
    assert config.to_dict() == expected


@pytest.mark.parametrize(
    ("config_class", "expected", "config"),
    [
        (
            EmuTNConfig,
            EmuTNConfig(
                dt=0.5,
                extra_config={"extra": "parameter", "extra_dict": {"key": "value"}},
            ),
            {
                "strict_validation": False,
                "dt": 0.5,
                "precision": "normal",
                "extra": "parameter",
                "extra_dict": {"key": "value"},
            },
        ),
        (
            EmuTNConfig,
            EmuTNConfig(),
            {"strict_validation": False, "dt": 10.0, "precision": "normal"},
        ),
        (
            EmuTNConfig,
            EmuTNConfig(strict_validation=True),
            {"strict_validation": True, "dt": 10.0, "precision": "normal"},
        ),
        (
            EmuFreeConfig,
            EmuFreeConfig(),
            {"strict_validation": False, "with_noise": False},
        ),
        (
            EmuFreeConfig,
            EmuFreeConfig(with_noise=True),
            {"strict_validation": False, "with_noise": True},
        ),
        (
            EmuFreeConfig,
            EmuFreeConfig(strict_validation=True),
            {"strict_validation": True, "with_noise": False},
        ),
        (
            BaseConfig,
            BaseConfig(),
            {
                "strict_validation": False,
            },
        ),
        (
            BaseConfig,
            BaseConfig(extra_config={"extra": "parameter"}),
            {"strict_validation": False, "extra": "parameter"},
        ),
    ],
)
def test_configuration_from_dict(
    config_class: type, expected: BaseConfig, config: dict
):
    assert config_class.from_dict(config) == expected


@pytest.mark.parametrize(
    ("config", "extra_config", "expected"),
    [
        (EmuTNConfig(), {"dt": 10.0}, INVALID_KEY_ERROR_MSG.format("dt")),
        (EmuTNConfig(dt=-1), None, DT_VALUE_NOT_VALID.format(-1)),
        (
            EmuTNConfig(precision="nonsense"),
            None,
            PRECISION_NOT_VALID.format("nonsense"),
        ),
        (
            EmuTNConfig(result_types=[ResultType.EXPECTATION]),
            None,
            INVALID_RESULT_TYPES.format(
                [ResultType.EXPECTATION], EmuTNConfig().allowed_result_types
            ),
        ),
    ],
)
def test_wrong_configuration(config, extra_config, expected):
    config.extra_config = extra_config
    with pytest.raises(InvalidConfiguration, match=re.escape(expected)):
        config.to_dict()
