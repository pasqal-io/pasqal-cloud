import json
import os
import pytest
import requests_mock


TEST_API_FIXTURES_PATH = "tests/fixtures/api"
JSON_FILE = "_.{}.json"


@pytest.fixture(scope="session")
@requests_mock.Mocker(kw="mock")
def request_mock(mock=None):
    def mock_response(request, context):
        path = request.url.split("/api/v1/")[1].split("?")[0]
        json_path = os.path.join(
            TEST_API_FIXTURES_PATH, path, JSON_FILE.format(request.method)
        )
        with open(json_path) as json_file:
            return json.load(json_file)

    # Configure requests to use the local JSON files a response
    mock.register_uri(requests_mock.ANY, requests_mock.ANY, json=mock_response)
    return mock


@pytest.fixture(scope="class")
def start_mock_request(request_mock):
    request_mock.start()
    yield request_mock
    request_mock.stop()