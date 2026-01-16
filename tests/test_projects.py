from unittest.mock import patch

import pytest
import requests_mock
from pasqal_cloud import ProjectNotFoundError, SDK

from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess


class TestProject:
    @pytest.fixture(autouse=True)
    @patch(
        "pasqal_cloud.client.Auth0TokenProvider",
        FakeAuth0AuthenticationSuccess,
    )
    @patch(
        "pasqal_cloud.client.PasswordGrantTokenProvider", FakeAuth0AuthenticationSuccess
    )
    def _init_sdk(self):
        self.project_id = "73feca86-a140-4ed8-a8e7-fe71428e0542"
        self.sdk = SDK(
            username="me@test.com", password="password", project_id=self.project_id
        )

    def test_get_all_projects(
        self,
        mock_request: requests_mock.mocker.Mocker,
    ):
        mock_request.reset_mock()
        projects = self.sdk.get_all_projects()
        assert len(projects) == 2

    def test_switch_to_other_existing_project(
        self,
        mock_request: requests_mock.mocker.Mocker,
    ):
        mock_request.reset_mock()
        assert self.sdk.project_id == self.project_id
        new_project_id = "54fd6ddf-73a6-45de-89c5-554ac48f8626"
        second_project_id = self.sdk.switch_to_project(new_project_id)
        assert second_project_id == new_project_id
        assert self.sdk.project_id == new_project_id

    def test_switch_to_other_non_existing_project(
        self,
        mock_request: requests_mock.mocker.Mocker,
    ):
        mock_request.reset_mock()
        assert self.sdk.project_id == self.project_id
        new_project_id = "00000000-0000-0000-0000-000000000001"
        with pytest.raises(
            ProjectNotFoundError,
            match="Project ID 00000000-0000-0000-0000-000000000001 does not "
            "exist or you are not a member of it.",
        ):
            self.sdk.switch_to_project(new_project_id)
        assert self.sdk.project_id == self.project_id
