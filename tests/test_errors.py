import json

import pytest
from requests import HTTPError, Response

from pasqal_cloud.errors import ExceptionWithResponseContext


def test_exception_for_response_with_description():
    response = Response()
    response.status_code = 400
    description = "Unprocessable entity."
    code = 400
    data = {"code": code, "data": {"description": description, "some": "data"}}
    response._content = json.dumps(data).encode("utf-8")
    error = HTTPError(response=response)
    with pytest.raises(
        ExceptionWithResponseContext,
        match=(
            f"some message: {code}: {description}\nDetails: "
            + f"{json.dumps(data, indent=2)}"
        ),
    ):
        raise ExceptionWithResponseContext("some message", error)


def test_exception_for_response_without_description():
    response = Response()
    response.status_code = 400
    data = {"message": "message"}
    response._content = json.dumps(data).encode("utf-8")
    error = HTTPError(response=response)
    with pytest.raises(
        ExceptionWithResponseContext,
        match=(f"some message: 0: message\nDetails: {json.dumps(data, indent=2)}"),
    ):
        raise ExceptionWithResponseContext("some message", error)


def test_exception_with_response_without_data():
    response = Response()
    response.status_code = 400
    error = HTTPError(response=response)
    with pytest.raises(ExceptionWithResponseContext, match="some message"):
        raise ExceptionWithResponseContext("some message", error)


def test_exception_without_response():
    with pytest.raises(ExceptionWithResponseContext, match="some message"):
        raise ExceptionWithResponseContext("some message")
