from unittest.mock import patch

import pytest
from auth0.v3.exceptions import Auth0Error  # type: ignore

from pasqal_cloud import AUTH0_CONFIG, Auth0Conf, Endpoints, PASQAL_ENDPOINTS, SDK
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
    def test_select_env(self, env, core_endpoint_expected):
        sdk = SDK(
            project_id=self.project_id,
            username=self.username,
            password=self.password,
            auth0=AUTH0_CONFIG[env],
            endpoints=PASQAL_ENDPOINTS[env],
        )
        assert sdk._client.endpoints.core == core_endpoint_expected
