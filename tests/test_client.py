import contextlib
from unittest.mock import patch
from uuid import uuid4

import pytest
import requests
import requests_mock
from auth0.v3.exceptions import Auth0Error

from pasqal_cloud import (
    AUTH0_CONFIG,
    Auth0Conf,
    Endpoints,
    PASQAL_ENDPOINTS,
    SDK,
)
from pasqal_cloud._version import __version__ as sdk_version
from pasqal_cloud.authentication import TokenProvider
from tests.test_doubles.authentication import (
    FakeAuth0AuthenticationFailure,
    FakeAuth0AuthenticationSuccess,
)


class TestSDKCommonAttributes:
    project_id = "random_project_id"
    username = "random_username"
    password = "random_password"
    new_core_endpoint = "random_endpoint"
    no_username = ""
    no_password = ""


@patch("pasqal_cloud.client.Auth0TokenProvider", FakeAuth0AuthenticationSuccess)
class TestAuthSuccess(TestSDKCommonAttributes):
    @patch("pasqal_cloud.client.getpass")
    def test_module_getpass_success(self, getpass):
        getpass.return_value = self.password
        SDK(project_id=self.project_id, username=self.username)
        getpass.assert_called_once()

    def test_authentication_success(self):
        SDK(project_id=self.project_id, username=self.username, password=self.password)

    def test_good_token_provider(self):
        SDK(
            project_id=self.project_id,
            token_provider=FakeAuth0AuthenticationSuccess("username", "password", None),
        )

    def test_custom_token_provider(self):
        """Test that the custom provider suggested in the readme is working"""

        class CustomTokenProvider(TokenProvider):
            def get_token(self):
                return "your-token"  # Replace this value with your token

        SDK(token_provider=CustomTokenProvider(), project_id="project_id")

    @pytest.mark.filterwarnings(
        "ignore:The parameters 'endpoints' and 'auth0' are deprecated, from now use"
        " 'env' instead"
    )
    def test_correct_endpoints(self):
        sdk = SDK(
            project_id=self.project_id,
            username=self.username,
            password=self.password,
            endpoints=Endpoints(core=self.new_core_endpoint),
        )
        assert sdk._client.endpoints.core == self.new_core_endpoint

    @pytest.mark.filterwarnings(
        "ignore:The parameters 'endpoints' and 'auth0' are deprecated, from now use"
        " 'env' instead"
    )
    def test_correct_new_auth0(self):
        new_auth0 = Auth0Conf(domain="new_domain")
        SDK(
            project_id=self.project_id,
            username=self.username,
            password=self.password,
            auth0=new_auth0,
        )


@patch("pasqal_cloud.client.Auth0TokenProvider", FakeAuth0AuthenticationFailure)
class TestAuthFailure(TestSDKCommonAttributes):
    @patch("pasqal_cloud.client.getpass")
    def test_module_getpass_bad_password(self, getpass):
        getpass.return_value = self.password

        with pytest.raises(Auth0Error):
            SDK(project_id=self.project_id, username=self.username)

        getpass.assert_called_once()

    def test_module_bad_password(self):
        with pytest.raises(Auth0Error):
            SDK(
                project_id=self.project_id,
                username=self.username,
                password=self.password,
            )


class TestAuthInvalidClient(TestSDKCommonAttributes):
    def test_module_no_project_id(self):
        with pytest.raises(
            ValueError,
            match="You need to provide a project_id",
        ):
            SDK(
                username=self.username,
                password=self.password,
            )

    def test_module_no_user_with_password(self):
        with pytest.raises(
            ValueError,
            match="At least a username or TokenProvider object should be provided",
        ):
            SDK(
                project_id=self.project_id,
                username=self.no_username,
                password=self.password,
            )

    @patch("pasqal_cloud.client.getpass")
    def test_module_no_password(self, getpass):
        getpass.return_value = ""
        with pytest.raises(
            ValueError, match="The prompted password should not be empty"
        ):
            SDK(
                project_id=self.project_id,
                username=self.username,
                password=self.no_password,
            )

    @patch("pasqal_cloud.client.getpass")
    def test_module_getpass_no_password(self, getpass):
        getpass.return_value = self.no_password

        with pytest.raises(
            ValueError, match="The prompted password should not be empty"
        ):
            SDK(project_id=self.project_id, username=self.username)

        getpass.assert_called_once()

    def test_bad_token_provider(self):
        with pytest.raises(TypeError):
            SDK(project_id=self.project_id, token_provider="token")

    def test_bad_auth0(self):
        with pytest.raises(TypeError):
            SDK(
                project_id=self.project_id,
                username=self.username,
                password=self.password,
                auth0="",
            )

    def test_authentication_no_credentials_provided(self):
        with pytest.raises(
            ValueError,
            match="At least a username or TokenProvider object should be provided",
        ):
            SDK(project_id=self.project_id)

    @pytest.mark.filterwarnings(
        "ignore:The parameters 'endpoints' and 'auth0' are deprecated, from now use"
        " 'env' instead"
    )
    def test_bad_endpoints(self):
        with pytest.raises(TypeError):
            SDK(
                project_id=self.project_id,
                username=self.username,
                password=self.password,
                endpoints={
                    "core": "",
                    "account": "",
                },
            )


@patch("pasqal_cloud.client.Auth0TokenProvider", FakeAuth0AuthenticationSuccess)
class TestEnvSDK(TestSDKCommonAttributes):
    @pytest.mark.parametrize(
        ("env", "core_endpoint_expected"),
        [
            ("prod", "https://apis.pasqal.cloud/core-fast"),
            ("preprod", "https://apis.preprod.pasqal.cloud/core-fast"),
            ("dev", "https://apis.dev.pasqal.cloud/core-fast"),
        ],
    )
    def test_select_env(self, env: str, core_endpoint_expected: str):
        sdk = SDK(
            project_id=self.project_id,
            username=self.username,
            password=self.password,
            auth0=AUTH0_CONFIG[env],
            endpoints=PASQAL_ENDPOINTS[env],
        )
        assert sdk._client.endpoints.core == core_endpoint_expected


class TestSDKRetry:
    """
    When we make HTTP calls, certain status codes will either force
    the SDK to retry a HTTP call, return a payload or raise an immediate
    exception.
    """

    @pytest.fixture(autouse=True)
    @patch(
        "pasqal_cloud.client.Auth0TokenProvider",
        FakeAuth0AuthenticationSuccess,
    )
    def _init_sdk(self):
        self.sdk = SDK(
            username="me@test.com",
            password="password",
            project_id=str(uuid4()),
        )

    @pytest.fixture(autouse=True)
    def _mock_sleep(self):
        """
        This fixture overrides sleeps, so tests don't need to wait for
        the entire duration of a sleep command.
        """
        with patch("time.sleep"):
            yield

    def test_download_results_retry_on_exception(
        self, mock_request: requests_mock.mocker.Mocker
    ):
        """
        Test the retry logic for HTTP calls when an error status code is encountered.

        This test verifies that when an HTTP request fails with an error status code,
        the system retries the HTTP call 2 additional times, resulting in a total of
        3 HTTP calls.
        """

        mock_request.reset_mock()
        mock_request.register_uri(
            "GET", "http://result-link", status_code=500, text="fake-results"
        )
        with contextlib.suppress(Exception):
            self.sdk._client._download_results("http://result-link")
        assert len(mock_request.request_history) == 6

    def test_download_results_retry_on_connection_error(
        self, mock_request: requests_mock.mocker.Mocker
    ):
        """
        Test the retry logic for HTTP calls when a network error is encountered.

        This test verifies that when an HTTP request fails with
        requests.connectionError, the system retries the HTTP call 2 additional times,
        resulting in a total of 3 HTTP calls.
        """

        def raise_connection_error(*_):
            raise requests.ConnectionError

        mock_request.reset_mock()
        mock_request.register_uri(
            "GET", "http://result-link", body=raise_connection_error
        )

        with contextlib.suppress(requests.ConnectionError):
            self.sdk._client._download_results("http://result-link")
        assert len(mock_request.request_history) == 6

    @pytest.mark.parametrize("status_code", [408, 425, 429, 500, 502, 503, 504])
    def test_sdk_retry_on_exception(
        self, mock_request: requests_mock.mocker.Mocker, status_code: int
    ):
        """
        If a HTTP status code matches any of the codes passed as parameters,
        we should retry a HTTP call 5 more times.

        This test should confirm that 6 HTTP calls take place per "valid retry" status
        code.
        """
        mock_request.reset_mock()
        mock_request.register_uri("GET", "http://test-domain", status_code=status_code)
        with contextlib.suppress(Exception):
            self.sdk._client._authenticated_request("GET", "http://test-domain")
        assert len(mock_request.request_history) == 6

    def test_sdk_doesnt_retry_on_exceptions(
        self, mock_request: requests_mock.mocker.Mocker
    ):
        """
        If the HTTP status code is not one we consider valid for retires, we should not
        retry any HTTP calls again, since we most likely won't succeeed.

        This test should confirm that if we get a status code we don't want to try
        then our request total should be 1.
        """
        mock_request.reset_mock()
        mock_request.register_uri("GET", "http://test-domain", status_code=400)
        with contextlib.suppress(Exception):
            self.sdk._client._authenticated_request("GET", "http://test-domain")
        assert len(mock_request.request_history) == 1

    def test_sdk_200_avoids_all_exception_handling(
        self, mock_request: requests_mock.mocker.Mocker
    ):
        """
        We have no need to retry requests on a successful HTTP request, so
        this test confirms that if we receive a 200 success, then we don't try
        more than 1 request.
        """
        mock_request.reset_mock()
        mock_request.register_uri("GET", "http://test-domain", json={}, status_code=200)
        self.sdk._client._authenticated_request("GET", "http://test-domain")
        assert len(mock_request.request_history) == 1


class TestRequestAllPages:
    @pytest.fixture(autouse=True)
    @patch(
        "pasqal_cloud.client.Auth0TokenProvider",
        FakeAuth0AuthenticationSuccess,
    )
    def _init_sdk(self):
        self.sdk = SDK(
            username="me@test.com",
            password="password",
            project_id=str(uuid4()),
        )

    def test_pagination_request_success(
        self, mock_request: requests_mock.mocker.Mocker
    ):
        """
        Test requests with pagination with multiple pages.
        This test verifies that the pagination works correctly by simulating
        multiple pages of data.
        It checks that the correct number of requests is made and the
        combined response contains all the expected items.
        """

        mock_request.reset_mock()
        mock_request.register_uri(
            "GET",
            "http://core-test.com/jobs",
            json={
                "data": [{"id": 1}, {"id": 2}],
                "pagination": {"total": 6, "start": 0, "end": 2},
            },
            status_code=200,
        )
        mock_request.register_uri(
            "GET",
            "http://core-test.com/jobs?offset=2",
            json={
                "data": [{"id": 3}, {"id": 4}],
                "pagination": {"total": 6, "start": 2, "end": 4},
            },
            status_code=200,
        )
        mock_request.register_uri(
            "GET",
            "http://core-test.com/jobs?offset=4",
            json={
                "data": [{"id": 5}, {"id": 6}],
                "pagination": {"total": 6, "start": 4, "end": 6},
            },
            status_code=200,
        )

        response = self.sdk._client._request_all_pages(
            "GET", "http://core-test.com/jobs"
        )
        assert len(response) == 6
        assert response == [{"id": number} for number in range(1, 7)]
        assert len(mock_request.request_history) == 3

    def test_pagination_request_changed_total_items_during_query_success(
        self, mock_request: requests_mock.mocker.Mocker
    ):
        """
        Test request with pagination where the total number of items
        changes during the query.
        This test verifies that the pagination can handle situations where
        the total number of items changes between requests.
        It ensures that the system gracefully handles such changes
        without errors.
        """
        mock_request.reset_mock()
        mock_request.register_uri(
            "GET",
            "http://core-test.com/jobs",
            json={
                "data": [{"id": 1}, {"id": 2}],
                "pagination": {"total": 8, "start": 0, "end": 2},
            },
            status_code=200,
        )
        mock_request.register_uri(
            "GET",
            "http://core-test.com/jobs?offset=2",
            json={
                "data": [{"id": 3}, {"id": 4}],
                "pagination": {"total": 6, "start": 2, "end": 4},
            },
            status_code=200,
        )
        mock_request.register_uri(
            "GET",
            "http://core-test.com/jobs?offset=4",
            json={
                "data": [{"id": 5}],
                "pagination": {"total": 5, "start": 4, "end": 6},
            },
            status_code=200,
        )

        response = self.sdk._client._request_all_pages(
            "GET", "http://core-test.com/jobs"
        )
        assert len(response) == 5
        assert response == [{"id": number} for number in range(1, 6)]
        assert len(mock_request.request_history) == 3

    def test_request_pagination_without_pagination_success(
        self, mock_request: requests_mock.mocker.Mocker
    ):
        """
        Test request with pagination when there is only a single page of data.
        This test verifies that the pagination request function can handle responses
        without pagination metadata correctly, by returning the data without
        making additional requests.
        """
        mock_request.reset_mock()
        mock_request.register_uri(
            "GET",
            "http://core-test.com/jobs",
            json={
                "data": [{"id": 1}],
            },
            status_code=200,
        )

        response = self.sdk._client._request_all_pages(
            "GET", "http://core-test.com/jobs"
        )
        assert len(response) == 1
        assert response == [{"id": 1}]


class TestHeaders:
    @pytest.fixture(autouse=True)
    @patch(
        "pasqal_cloud.client.Auth0TokenProvider",
        FakeAuth0AuthenticationSuccess,
    )
    def _init_sdk(self):
        self.sdk = SDK(
            username="me@test.com",
            password="password",
            project_id=str(uuid4()),
        )

    def test_user_agent_in_request_headers(
        self, mock_request: requests_mock.mocker.Mocker
    ):
        """
        Test that the `_authenticated_request` method of
        the client injects the user-agent header properly
        in the headers.
        """
        mock_request.reset_mock()
        mock_request.register_uri(
            "GET", "http://core-test.com", status_code=200, json={"ok": True}
        )

        _ = self.sdk._client._authenticated_request("GET", "http://core-test.com")
        assert mock_request.last_request.headers["User-Agent"] == (
            f"PasqalCloudSDK/{sdk_version}"
        )
