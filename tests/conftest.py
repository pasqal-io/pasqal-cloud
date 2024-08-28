import json
import os
from typing import Any, Dict, Generator, Optional
from unittest.mock import patch

import pytest
import requests_mock
from requests import HTTPError, Request

from pasqal_cloud import Batch, Client, Job, Workload
from pasqal_cloud.endpoints import Endpoints
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess

TEST_API_FIXTURES_PATH = "tests/fixtures/api"
RESULT_LINK_ENDPOINT = "http://result-link/"
JOB_RESULT_LINK_ENDPOINT = "http://jobs-result-link/"
JSON_FILE = "_.{}.json"


@pytest.fixture()
def result_link_endpoint() -> str:
    return RESULT_LINK_ENDPOINT


def mock_core_response(request):
    version = request.url.split("api/")[1].split("/")[0]
    path = request.url.split(f"{version}/")[1].split("?")[0]
    data = None
    if request.method == "POST" and request.body:
        data = request.json()

    json_path = os.path.join(
        TEST_API_FIXTURES_PATH, version, path, JSON_FILE.format(request.method)
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


def mock_s3_presigned_url_response(request: Request) -> Dict[str, Any]:
    """
    Mock the response of a presigned URL and return expected results

    Args:
        request (Request): The incoming HTTP request

    Returns:
        Dict[str, Any]: The parsed JSON content from the results file
    """
    resource_id = request.url.split("/")[-1]
    results_path = os.path.join(
        TEST_API_FIXTURES_PATH, "v1", f"jobs/{resource_id}/results_link/result.json"
    )
    with open(results_path) as json_file:
        return json.load(json_file)


def mock_result_link_response() -> Dict[str, str]:
    """This mocks the response from the s3 result link."""
    return {"some": "result"}


def mock_response(request, _) -> Dict[str, Any]:
    """This acts as a Router to Mock the requests we make with custom behaviors.

    A linter might suggest 'context' is unused, but is required for some
    tests to execute.
    """
    if request.url.startswith(Endpoints.core):
        return mock_core_response(request)
    if request.url.startswith(JOB_RESULT_LINK_ENDPOINT):
        return mock_s3_presigned_url_response(request)
    if request.url.startswith(RESULT_LINK_ENDPOINT):
        return mock_result_link_response()
    return None


@pytest.fixture(scope="session")
@requests_mock.Mocker(kw="mock")
def request_mock(mock=None) -> Optional[Any]:
    # Configure requests to use the local JSON files a response
    mock.register_uri(
        requests_mock.ANY,
        requests_mock.ANY,
        status_code=200,
        json=mock_response,
    )
    return mock


@pytest.fixture(scope="session")
@requests_mock.Mocker(kw="mock")
def request_mock_exception(mock=None) -> Optional[Any]:
    mock.register_uri(
        requests_mock.ANY,
        requests_mock.ANY,
        exc=HTTPError,
    )
    return mock


@pytest.fixture(scope="session")
def batch_creation_error_data() -> Dict[str, Any]:
    return {
        "status": "fail",
        "message": "Unprocessable Entity",
        "code": "422",
        "data": {
            "description": [
                {
                    "loc": ["body", "jobs"],
                    "msg": "The batch sequence is not parametrized and"
                    + "expects no variables.",
                    "type": "value_error",
                }
            ]
        },
    }


@pytest.fixture()
def mock_request(request_mock) -> Generator[Any, Any, None]:
    request_mock.start()
    yield request_mock
    request_mock.stop()


@pytest.fixture()
def mock_request_exception(request_mock_exception) -> Generator[Any, Any, None]:
    request_mock_exception.start()
    yield request_mock_exception
    request_mock_exception.stop()


@pytest.fixture()
@patch("pasqal_cloud.client.Auth0TokenProvider", FakeAuth0AuthenticationSuccess)
def pasqal_client_mock():
    return Client(
        project_id="00000000-0000-0000-0000-000000000002",
        username="00000000-0000-0000-0000-000000000001",
        password="password",
    )


@pytest.fixture()
def workload(pasqal_client_mock):
    workload_data = {
        "id": "00000000-0000-0000-0000-000000000001",
        "project_id": "00000000-0000-0000-0000-000000000001",
        "status": "PENDING",
        "_client": pasqal_client_mock,
        "created_at": "2022-12-31T23:59:59.999Z",
        "updated_at": "2023-01-01T00:00:00.000Z",
        "errors": [],
        "backend": "backend_test",
        "workload_type": "workload_type_test",
        "config": {"test1": "test1", "test2": 2},
    }
    return Workload(**workload_data)


@pytest.fixture()
def batch_data_fixture() -> Dict[str, Any]:
    return {
        "complete": False,
        "open": True,
        "created_at": "2022-12-31T23:59:59.999Z",
        "updated_at": "2023-01-01T00:00:00.000Z",
        "device_type": "qpu",
        "project_id": "00000000-0000-0000-0000-000000000002",
        "id": "00000000-0000-0000-0000-000000000001",
        "user_id": "EQZj1ZQE",
        "status": "PENDING",
        "webhook": "https://example.com/webhook",
        "sequence_builder": "pulser",
        "start_datetime": "2023-01-01T00:00:00.000Z",
        "end_datetime": None,
        "device_status": "available",
    }


@pytest.fixture()
def batch(batch_data_fixture: Dict[str, Any], pasqal_client_mock) -> Batch:
    return Batch(**batch_data_fixture, _client=pasqal_client_mock)


@pytest.fixture()
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
