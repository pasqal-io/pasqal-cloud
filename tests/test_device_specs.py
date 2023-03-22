import json
from uuid import uuid4

import pytest

from sdk import SDK


class TestDeviceSpecs:
    @pytest.fixture(autouse=True)
    def init_sdk(self, start_mock_request):
        self.sdk = SDK(
            username="me@test.com", password="password", group_id=str(uuid4())
        )

    def test_get_device_specs_success(self):
        device_specs_dict = self.sdk.get_device_specs_dict()
        assert type(device_specs_dict) == dict
        specs = device_specs_dict["FRESNEL"]
        json.loads(specs)
