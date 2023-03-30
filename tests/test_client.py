from __future__ import annotations


from auth0.v3.exceptions import Auth0Error
import pytest
from typing import Any

from unittest.mock import patch
from sdk import SDK, Endpoints, Auth0Conf
from sdk.authentication import TokenProvider


class FakeAuth0GoodAuthentication(TokenProvider):
    def _query_token(self) -> dict[str, Any]:
        return {
            "access_token": "some_token",
            "id_token": "id_token",
            "scope": "openid profile email",
            "expires_in": 86400,
            "token_type": "Bearer",
        }


class FakeAuth0BadAuthentication(TokenProvider):
    def __init__(self, *args: tuple, **kwags: dict):
        """The arguments are not important.
        What's important is that the init raise the error below.
        """
        self._query_token()

    def _query_token(self) -> dict[str, Any]:
        """The lib raises a Auth0Error, but I raise a ValueError in order
        not to confused the tests. If a Auth0Error is raised, it's
        because we didn't mock properly.
        """
        raise ValueError()


@patch("sdk.client.Auth0TokenProvider", FakeAuth0GoodAuthentication)
class TestAuthSuccess:
    group_id = "random_group_id"
    username = "random_username"
    password = "random_password"
    new_core_endpoint = "random_endpoint"

    @patch("sdk.client.getpass")
    def test_module_getpass_success(self, getpass):
        getpass.return_value = self.password
        SDK(group_id=self.group_id, username=self.username)
        getpass.assert_called_once()

    def test_authentication_success(self):
        SDK(group_id=self.group_id, username=self.username, password=self.password)

    def test_good_token_provider(self):
        SDK(group_id=self.group_id, token_provider=FakeAuth0GoodAuthentication)

    def test_correct_endpoints(self):
        sdk = SDK(
            group_id=self.group_id,
            username=self.username,
            password=self.password,
            endpoints=Endpoints(core=self.new_core_endpoint),
        )
        assert sdk._client.endpoints.core == self.new_core_endpoint

    def test_correct_new_auth0(self):
        new_auth0 = Auth0Conf(domain="new_domain")
        SDK(
            group_id=self.group_id,
            username=self.username,
            password=self.password,
            auth0=new_auth0,
        )


@patch("sdk.client.Auth0TokenProvider", FakeAuth0BadAuthentication)
class TestAuthFailure:
    group_id = "random_group_id"
    username = "random_username"
    no_username = ""
    password = "random_password"
    no_password = ""

    @patch("sdk.client.getpass")
    def test_module_getpass_bad_password(self, getpass):
        getpass.return_value = self.password

        with pytest.raises(ValueError):
            SDK(group_id=self.group_id, username=self.username)

        getpass.assert_called_once()

    def test_module_bad_password(self):
        with pytest.raises(ValueError):
            SDK(group_id=self.group_id, username=self.username, password=self.password)


class TestAuthInvalidClient:
    group_id = "random_group_id"
    username = "random_username"
    no_username = ""
    password = "random_password"
    no_password = ""

    def test_module_no_user_with_password(self):
        with pytest.raises(ValueError):
            SDK(
                group_id=self.group_id,
                username=self.no_username,
                password=self.password,
            )

    @patch("sdk.client.getpass")
    def test_module_no_password(self, getpass):
        getpass.return_value = ""
        with pytest.raises(ValueError):
            SDK(
                group_id=self.group_id,
                username=self.username,
                password=self.no_password,
            )

    @patch("sdk.client.getpass")
    def test_module_getpass_no_password(self, getpass):
        getpass.return_value = self.no_password

        with pytest.raises(ValueError):
            SDK(group_id=self.group_id, username=self.username)

        getpass.assert_called_once()

    def test_bad_token_provider(self):
        with pytest.raises(TypeError):
            SDK(group_id=self.group_id, token_provider="token")

    def test_bad_auth0(self):
        with pytest.raises(TypeError):
            SDK(
                group_id=self.group_id,
                username=self.username,
                password=self.password,
                auth0="",
            )

    def test_authentication_no_credentials_provided(self):
        with pytest.raises(ValueError):
            SDK(group_id=self.group_id)

    def test_bad_endpoints(self):
        with pytest.raises(TypeError):
            SDK(
                group_id=self.group_id,
                username=self.username,
                password=self.password,
                endpoints={
                    "core": "",
                    "account": "",
                },
            )
