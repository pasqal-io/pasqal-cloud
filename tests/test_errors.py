import json

import pytest
from requests import HTTPError, Response

from pasqal_cloud.errors import ExceptionWithResponseContext


def test_exception_for_response_with_context():
    response = Response()
    response.status_code = 400
    response._content = json.dumps({"some": "data"}).encode("utf-8")
    error = HTTPError(response=response)
    with pytest.raises(
        ExceptionWithResponseContext, match="some message: {'some': 'data'}"
    ):
        raise ExceptionWithResponseContext("some message", error)


def test_exception_with_response_without_context():
    response = Response()
    response.status_code = 400
    error = HTTPError(response=response)
    with pytest.raises(
        ExceptionWithResponseContext, match="some message: without context."
    ):
        raise ExceptionWithResponseContext("some message", error)


def test_exception_without_response():
    with pytest.raises(ExceptionWithResponseContext, match="some message"):
        raise ExceptionWithResponseContext("some message")
