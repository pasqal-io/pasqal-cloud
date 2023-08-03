from unittest.mock import patch
from uuid import uuid4

import pytest

from pasqal_cloud import SDK, Workload
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess


class TestWorkload:
    @pytest.fixture(autouse=True)
    @patch(
        "pasqal_cloud.client.Auth0TokenProvider",
        FakeAuth0AuthenticationSuccess,
    )
    def init_sdk(self, start_mock_request):
        self.sdk = SDK(
            username="me@test.com",
            password="password",
            project_id=str(uuid4()),
        )
        self.workload_id = "00000000-0000-0000-0000-000000000001"
        self.backend = "backend_test"
        self.workload_type = "workload_type_test"
        self.config = {"test1": "test1", "test2": 2}
        self.workload_result = {"1001": 12, "0110": 35, "1111": 1}

    def test_create_workload(self):
        workload = self.sdk.create_workload(
            backend=self.backend,
            workload_type=self.workload_type,
            config=self.config,
        )
        assert workload.id == self.workload_id
        assert workload.backend == self.backend
        assert workload.workload_type == self.workload_type
        assert workload.config == self.config

    def test_create_workload_and_wait(self, request_mock):
        workload = self.sdk.create_workload(
            backend=self.backend,
            workload_type=self.workload_type,
            config=self.config,
            wait=True,
        )
        assert workload.id == self.workload_id
        assert workload.backend == self.backend
        assert workload.workload_type == self.workload_type
        assert workload.config == self.config
        assert workload.result == self.workload_result
        assert request_mock.last_request.method == "GET"

    def test_get_workload(self, request_mock, workload):
        workload_requested = self.sdk.get_workload(workload.id)
        assert workload_requested.id == self.workload_id
        assert (
            request_mock.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/workloads/{self.workload_id}"
        )

    def test_cancel_workload_self(self, request_mock, workload):
        workload.cancel()
        assert workload.status == "CANCELED"
        assert request_mock.last_request.method == "PUT"
        assert (
            request_mock.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/workloads/{self.workload_id}/cancel"
        )

    def test_cancel_workload_sdk(self, request_mock, workload):
        client_rsp = self.sdk.cancel_workload(self.workload_id)
        assert type(client_rsp) == Workload
        assert client_rsp.status == "CANCELED"
        assert request_mock.last_request.method == "PUT"
        assert (
            request_mock.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/workloads/{self.workload_id}/cancel"
        )

    def test_workload_instantiation_with_extra_field(self, workload):
        """Instantiating a workload with an extra field should not raise an error.

        This enables us to add new fields in the API response on the workloads endpoint
        without breaking compatibility for users with old versions of the SDK where
        the field is not present in the Batch class.
        """
        workload_dict = workload.dict()  # Batch data expected by the SDK
        # We add an extra field to mimick the API exposing new values to the user
        workload_dict["new_field"] = "any_value"

        new_workload = Workload(**workload_dict)  # this should raise no error
        assert (
            new_workload.new_field == "any_value"
        )  # The new value should be stored regardless
