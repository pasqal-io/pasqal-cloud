import json
import os

import pytest
import requests_mock

from pasqal_cloud.endpoints import Endpoints

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
        if data:
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
