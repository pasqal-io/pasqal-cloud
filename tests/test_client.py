from unittest.mock import patch

import pytest
from auth0.v3.exceptions import Auth0Error  # type: ignore

from pasqal_cloud import Auth0Conf, Endpoints, SDK
from pasqal_cloud.authentication import TokenProvider
from tests.test_doubles.authentication import (
    FakeAuth0AuthenticationFailure,
    FakeAuth0AuthenticationSuccess,
)


@patch("pasqal_cloud.client.Auth0TokenProvider", FakeAuth0AuthenticationSuccess)
class TestAuthSuccess:
    project_id = "random_project_id"
    username = "random_username"
    password = "random_password"
    new_core_endpoint = "random_endpoint"

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
                return "your-token" # Replace this value with your token
        SDK(token_provider=CustomTokenProvider(), project_id="project_id")

    def test_correct_endpoints(self):
        sdk = SDK(
            project_id=self.project_id,
            username=self.username,
            password=self.password,
            endpoints=Endpoints(core=self.new_core_endpoint),
        )
        assert sdk._client.endpoints.core == self.new_core_endpoint

    def test_correct_new_auth0(self):
        new_auth0 = Auth0Conf(domain="new_domain")
        SDK(
            project_id=self.project_id,
            username=self.username,
            password=self.password,
            auth0=new_auth0,
        )


@patch("pasqal_cloud.client.Auth0TokenProvider", FakeAuth0AuthenticationFailure)
class TestAuthFailure:
    project_id = "random_project_id"
    username = "random_username"
    no_username = ""
    password = "random_password"
    no_password = ""

    @patch("pasqal_cloud.client.getpass")
    def test_module_getpass_bad_password(self, getpass):
        getpass.return_value = self.password

        with pytest.raises(Auth0Error):
            SDK(project_id=self.project_id, username=self.username)

        getpass.assert_called_once()

    def test_module_bad_password(self):
        with pytest.raises(Auth0Error):
            SDK(project_id=self.project_id, username=self.username, password=self.password)


class TestAuthInvalidClient:
    project_id = "random_project_id"
    username = "random_username"
    no_username = ""
    password = "random_password"
    no_password = ""

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
