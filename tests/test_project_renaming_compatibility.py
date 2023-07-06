from unittest.mock import patch

import pytest

from pasqal_cloud import SDK
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess

"""
Ticket (#622), Python file to be entirely removed
"""


@patch("pasqal_cloud.client.Auth0TokenProvider", FakeAuth0AuthenticationSuccess)
class TestInitSDKWithGroupId:
    project_id = "random_project_id"
    group_id = "random_group_id"
    username = "random_username"
    password = "random_password"

    @pytest.mark.filterwarnings(
        "ignore:The parameter 'group_id' is deprecated, from now on use 'project_id'"
        " instead"
    )
    def test_client_group_parameter(self):
        sdk = SDK(
            group_id=self.group_id, username=self.username, password=self.password
        )
        assert sdk._client.project_id == self.group_id

    def test_client_project_and_group_given(self):
        sdk = SDK(
            project_id=self.project_id,
            group_id=self.group_id,
            username=self.username,
            password=self.password,
        )
        assert sdk._client.project_id == self.project_id

    def test_client_group_and_project_arguments_not_given(self):
        with pytest.raises(
            TypeError,
            match=r"Either a 'group_id' or 'project_id' has to be given as argument",
        ):
            SDK(username=self.username, password=self.password)
