import json
import logging
from unittest.mock import patch
from uuid import uuid4

import pytest
import requests_mock
from pulser import AnalogDevice, Register, Sequence
from pulser.backend import BitStrings, CorrelationMatrix
from pulser.backend.config import EmulationConfig
from pulser.backend.remote import JobParams
from pasqal_cloud.backends import EmuFreeBackend
from pasqal_cloud.pasqal_cloud_connection import PasqalCloudConnection

from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess

# Batch ID that has a matching fixture file under
# tests/fixtures/core-fast/api/v2/batches/
MOCK_BATCH_ID = "00000000-0000-0000-0000-000000000001"


def _make_backend(connection, config=None):
    """Helper to build an EmuFreeBackend with a minimal sequence."""
    device = AnalogDevice
    register = Register.from_coordinates([(0, 0)], prefix="q")
    sequence = Sequence(register, device)
    sequence.declare_channel("rydberg_global", "rydberg_global")
    sequence.measure()
    return EmuFreeBackend(
        sequence=sequence, connection=connection, config=config
    ), sequence


@patch(
    "pasqal_cloud.http_client.PasswordGrantTokenProvider",
    FakeAuth0AuthenticationSuccess,
)
@pytest.mark.parametrize(
    ("job_params", "expected_default_num_shots"),
    [
        pytest.param(None, None, id="no_job_params"),
        pytest.param([JobParams(runs=10)], 10, id="runs_10"),
    ],
)
def test_emu_free_backend(
    mock_request: requests_mock.mocker.Mocker,
    caplog,
    job_params,
    expected_default_num_shots,
):
    mock_request.reset_mock()
    connection = PasqalCloudConnection(
        username="test", password="test", project_id=str(uuid4())
    )

    backend, sequence = _make_backend(connection)
    # Outside an open_batch with runs should NOT warn (it sets
    # default_num_shots instead), and without runs should not warn either.
    with caplog.at_level(logging.INFO, logger="pasqal_cloud.backends"):
        _ = backend.run(job_params=job_params)
    assert (
        mock_request.request_history[0].url
        == "https://apis.pasqal.cloud/core-fast/api/v1/batches"
    )
    assert mock_request.request_history[0].method == "POST"
    post_batch_body = mock_request.request_history[0].json()
    assert post_batch_body["device_type"] == "EMU_FREE"
    assert post_batch_body["sequence_builder"] == sequence.to_abstract_repr()
    assert "emulator" not in post_batch_body
    assert post_batch_body["jobs"] == job_params or {"runs": 1}

    # When runs is provided, default_num_shots is set on the config;
    # otherwise the default config is sent unchanged.
    if expected_default_num_shots is not None:
        expected_config = EmuFreeBackend.default_config.with_changes(
            default_num_shots=expected_default_num_shots,
        )
        assert any(
            "Setting 'default_num_shots'" in r.message
            and str(expected_default_num_shots) in r.message
            for r in caplog.records
        ), f"Expected INFO log with default_num_shots={expected_default_num_shots}"
    else:
        expected_config = EmuFreeBackend.default_config
    assert (
        post_batch_body["backend_configuration"] == expected_config.to_abstract_repr()
    )


@patch(
    "pasqal_cloud.http_client.PasswordGrantTokenProvider",
    FakeAuth0AuthenticationSuccess,
)
def test_emu_free_backend_with_custom_config(mock_request: requests_mock.mocker.Mocker):
    mock_request.reset_mock()
    connection = PasqalCloudConnection(
        username="test", password="test", project_id=str(uuid4())
    )

    config = EmulationConfig(observables=[BitStrings(), CorrelationMatrix()])
    backend, sequence = _make_backend(connection, config=config)
    _ = backend.run()
    assert (
        mock_request.request_history[0].url
        == "https://apis.pasqal.cloud/core-fast/api/v1/batches"
    )
    assert mock_request.request_history[0].method == "POST"
    post_batch_body = mock_request.request_history[0].json()
    assert post_batch_body["device_type"] == "EMU_FREE"
    assert post_batch_body["sequence_builder"] == sequence.to_abstract_repr()
    assert post_batch_body["backend_configuration"] == config.to_abstract_repr()
    assert "emulator" not in post_batch_body


@patch(
    "pasqal_cloud.http_client.PasswordGrantTokenProvider",
    FakeAuth0AuthenticationSuccess,
)
def test_no_open_batch_one_job_sets_default_num_shots(
    mock_request: requests_mock.mocker.Mocker,
    caplog,
):
    """Outside an open_batch, a single job with runs should set
    default_num_shots without any warning."""
    mock_request.reset_mock()
    connection = PasqalCloudConnection(
        username="test", password="test", project_id=str(uuid4())
    )
    backend, _ = _make_backend(connection)

    with caplog.at_level(logging.INFO, logger="pasqal_cloud.backends"):
        _ = backend.run(job_params=[JobParams(runs=200)])

    post_batch_body = mock_request.request_history[0].json()
    config_sent = json.loads(post_batch_body["backend_configuration"])
    assert config_sent.get("default_num_shots") == 200

    assert any(
        "Setting 'default_num_shots'" in record.message and "200" in record.message
        for record in caplog.records
    ), "Expected INFO log with default_num_shots=200"


@patch(
    "pasqal_cloud.http_client.PasswordGrantTokenProvider",
    FakeAuth0AuthenticationSuccess,
)
@pytest.mark.parametrize(
    ("job_params", "expected_default_num_shots"),
    [
        pytest.param(
            [JobParams(runs=50, variables={})] * 3,
            50,
            id="multiple_jobs_same_runs",
        ),
        pytest.param(
            [
                JobParams(runs=10, variables={}),
                JobParams(runs=100, variables={}),
                JobParams(runs=50, variables={}),
            ],
            100,
            id="multiple_jobs_different_runs_takes_highest",
        ),
    ],
)
def test_no_open_batch_multiple_jobs_warns_and_sets_default_num_shots(
    mock_request: requests_mock.mocker.Mocker,
    caplog,
    job_params,
    expected_default_num_shots,
):
    """Outside an open_batch, multiple jobs with runs should warn that
    this is not supported for now, and set default_num_shots to the
    highest value."""
    mock_request.reset_mock()
    connection = PasqalCloudConnection(
        username="test", password="test", project_id=str(uuid4())
    )
    backend, _ = _make_backend(connection)

    with (
        caplog.at_level(logging.INFO, logger="pasqal_cloud.backends"),
        pytest.warns(
            UserWarning,
            match="Passing multiple jobs with 'runs' is not supported",
        ),
    ):
        _ = backend.run(job_params=job_params)

    post_batch_body = mock_request.request_history[0].json()
    config_sent = json.loads(post_batch_body["backend_configuration"])
    assert config_sent.get("default_num_shots") == expected_default_num_shots

    assert any(
        "Setting 'default_num_shots'" in record.message
        and str(expected_default_num_shots) in record.message
        for record in caplog.records
    ), f"Expected INFO log with default_num_shots={expected_default_num_shots}"


@patch(
    "pasqal_cloud.http_client.PasswordGrantTokenProvider",
    FakeAuth0AuthenticationSuccess,
)
def test_no_open_batch_custom_num_shots_warns_runs_ignored(
    mock_request: requests_mock.mocker.Mocker,
):
    """Outside an open_batch, if BitStrings already has a custom num_shots,
    passing runs should emit a warning that runs has no effect."""
    mock_request.reset_mock()
    connection = PasqalCloudConnection(
        username="test", password="test", project_id=str(uuid4())
    )
    config = EmulationConfig(observables=[BitStrings(num_shots=500)])
    backend, _ = _make_backend(connection, config=config)

    with pytest.warns(UserWarning, match="'runs' parameter has no effect"):
        _ = backend.run(job_params=[JobParams(runs=100)])


@patch(
    "pasqal_cloud.http_client.PasswordGrantTokenProvider",
    FakeAuth0AuthenticationSuccess,
)
@pytest.mark.parametrize(
    "job_params",
    [
        pytest.param(
            [JobParams(runs=50, variables={})] * 3,
            id="multiple_jobs_with_runs",
        ),
        pytest.param(
            [JobParams(runs=200)],
            id="one_job_with_runs",
        ),
    ],
)
def test_open_batch_with_runs_warns(
    mock_request: requests_mock.mocker.Mocker,
    job_params,
):
    """Inside an open_batch, any job with runs should warn."""
    mock_request.reset_mock()
    connection = PasqalCloudConnection(
        username="test", password="test", project_id=str(uuid4())
    )
    backend, _ = _make_backend(connection)
    backend._batch_id = MOCK_BATCH_ID

    with pytest.warns(UserWarning, match="'runs' parameter is ignored"):
        _ = backend.run(job_params=job_params)


@patch(
    "pasqal_cloud.http_client.PasswordGrantTokenProvider",
    FakeAuth0AuthenticationSuccess,
)
def test_open_batch_no_runs_no_warning(
    mock_request: requests_mock.mocker.Mocker,
    recwarn,
):
    """Inside an open_batch, if no runs are specified, no warning."""
    mock_request.reset_mock()
    connection = PasqalCloudConnection(
        username="test", password="test", project_id=str(uuid4())
    )
    backend, _ = _make_backend(connection)
    backend._batch_id = MOCK_BATCH_ID

    _ = backend.run(job_params=[JobParams(variables={})])

    # Assert no UserWarning was emitted
    user_warnings = [w for w in recwarn.list if issubclass(w.category, UserWarning)]
    assert (
        len(user_warnings) == 0
    ), f"Expected no UserWarning but got: {[str(w.message) for w in user_warnings]}"
