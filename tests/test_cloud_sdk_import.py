import inspect

import pytest

"""
Tests written to verify if the backward compatibility is working between the new name of the package `pasqal-cloud` 
and its main folder renamed to `pasqal_cloud` and the previous package name that was `pasqal-cloud` 
with the former folder called `sdk`.
"""


def test_verify_import_sdk_is_module():
    with pytest.warns(DeprecationWarning):
        import sdk
        assert inspect.ismodule(sdk)


def test_verify_import_classes_from_sdk():
    with pytest.warns(DeprecationWarning):
        from sdk import SDK
        from sdk import Batch
        from sdk import Job
        from sdk import Endpoints
        from sdk import EmulatorType
        from sdk.device.configuration import BaseConfig
        from sdk.device.configuration import EmuFreeConfig
        from sdk.device.configuration import EmuTNConfig
        from sdk.utils import JSendPayload
        from sdk.utils import StrEnum
