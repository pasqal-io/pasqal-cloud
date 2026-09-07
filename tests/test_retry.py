from unittest.mock import patch

import pytest
import requests
import requests_mock

from pasqal_cloud.utils.retry import retry_http_error


@pytest.fixture
def make_request():
    @retry_http_error(max_retries=3, retry_status_code={429})
    def _make_request():
        response = requests.get("http://test-domain")
        response.raise_for_status()
        return response

    return _make_request


class TestRetryAfterOn429:
    """
    On a 429 response, the retry decorator should sleep for the duration
    given by the Retry-After header instead of the default exponential
    backoff, when that header is present and valid.
    """

    def test_uses_retry_after_seconds_value(self, make_request):
        with requests_mock.Mocker() as mock_request, patch("time.sleep") as mock_sleep:
            mock_request.get(
                "http://test-domain",
                [
                    {"status_code": 429, "headers": {"Retry-After": "12"}},
                    {"status_code": 200},
                ],
            )
            make_request()

        mock_sleep.assert_called_once_with(12)

    def test_uses_retry_after_http_date_value(self, make_request):
        with requests_mock.Mocker() as mock_request, patch("time.sleep") as mock_sleep:
            mock_request.get(
                "http://test-domain",
                [
                    {
                        "status_code": 429,
                        "headers": {"Retry-After": "Wed, 21 Oct 2099 07:28:00 GMT"},
                    },
                    {"status_code": 200},
                ],
            )
            make_request()

        assert mock_sleep.call_count == 1
        (delay,) = mock_sleep.call_args[0]
        assert delay > 0

    def test_falls_back_to_exponential_backoff_without_header(self, make_request):
        with requests_mock.Mocker() as mock_request, patch("time.sleep") as mock_sleep:
            mock_request.get(
                "http://test-domain",
                [
                    {"status_code": 429},
                    {"status_code": 200},
                ],
            )
            make_request()

        mock_sleep.assert_called_once_with(1)

    def test_falls_back_to_exponential_backoff_on_invalid_header(self, make_request):
        with requests_mock.Mocker() as mock_request, patch("time.sleep") as mock_sleep:
            mock_request.get(
                "http://test-domain",
                [
                    {"status_code": 429, "headers": {"Retry-After": "not-a-value"}},
                    {"status_code": 200},
                ],
            )
            make_request()

        mock_sleep.assert_called_once_with(1)

    def test_other_status_codes_ignore_retry_after(self):
        @retry_http_error(max_retries=3, retry_status_code={500})
        def _make_request():
            response = requests.get("http://test-domain")
            response.raise_for_status()
            return response

        with requests_mock.Mocker() as mock_request, patch("time.sleep") as mock_sleep:
            mock_request.get(
                "http://test-domain",
                [
                    {"status_code": 500, "headers": {"Retry-After": "99"}},
                    {"status_code": 200},
                ],
            )
            _make_request()

        mock_sleep.assert_called_once_with(1)
