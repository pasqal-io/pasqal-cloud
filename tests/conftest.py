import json
import os
from unittest.mock import patch

import pytest
import requests_mock

from pasqal_cloud import Client, Batch, Job
from pasqal_cloud.endpoints import Endpoints
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess

TEST_API_FIXTURES_PATH = "tests/fixtures/api"
JSON_FILE = "_.{}.json"


def mock_core_response(request):
    path = request.url.split("/api/v1/")[1].split("?")[0]

    data = None
    if request.method == "POST":
        data = request.json()

    json_path = os.path.join(
        TEST_API_FIXTURES_PATH, path, JSON_FILE.format(request.method)
    )
    with open(json_path) as json_file:
        result = json.load(json_file)
        if path == "batches" and data:
            if data.get("emulator"):
                result["data"]["device_type"] = data["emulator"]
            else:
                result["data"]["device_type"] = "FRESNEL"
                result["data"]["configuration"] = None
        return result


def mock_response(request, context):
    """This acts as a Router to Mock the requests we make with custom behaviors."""
    if request.url.startswith(Endpoints.core):
        return mock_core_response(request)


@pytest.fixture(scope="session")
@requests_mock.Mocker(kw="mock")
def request_mock(mock=None):
    # Configure requests to use the local JSON files a response
    mock.register_uri(requests_mock.ANY, requests_mock.ANY, json=mock_response)
    return mock


@pytest.fixture(scope="function")
def start_mock_request(request_mock):
    request_mock.start()
    yield request_mock
    request_mock.stop()


@pytest.fixture
@patch("pasqal_cloud.client.Auth0TokenProvider", FakeAuth0AuthenticationSuccess)
def pasqal_client_mock():
    client = Client(
        project_id="00000000-0000-0000-0000-000000000002",
        username="00000000-0000-0000-0000-000000000001",
        password="password",
    )
    return client


@pytest.fixture
def batch(pasqal_client_mock):
    batch_data = {
        "complete": False,
        "created_at": "2022-12-31T23:59:59.999Z",
        "updated_at": "2023-01-01T00:00:00.000Z",
        "device_type": "qpu",
        "project_id": "00000000-0000-0000-0000-000000000002",
        "id": "00000000-0000-0000-0000-000000000001",
        "user_id": "EQZj1ZQE",
        "priority": 0,
        "status": "PENDING",
        "webhook": "https://example.com/webhook",
        "_client": pasqal_client_mock,
        "sequence_builder": "pulser",
        "start_datetime": "2023-01-01T00:00:00.000Z",
        "end_datetime": None,
        "device_status": "available",
        "jobs": {},
    }
    return Batch(**batch_data)


@pytest.fixture
def job(pasqal_client_mock):
    job_data = {
        "runs": 50,
        "batch_id": "00000000-0000-0000-0000-000000000001",
        "id": "00000000-0000-0000-0000-000000022010",
        "project_id": "00000000-0000-0000-0000-000000000001",
        "status": "PENDING",
        "_client": pasqal_client_mock,
        "created_at": "2022-12-31T23:59:59.999Z",
        "updated_at": "2023-01-01T00:00:00.000Z",
        "errors": [],
        "variables": {"param1": 1, "param2": 2, "param3": 3},
    }
    return Job(**job_data)
