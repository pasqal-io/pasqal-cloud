import json
from typing import Any, Generator
from unittest.mock import patch
from uuid import uuid4

import pytest

from pasqal_cloud import SDK
from pasqal_cloud.errors import DeviceSpecsFetchingError
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess


class TestDeviceSpecs:
    @pytest.fixture(autouse=True)
    @patch("pasqal_cloud.client.Auth0TokenProvider", FakeAuth0AuthenticationSuccess)
    def _init_sdk(self):
        self.sdk = SDK(
            username="me@test.com", password="password", project_id=str(uuid4())
        )

    @pytest.fixture(autouse=True)
    def _mock_sleep(self):
        """
        This fixture overrides sleeps, so tests don't need to wait for
        the total elapsed time.
        """
        with patch("time.sleep"):
            yield

    @pytest.mark.usefixtures("mock_request")
    def test_get_device_specs_success(self):
        device_specs_dict = self.sdk.get_device_specs_dict()
        assert isinstance(device_specs_dict, dict)
        specs = device_specs_dict["FRESNEL"]
        json.loads(specs)

    def test_get_device_specs_error(
        self, mock_request_exception: Generator[Any, Any, None]
    ):
        with pytest.raises(DeviceSpecsFetchingError):
            _ = self.sdk.get_device_specs_dict()
        assert mock_request_exception.last_request.method == "GET"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/devices/specs"
        )
