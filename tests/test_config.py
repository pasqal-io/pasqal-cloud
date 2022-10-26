from typing import Dict
import pytest

from sdk.utils.configuration import (
    Configuration,
    InvalidConfiguration,
    INVALID_KEY_ERROR_MSG,
    DT_VALUE_NOT_VALID,
    PRECISION_NOT_VALID,
)


@pytest.mark.parametrize(
    "config, expected",
    [
        (
            Configuration(
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
        (Configuration(), {"dt": 0.1, "precision": "normal"}),
    ],
)
def test_configuration_to_dict(config: Configuration, expected: Dict):
    assert config.to_dict() == expected


@pytest.mark.parametrize(
    "expected, config",
    [
        (
            Configuration(
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
        (Configuration(), {"dt": 0.1, "precision": "normal"}),
    ],
)
def test_configuration_from_dict(expected: Configuration, config: Dict):
    assert Configuration.from_dict(config) == expected


@pytest.mark.parametrize(
    "config, extra_config, expected",
    [
        (Configuration(), {"dt": 0.1}, INVALID_KEY_ERROR_MSG.format("dt")),
        (Configuration(dt=-1), None, DT_VALUE_NOT_VALID.format(-1)),
        (
            Configuration(precision="nonsense"),
            None,
            PRECISION_NOT_VALID.format("nonsense"),
        ),
    ],
)
def test_wrong_configuration(config, extra_config, expected):
    config.extra_config = extra_config
    with pytest.raises(InvalidConfiguration, match=expected):
        config.to_dict()
