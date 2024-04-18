from unittest.mock import patch

import pytest
from auth0.v3.exceptions import Auth0Error  # type: ignore

from pasqal_cloud import (
    AUTH0_CONFIG,
    Auth0Conf,
    Endpoints,
    PASQAL_ENDPOINTS,
    SDK,
    Client,
)
from pasqal_cloud.authentication import TokenProvider
from tests.test_doubles.authentication import (
    FakeAuth0AuthenticationFailure,
    FakeAuth0AuthenticationSuccess,
)
import json
from typing import Any, Generator, Dict
from uuid import uuid4


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
    def test_module_no_user_with_password(self):
        with pytest.raises(ValueError):
            SDK(
                project_id=self.project_id,
                username=self.no_username,
                password=self.password,
            )

    @patch("pasqal_cloud.client.getpass")
    def test_module_no_password(self, getpass):
        getpass.return_value = ""
        with pytest.raises(ValueError):
            SDK(
                project_id=self.project_id,
                username=self.username,
                password=self.no_password,
            )

    @patch("pasqal_cloud.client.getpass")
    def test_module_getpass_no_password(self, getpass):
        getpass.return_value = self.no_password

        with pytest.raises(ValueError):
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
        with pytest.raises(ValueError):
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
        "env, core_endpoint_expected",
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
    def init_sdk(self):
        self.sdk = SDK(
            username="me@test.com",
            password="password",
            project_id=str(uuid4()),
        )

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """
        This fixture overrides sleeps, so tests don't need to wait for
        the entire duration of a sleep command.
        """
        with patch("time.sleep"):
            yield

    @pytest.mark.parametrize("status_code", [408, 425, 429, 500, 502, 503, 504])
    def test_sdk_retry_on_exception(
        self, mock_request: Generator[Any, Any, None], status_code: int
    ):
        """
        If a HTTP status code matches any of the codes passed as parameters,
        we should retry a HTTP call 5 more times.

        This test should confirm that 6 HTTP calls take place per "valid retry" status
        code.
        """
        mock_request.reset_mock()
        mock_request.register_uri("GET", "http://test-domain", status_code=status_code)
        try:
            self.sdk._client._request("GET", "http://test-domain")
        except Exception:
            ...
        assert len(mock_request.request_history) == 6

    def test_sdk_doesnt_retry_on_exceptions(
        self, mock_request: Generator[Any, Any, None]
    ):
        """
        If the HTTP status code is not one we consider valid for retires, we should not
        retry any HTTP calls again, since we most likely won't succeeed.

        This test should confirm that if we get a status code we don't want to try
        then our request total should be 1.
        """
        mock_request.reset_mock()
        mock_request.register_uri("GET", "http://test-domain", status_code=400)
        try:
            self.sdk._client._request("GET", "http://test-domain")
        except Exception:
            ...
        assert len(mock_request.request_history) == 1

    def test_sdk_200_avoids_all_exception_handling(
        self, mock_request: Generator[Any, Any, None]
    ):
        """
        We have no need to retry requests on a successful HTTP request, so
        this test confirms that if we receive a 200 success, then we don't try
        more than 1 request.
        """
        mock_request.reset_mock()
        mock_request.register_uri("GET", "http://test-domain", json={}, status_code=200)
        self.sdk._client._request("GET", "http://test-domain")
        assert len(mock_request.request_history) == 1
