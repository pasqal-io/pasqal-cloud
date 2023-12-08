import json
import requests
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from pasqal_cloud import SDK, Workload
from pasqal_cloud.errors import (
    WorkloadCancellingError,
    WorkloadCreationError,
    WorkloadFetchingError,
    WorkloadResultsConnectionError,
    WorkloadResultsDecodeError,
)
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess


class TestWorkload:
    @pytest.fixture
    def workload_with_link_id(self) -> str:
        return str(UUID(int=0x2))

    @pytest.fixture
    def workload_with_invalid_link_id(self) -> str:
        return str(UUID(int=0x3))

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
        self.workload_id = "00000000-0000-0000-0000-000000000001"
        self.backend = "backend_test"
        self.workload_type = "workload_type_test"
        self.config = {"test1": "test1", "test2": 2}
        self.workload_result = {"1001": 12, "0110": 35, "1111": 1}

    def test_create_workload(self, mock_request):
        workload = self.sdk.create_workload(
            backend=self.backend,
            workload_type=self.workload_type,
            config=self.config,
        )
        assert workload.id == self.workload_id
        assert workload.backend == self.backend
        assert workload.workload_type == self.workload_type
        assert workload.config == self.config
        assert (
            mock_request.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/workloads"
        )
        assert mock_request.last_request.method == "POST"

    def test_create_workload_error(self, mock_request_exception):
        with pytest.raises(WorkloadCreationError):
            _ = self.sdk.create_workload(
                backend=self.backend,
                workload_type=self.workload_type,
                config=self.config,
            )
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/workloads"
        )
        assert mock_request_exception.last_request.method == "POST"

    def test_create_workload_and_wait(self, mock_request):
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
        assert mock_request.last_request.method == "GET"

    def test_get_workload(self, mock_request, workload):
        workload_requested = self.sdk.get_workload(workload.id)
        assert workload_requested.id == self.workload_id
        assert (
            mock_request.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v2/workloads/{self.workload_id}"
        )

    def test_get_workload_with_link(
        self, mock_request, workload_with_link_id, result_link_endpoint
    ):
        self.sdk.get_workload(workload_with_link_id)
        assert mock_request.last_request.url == (
            f"{result_link_endpoint}{workload_with_link_id}"
        )

    def test_get_workload_with_invalid_link(
        self, workload_with_invalid_link_id, mock_request
    ):
        with pytest.raises(WorkloadResultsDecodeError):
            self.sdk.get_workload(workload_with_invalid_link_id)
        assert (
            mock_request.last_request.url
            == "http://invalid-link/00000000-0000-0000-0000-000000000003"
        )

    def test_get_workload_error(self, mock_request_exception, workload):
        with pytest.raises(WorkloadFetchingError):
            _ = self.sdk.get_workload(workload.id)
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}"
            f"/api/v2/workloads/{self.workload_id}"
        )
        assert mock_request_exception.last_request.method == "GET"

    def test_cancel_workload_self(self, mock_request, workload):
        workload.cancel()
        assert workload.status == "CANCELED"
        assert mock_request.last_request.method == "PUT"
        assert (
            mock_request.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/workloads/{self.workload_id}/cancel"
        )

    def test_cancel_workload_self_error(self, mock_request_exception, workload):
        with pytest.raises(WorkloadCancellingError):
            workload.cancel()
        assert workload.status == "PENDING"
        assert mock_request_exception.last_request.method == "PUT"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/workloads/{self.workload_id}/cancel"
        )

    def test_cancel_workload_sdk(self, mock_request, workload):
        client_rsp = self.sdk.cancel_workload(self.workload_id)
        assert type(client_rsp) == Workload
        assert client_rsp.status == "CANCELED"
        assert mock_request.last_request.method == "PUT"
        assert (
            mock_request.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/workloads/{self.workload_id}/cancel"
        )

    def test_cancel_workload_sdk_error(self, mock_request_exception, workload):
        with pytest.raises(WorkloadCancellingError):
            _ = self.sdk.cancel_workload(self.workload_id)
        assert workload.status == "PENDING"
        assert mock_request_exception.last_request.method == "PUT"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}"
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

    def test_workload_result_raise_connection_error(self, workload):
        """
        Check that error is raised when improper url is set.
        """
        workload_dict = workload.dict()
        workload_dict.pop("result")
        workload_dict["result_link"] = "http://test.test"
        with pytest.raises(WorkloadResultsConnectionError):
            Workload(**workload_dict)

    def tests_workload_result_set(self, workload):
        """
        Check that result is set when only result_link is provided.
        """
        workload_dict = workload.dict()
        workload_dict.pop("result")
        workload_dict["result_link"] = "http://test.test"
        resp = requests.Response()
        resp._content = json.dumps({"some": "data"}).encode("utf-8")
        with patch("requests.get", lambda x: resp):
            res = Workload(**workload_dict)
        assert res.result == {"some": "data"}
