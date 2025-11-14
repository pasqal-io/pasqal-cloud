import contextlib
import dataclasses
import json
from unittest.mock import patch
from uuid import uuid4

import pytest
import requests_mock
from pulser import AnalogDevice, DigitalAnalogDevice, Register, Sequence
from pulser.backend import BitStrings, EmulationConfig
from pulser.backend.remote import JobParams
from pulser_pasqal.backends import EmuMPSBackend
from pulser_pasqal.pasqal_cloud import PasqalCloud

from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess

test_device = dataclasses.replace(
    DigitalAnalogDevice,
    dmm_objects=(
        dataclasses.replace(
            DigitalAnalogDevice.dmm_objects[0], total_bottom_detuning=-1000
        ),
    ),
)


@pytest.mark.parametrize(
    "config", [None, EmulationConfig(observables=[BitStrings(tag_suffix="custom")])]
)
@pytest.mark.parametrize("job_params", [None, [JobParams(runs=10)]])
@patch(
    "pasqal_cloud.client.Auth0TokenProvider",
    FakeAuth0AuthenticationSuccess,
)
def test_emu_mps_backend(mock_request: requests_mock.mocker.Mocker, job_params, config):
    mock_request.reset_mock()
    connection = PasqalCloud(username="test", password="test", project_id=str(uuid4()))

    device = AnalogDevice
    register = Register.from_coordinates([(0, 0)], prefix="q")
    sequence = Sequence(register, device)
    # Just to avoid warning when measure() is called
    sequence.declare_channel("rydberg_global", "rydberg_global")
    sequence.measure()

    backend = EmuMPSBackend(sequence=sequence, connection=connection, config=config)

    context_manager = (
        pytest.warns(UserWarning, match="'runs' parameter is ignored")
        if job_params
        else contextlib.nullcontext()
    )
    with context_manager:
        _ = backend.run(job_params=job_params)
    assert (
        mock_request.request_history[0].url
        == "https://apis.pasqal.cloud/core-fast/api/v1/batches"
    )
    assert mock_request.request_history[0].method == "POST"
    post_batch_body = json.loads(mock_request.request_history[0].body)
    assert post_batch_body["device_type"] == "EMU_MPS"
    assert post_batch_body["sequence_builder"] == sequence.to_abstract_repr()
    assert "emulator" not in post_batch_body
    assert post_batch_body["jobs"] == job_params or {"runs": 1}

    default_config_params = json.loads(
        (EmuMPSBackend.default_config).to_abstract_repr()
    )
    custom_config_params = json.loads(config.to_abstract_repr()) if config else {}
    assert (
        json.loads(post_batch_body["backend_configuration"])
        == default_config_params | custom_config_params
    )
