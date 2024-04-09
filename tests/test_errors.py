import json

import pytest
from requests import HTTPError, Response

from pasqal_cloud.errors import ExceptionWithResponseContext


def test_exception_for_response_with_description():
    """
    When we catch an exception with a populated Response object,
    the error message should extract data from the object
    and format the message. Then we assert it's as expected
    with an f-string pattern.
    """
    response = Response()
    response.status_code = 400
    description = "Unprocessable entity."
    data = {
        "code": response.status_code,
        "data": {"description": description, "some": "data"},
    }
    response._content = json.dumps(data).encode("utf-8")
    error = HTTPError(response=response)
    with pytest.raises(
        ExceptionWithResponseContext,
        match=(
            f"some message: {response.status_code}: {description}\nDetails: "
            + f"{json.dumps(data, indent=2)}"
        ),
    ):
        raise ExceptionWithResponseContext("some message", error)


def test_exception_for_response_without_description():
    """
    When we catch an exception with a populated Response object,
    the error message should extract data from the object
    and format the message. Then we assert it's as expected
    with an f-string pattern.
    """
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
    """
    When we catch an exception with a unpopulated Response object,
    the error message should extract the data it contains
    and format the message. Then we assert it's as expected.
    """
    response = Response()
    response.status_code = 400
    error = HTTPError(response=response)
    with pytest.raises(ExceptionWithResponseContext, match="some message"):
        raise ExceptionWithResponseContext("some message", error)


def test_exception_without_response():
    with pytest.raises(ExceptionWithResponseContext, match="some message"):
        raise ExceptionWithResponseContext("some message")
