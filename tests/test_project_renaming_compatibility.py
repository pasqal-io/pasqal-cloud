from unittest.mock import patch
from uuid import uuid4

import pytest

from pasqal_cloud import SDK
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess


"""
Ticket (#622), Python file to be entirely removed
"""


@patch("pasqal_cloud.client.Auth0TokenProvider", FakeAuth0AuthenticationSuccess)
class TestSDKAndClientInit:
    group_id = "random_group_id"
    project_id = "random_project_id"
    username = "random_username"
    password = "random_password"

    def test_client_group_argument_converted_to_project(self):
        sdk = SDK(group_id=self.group_id, username=self.username, password=self.password)
        assert sdk._client.project_id == self.group_id

    def test_client_project_and_group_given(self):
        sdk = SDK(group_id=self.group_id, username=self.username, password=self.password)
        assert sdk._client.project_id == self.group_id

    def test_client_group_and_project_arguments_not_given(self):
        with pytest.raises(TypeError, match=r"Either a group_id or project_id has to be given as argument"):
            SDK(username=self.username, password=self.password)


class TestBatch:
    @pytest.fixture(autouse=True)
    @patch("pasqal_cloud.client.Auth0TokenProvider", FakeAuth0AuthenticationSuccess)
    def init_sdk(self, start_mock_request):
        self.sdk = SDK(
            username="me@test.com", password="password", project_id=str(uuid4())
        )
        self.pulser_sequence = "pulser_test_sequence"
        self.batch_id = "00000000-0000-0000-0000-000000000001"
        self.job_result = {"1001": 12, "0110": 35, "1111": 1}
        self.n_job_runs = 50
        self.job_id = "00000000-0000-0000-0000-000000022010"
        self.job_variables = {"Omega_max": 14.4, "last_target": "q1", "ts": [200, 500]}

    def test_create_batch(self):
        job = {"runs": self.n_job_runs, "variables": self.job_variables}
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[job],
            emulator=None,
        )
        assert batch.project_id == batch.group_id
