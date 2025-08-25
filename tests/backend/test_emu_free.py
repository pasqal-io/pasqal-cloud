import json
from unittest.mock import patch
from uuid import uuid4

import requests_mock
from pulser import AnalogDevice, Register, Sequence
from pulser.backend.remote import JobParams
from pulser_pasqal.backends import EmuFreeBackendV2
from pulser_pasqal.pasqal_cloud import PasqalCloud

from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess


@patch(
    "pasqal_cloud.client.Auth0TokenProvider",
    FakeAuth0AuthenticationSuccess,
)
def test_emu_free_backend(mock_request: requests_mock.mocker.Mocker):
    mock_request.reset_mock()
    connection = PasqalCloud(username="test", password="test", project_id=str(uuid4()))

    device = AnalogDevice
    register = Register.from_coordinates([(0, 0)], prefix="q")
    sequence = Sequence(register, device)
    sequence.measure()

    backend = EmuFreeBackendV2(sequence=sequence, connection=connection)
    _ = backend.run(job_params=[JobParams(runs=10)])
    assert (
        mock_request.request_history[0].url
        == "https://apis.pasqal.cloud/core-fast/api/v1/batches"
    )
    assert mock_request.request_history[0].method == "POST"
    post_batch_body = json.loads(mock_request.request_history[0].body)
    assert post_batch_body["device_type"] == "EMU_FREE"
    assert post_batch_body["sequence_builder"] == sequence.to_abstract_repr()
    assert (
        post_batch_body["backend_configuration"]
        == EmuFreeBackendV2.default_config.to_abstract_repr()
    )
    assert "emulator" not in post_batch_body
