import contextlib
import json
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Union
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
import requests
import requests_mock
from pasqal_cloud import (
    Batch,
    BatchCancellationResponse,
    Job,
    PaginatedResponse,
    PaginationParams,
    RebatchFilters,
    SDK,
)
from pasqal_cloud.batch import Batch as BatchModel
from pasqal_cloud.device import (
    BaseConfig,
    DeviceTypeName,
    EmuFreeConfig,
    EmulatorType,
    EmuTNConfig,
)
from pasqal_cloud.errors import (
    BatchCancellingError,
    BatchClosingError,
    BatchCreationError,
    BatchFetchingError,
    JobCreationError,
    JobRetryError,
    OnlyCompleteOrOpenCanBeSet,
    RebatchError,
)
from pasqal_cloud.utils.constants import BatchStatus, JobStatus
from pasqal_cloud.utils.filters import BatchFilters

from tests.conftest import mock_core_response
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess
from tests.utils import build_query_params, mock_500_http_error_response


class TestBatch:
    @pytest.fixture
    def load_mock_batch_json_response(self) -> Dict[str, Any]:
        with open("tests/fixtures/api/v1/batches/_.POST.json") as f:
            return json.load(f)

    @pytest.fixture(autouse=True)
    def _mock_sleep(self):
        """
        This fixture overrides sleeps, so tests don't need to wait for
        the entire duration of a sleep command.
        """
        with patch("time.sleep"):
            yield

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
        self.pulser_sequence = "pulser_test_sequence"
        self.batch_id = "00000000-0000-0000-0000-000000000001"
        self.job_id = "00000000-0000-0000-0000-000000022010"
        self.n_job_runs = 50
        self.job_variables = {
            "Omega_max": 14.4,
            "last_target": "q1",
            "ts": [200, 500],
        }
        self.simple_job_args = {
            "runs": self.n_job_runs,
            "variables": self.job_variables,
        }
        self.job_result = {"1001": 12, "0110": 35, "1111": 1}
        self.job_full_result = {
            "counter": {"1001": 12, "0110": 35, "1111": 1},
            "raw": ["1001", "1001", "0110", "1001", "0110"],
        }
        self.tags = ["test"]

    @pytest.mark.parametrize("device_type", DeviceTypeName.list())
    def test_create_batch(
        self, device_type: DeviceTypeName, mock_request: requests_mock.mocker.Mocker
    ):
        """
        When successfully creating a batch, we should be able to assert
        certain fields and values are in the assigned return object.
        """
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[self.simple_job_args],
            device_type=device_type,
            tags=self.tags,
        )
        assert batch.id == self.batch_id
        assert not batch.open
        assert batch.complete
        assert batch.ordered_jobs[0].batch_id == batch.id
        assert mock_request.last_request.method == "POST"
        assert batch.sequence_builder == self.pulser_sequence
        assert mock_request.last_request.method == "GET"
        assert batch.tags == self.tags

    @pytest.mark.parametrize("device_type", DeviceTypeName.list())
    def test_create_batch_with_complete_raises_warning(
        self, device_type: DeviceTypeName, mock_request: requests_mock.mocker.Mocker
    ):
        """
        Test that using complete at batch definition is still accepted but will
        trigger a deprecation warning.
        """
        with pytest.warns(DeprecationWarning):
            batch = self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
                jobs=[self.simple_job_args],
                device_type=device_type,
                complete=True,
            )
        assert batch.id == self.batch_id
        assert not batch.open
        assert mock_request.last_request.method == "POST"
        assert batch.sequence_builder == self.pulser_sequence
        assert mock_request.last_request.method == "GET"

    @pytest.mark.parametrize("device_type", DeviceTypeName.list())
    def test_create_batch_open_and_complete_raises_error(
        self, device_type: DeviceTypeName
    ):
        """
        Test that setting both complete and open values will result in the proper
        error being raised.
        """
        with pytest.raises(OnlyCompleteOrOpenCanBeSet):
            _ = self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
                jobs=[self.simple_job_args],
                device_type=device_type,
                complete=True,
                open=True,
            )

    @pytest.mark.parametrize("emulator", EmulatorType.list())
    def test_create_batch_with_emulator_raises_warning(
        self, emulator: Optional[str], mock_request: requests_mock.mocker.Mocker
    ):
        """
        Test that using emulator at batch definition is still accepted but will
        trigger a deprecation warning.
        """
        with pytest.warns(DeprecationWarning):
            batch = self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
                jobs=[self.simple_job_args],
                emulator=emulator,
                open=True,
            )
        assert batch.id == self.batch_id
        assert mock_request.last_request.method == "POST"
        assert batch.sequence_builder == self.pulser_sequence
        assert mock_request.last_request.method == "GET"
        assert not batch.open

    def test_batch_create_exception(
        self, mock_request_exception: requests_mock.mocker.Mocker
    ):
        """
        Assert the correct exception is raised when failing to create a batch
        and that the correct methods and URLs are used.
        """
        with pytest.raises(BatchCreationError):
            _ = self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence, jobs=[self.simple_job_args]
            )

        assert mock_request_exception.last_request.method == "POST"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches"
        )

    @pytest.mark.filterwarnings(
        "ignore:Argument `fetch_results` is deprecated and will be removed "
        "in a future version. Please use argument `wait` instead"
    )
    @pytest.mark.parametrize(("wait", "fetch_results"), [(True, False), (False, True)])
    def test_create_batch_and_wait(
        self, mock_request: requests_mock.mocker.Mocker, wait: bool, fetch_results: bool
    ):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[self.simple_job_args],
            wait=wait,
            fetch_results=fetch_results,
        )
        assert (
            batch.id == "00000000-0000-0000-0000-000000000001"
        )  # the batch_id used in the mock data
        assert batch.sequence_builder == self.pulser_sequence
        assert not batch.open
        assert batch.complete
        assert batch.ordered_jobs
        assert batch.ordered_jobs[0].id == self.job_id
        assert batch.ordered_jobs[0].result == self.job_result
        assert batch.ordered_jobs[0].full_result == self.job_full_result
        # Ticket (#704)
        with pytest.warns(
            DeprecationWarning,
            match="'jobs' attribute is deprecated, use 'ordered_jobs' instead",
        ):
            for job_id, job in batch.jobs.items():
                assert self.job_id == job_id
                assert job.result == self.job_result
                assert job.full_result == self.job_full_result
            assert len(batch.jobs) == len(batch.ordered_jobs)
        assert mock_request.last_request.method == "GET"

    @pytest.mark.usefixtures("mock_request")
    def test_get_batch(self, batch: Batch):
        """
        Assert that with a mocked, successful HTTP request our get_batch
        function returns an insance of the Batch model used in the SDK.
        """
        batch_requested = self.sdk.get_batch(batch.id)
        assert isinstance(batch_requested, BatchModel)

    def test_batch_add_jobs(self, mock_request: requests_mock.mocker.Mocker):
        """
        Test that after successfully creating, and adding jobs, the total number of jobs
        associated with a batch is correct, and the batch id is in the URL that was most
        recently called.
        """
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence, jobs=[self.simple_job_args]
        )
        batch.add_jobs([{"runs": self.n_job_runs, "variables": self.job_variables}])
        assert batch.id in mock_request.last_request.url
        assert len(batch.ordered_jobs) == 2

    def test_batch_add_jobs_failure(
        self, batch, mock_request_exception: requests_mock.mocker.Mocker
    ):
        """
        When trying to add jobs to a batch, we test that we catch
        an exception JobCreationError while later validating the HTTP method
        and URL executed.
        """
        with pytest.raises(JobCreationError):
            _ = batch.add_jobs(
                [{"runs": self.n_job_runs, "variables": self.job_variables}]
            )
        assert mock_request_exception.last_request.method == "POST"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v2/batches/{batch.id}/jobs"
        )

    def test_batch_add_jobs_and_wait_for_results(
        self,
        batch: Batch,
        mock_request: requests_mock.mocker.Mocker,
        load_mock_batch_json_response: Dict[str, Any],
    ):
        mock_request.reset_mock()
        # Override the batch id so that we load the right API fixtures
        batch.id = "00000000-0000-0000-0000-000000000002"

        # List of job statuses for each request to the get batch endpoint
        # We should keep fetching until jobs are terminated (DONE or ERROR)
        job_statuses = [
            ("PENDING", "PENDING"),  # First call, both jobs are PENDING
            ("RUNNING", "PENDING"),  # Second call, first job has started
            ("DONE", "PENDING"),  # Third call, first job is done
            (
                "DONE",
                "ERROR",
            ),  # Last call, the second job has an ERROR, both jobs are now terminated
        ]

        call_count = 0  # Count calls to the GET endpoint

        def custom_get_batch_mock(request, _):
            nonlocal call_count
            resp = mock_core_response(request)
            # Override with custom status the fixture data
            resp["data"]["jobs"][0]["status"] = job_statuses[call_count][0]
            resp["data"]["jobs"][1]["status"] = job_statuses[call_count][1]
            call_count += 1
            return resp

        mock_request.register_uri(
            "GET", f"/core-fast/api/v1/batches/{batch.id}", json=custom_get_batch_mock
        )

        mock_request.register_uri(
            "POST",
            f"/core-fast/api/v1/batches/{batch.id}/jobs",
            json=load_mock_batch_json_response,
        )
        batch.add_jobs(
            [{"runs": self.n_job_runs}, {"runs": self.n_job_runs}],
            wait=True,
        )

        # Several calls take place to POST /core-fast/api/v1/batches
        # and GET core-fast/api/v1/batches/{id}
        assert mock_request.call_count == 3

        assert mock_request.request_history[0].method == "POST"
        methods = {req.method for req in mock_request.request_history}

        # Check both GET and POST methods execute
        assert {"GET", "POST"} == methods

        assert all(job.result == self.job_result for job in batch.ordered_jobs)
        assert all(
            job.full_result == self.job_full_result for job in batch.ordered_jobs
        )

    @pytest.mark.usefixtures("mock_request")
    def test_batch_declare_complete(self, batch: Batch):
        """
        Test that calling declare_complete on the batch will
        raise a deprecation warning.
        """
        with pytest.warns(DeprecationWarning):
            batch.declare_complete(wait=False)
        assert batch.complete
        assert not batch.open

    @pytest.mark.usefixtures("mock_request")
    def test_batch_close(self, batch: Batch):
        batch.close(wait=False)
        assert batch.complete
        assert not batch.open

    def test_batch_close_failure(
        self, batch: Batch, mock_request_exception: requests_mock.mocker.Mocker
    ):
        with pytest.raises(BatchClosingError):
            _ = batch.close(wait=False)

        assert batch.status == "PENDING"
        mock_request_exception.stop()

    def test_batch_close_and_wait_for_results(
        self, batch: Batch, mock_request: requests_mock.mocker.Mocker
    ):
        """TODO"""
        batch.close(wait=True)
        assert batch.complete
        assert not batch.open
        assert mock_request.last_request.method == "GET"
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v2/jobs?batch_id={batch.id}"
            "&order_by=ordered_id&order_by_direction=ASC"
        )
        assert batch.ordered_jobs[0].batch_id == batch.id
        assert batch.ordered_jobs[0].result == self.job_result
        assert batch.ordered_jobs[0].full_result == self.job_full_result
        assert len(batch.ordered_jobs) == 1

    def test_cancel_batch_self(self, mock_request, batch):
        batch.cancel()
        assert batch.status == "CANCELED"
        assert mock_request.last_request.method == "PATCH"
        assert (
            mock_request.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v2/batches/{self.batch_id}/cancel"
        )

    def test_cancel_batch_self_error(self, mock_request_exception, batch):
        with pytest.raises(BatchCancellingError):
            batch.cancel()
        assert batch.status == "PENDING"
        assert mock_request_exception.last_request.method == "PATCH"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}"
            f"/api/v2/batches/{self.batch_id}/cancel"
        )

    def test_cancel_batch_sdk(self, mock_request):
        client_rsp = self.sdk.cancel_batch(self.batch_id)
        assert isinstance(client_rsp, Batch)
        assert client_rsp.status == "CANCELED"
        assert mock_request.last_request.method == "PATCH"
        assert (
            mock_request.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v2/batches/{self.batch_id}/cancel"
        )

    def test_cancel_batch_sdk_error(
        self, mock_request_exception: requests_mock.mocker.Mocker
    ):
        """
        Assert that a BatchCancellingError is raised appropriately for
        failling requests when calling sdk.cancel_batch(...)

        This test also assert the most recently used HTTP method and URL
        are correct.
        """
        with pytest.raises(BatchCancellingError):
            _ = self.sdk.cancel_batch(self.batch_id)

        assert mock_request_exception.last_request.method == "PATCH"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}"
            f"/api/v2/batches/{self.batch_id}/cancel"
        )

    @pytest.mark.parametrize(
        ("device_type", "configuration", "expected"),
        [
            (DeviceTypeName.EMU_TN, EmuTNConfig(), EmuTNConfig()),
            (DeviceTypeName.EMU_FRESNEL, None, None),
            (DeviceTypeName.EMU_MPS, None, None),
            (
                DeviceTypeName.EMU_FREE,
                EmuFreeConfig(),
                EmuFreeConfig(extra_config={"dt": 10.0, "precision": "normal"}),
            ),
            (None, None, None),
        ],
    )
    @pytest.mark.usefixtures("mock_request")
    def test_create_batch_configuration(
        self, device_type: str, configuration: BaseConfig, expected: BaseConfig
    ):
        """
        Assert that when creating a batch with a certain confiuration,
        we create the exected object
        """
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[self.simple_job_args],
            device_type=device_type,
            configuration=configuration,
        )
        assert batch.configuration == expected

    def test_batch_instantiation_with_extra_field(self, batch: Batch):
        """Instantiating a batch with an extra field should not raise an error.

        This enables us to add new fields in the API response on the batches endpoint
        without breaking compatibility for users with old versions of the SDK where
        the field is not present in the Batch class.
        """
        batch_dict = batch.model_dump()  # Batch data expected by the SDK
        # We add an extra field to mimick the API exposing new values to the user
        batch_dict["new_field"] = "any_value"

        new_batch = Batch(**batch_dict)  # this should raise no error
        assert (
            new_batch.new_field == "any_value"
        )  # The new value should be stored regardless

    @pytest.mark.usefixtures("mock_request")
    def test_create_batch_fetch_results_deprecated(
        self,
    ):
        """
        When trying to retrieve batch results with a deprecated argument
        we are able to confirm a certain warning is raised in response.
        """
        with pytest.warns(DeprecationWarning):
            self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
                jobs=[self.simple_job_args],
                fetch_results=True,
            )

    @pytest.mark.usefixtures("mock_request")
    def test_get_batch_fetch_results_deprecated(
        self,
    ):
        """Assert that when we use the deprecated argument
        'fetch_results', we receive a DeprecationWarning"""
        with pytest.warns(DeprecationWarning):
            self.sdk.get_batch(self.batch_id, fetch_results=True)

    @pytest.mark.parametrize(
        "filters",
        [
            # No filters provided
            None,
            # Empty object
            RebatchFilters(),
            # Job ID as UUID
            RebatchFilters(id=[UUID(int=0x1)]),
            # Start date
            RebatchFilters(start_date=datetime(2023, 1, 1)),
            # End date
            RebatchFilters(end_date=datetime(2023, 1, 1)),
            # Single job status
            RebatchFilters(status=JobStatus.DONE),
            # List of job statuses
            RebatchFilters(status=[JobStatus.DONE, JobStatus.PENDING]),
            # Minimum runs
            RebatchFilters(min_runs=10),
            # Maximum runs
            RebatchFilters(max_runs=10),
            # Combined
            RebatchFilters(
                id=[UUID(int=0x1)],
                status=[JobStatus.DONE, JobStatus.PENDING],
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 1),
            ),
        ],
    )
    def test_rebatch_success(
        self,
        mock_request: requests_mock.mocker.Mocker,
        filters: Union[RebatchFilters, None],
    ):
        """
        As a user using the SDK with proper credentials,
        I can rebatch an existing batch with specific filters.
        The resulting request will create a new batch which includes
        copies of the jobs that match the filters.
        """
        batch = self.sdk.rebatch(self.batch_id, filters=filters)
        assert mock_request.last_request.method == "POST"

        # Convert filters to the appropriate format for query parameters
        query_params = build_query_params(
            filters.model_dump(exclude_unset=True) if filters is not None else None,
        )

        # Check that the correct url was requested with query params
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches/"
            + f"{self.batch_id}/rebatch{query_params}"
        )
        assert batch.parent_id == self.batch_id
        assert batch.ordered_jobs[0].parent_id

    def test_rebatch_sdk_error(
        self, mock_request_exception: requests_mock.mocker.Mocker
    ):
        """
        As a user using the SDK with proper credentials,
        if my request for rebatching returns a status code
        different from 200,
        I am faced with the RebatchError exception.
        """
        with pytest.raises(RebatchError):
            _ = self.sdk.rebatch(self.batch_id)
        assert mock_request_exception.last_request.method == "POST"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches/"
            + f"{self.batch_id}/rebatch"
        )

    def test_retry(
        self,
        mock_request: requests_mock.mocker.Mocker,
    ):
        """
        As a user using the SDK with proper credentials,
        I can retry a job from a given batch.
        The resulting job is added to the batch ordered jobs
        and shares the same variables and results as the original job.
        The endpoint to add jobs was called.
        """
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[self.simple_job_args],
        )
        assert len(batch.ordered_jobs) == 1
        batch.retry(batch.ordered_jobs[0])
        assert len(batch.ordered_jobs) == 2
        assert batch.ordered_jobs[1].variables == batch.ordered_jobs[0].variables
        assert batch.ordered_jobs[1].runs == batch.ordered_jobs[0].runs
        assert mock_request.last_request.method == "POST"
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v2/batches/"
            + f"{self.batch_id}/jobs"
        )

    def test_retry_sdk_error(
        self,
        batch: Batch,
        job: Job,
        mock_request_exception: requests_mock.mocker.Mocker,
    ):
        """
        As a user using the SDK with proper credentials,
        if my request for retrying a job returns a status code
        different from 200,
        I am faced with the JobRetryError exception.
        """
        batch.ordered_jobs = [job]
        with pytest.raises(JobRetryError):
            batch.retry(job)

        assert len(batch.ordered_jobs) == 1
        assert mock_request_exception.last_request.method == "POST"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v2/batches/"
            + f"{self.batch_id}/jobs"
        )

    def test_add_jobs_calls_the_correct_features(
        self,
        mock_request: requests_mock.mocker.Mocker,
    ):
        """
        Assert than we calling add_jobs that the correct
        HTTP request method and URL are used.

        We also confirm an instance the correct model
        is returned. The inline mock function allows the reuse
        of an already existing fixture while just overriding a
        the values we want.
        """
        mock_request.reset_mock()

        def inline_mock_batch_response(request, _):
            resp = mock_core_response(request)
            resp["data"]["complete"] = False
            resp["data"]["open"] = True
            resp["data"]["id"] = self.batch_id
            return resp

        # Inline mock assures we reach the end of the function body to call `core`.
        # The add_jobs method has a condition to raise an Exception
        # if the batch is complete.
        mock_request.register_uri(
            "GET",
            f"/core-fast/api/v1/batches/{self.batch_id}",
            json=inline_mock_batch_response,
        )

        b = self.sdk.add_jobs(self.batch_id, [])

        assert (
            mock_request.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v2/batches/{self.batch_id}/jobs"
        )
        assert isinstance(b, Batch)

    def test_add_jobs_call_raises_job_creation_error(
        self,
        mock_request_exception: requests_mock.mocker.Mocker,
        load_mock_batch_json_response: Generator[Any, Any, None],
    ):
        """
        Assert than we calling add_jobs that the correct
        HTTP request method and URL are used.

        We also confirm that when a batch is marked as closed
        we raise the correct exception. The value
        load_mock_batch_json_response provides a prefabricated data structure
        with a `open: false` value set.
        """
        mock_request_exception.register_uri(
            "POST",
            f"/core-fast/api/v1/batches/{self.batch_id}",
            json=load_mock_batch_json_response,
        )

        with pytest.raises(JobCreationError):
            _ = self.sdk.add_jobs(self.batch_id, [])

        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}"
            f"/api/v2/batches/{self.batch_id}/jobs"
        )

    def test_close_batch_raises_batch_close_error(
        self, mock_request_exception: requests_mock.mocker.Mocker
    ):
        """
        Assert that when calling close_batch, we're capable of
        encapsulating the HTTPError as a BatchClosingError instead.
        """
        mock_request_exception.register_uri(
            "PATCH",
            f"/core-fast/api/v2/batches/{self.batch_id}/complete",
            status_code=500,
        )
        with pytest.raises(BatchClosingError):
            _ = self.sdk.close_batch(self.batch_id)

        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}"
            f"/api/v2/batches/{self.batch_id}/complete"
        )

    def test_rebatch_raises_value_error_on_invalid_filters(self):
        """
        As a user using the SDK with proper credentials,
        if I pass a dictionary instead of RebatchFilters, a ValueError should be raised.
        """
        with pytest.raises(
            TypeError, match="Filters needs to be a RebatchFilters instance"
        ):
            _ = self.sdk.rebatch(id=UUID(int=0x1), filters={"min_runs": 10})

    @pytest.mark.parametrize(
        "filters",
        [
            # No filters provided
            None,
            # Empty object
            BatchFilters(),
            # Single UUID for id
            BatchFilters(id=UUID(int=0x1)),
            # List of UUIDs for id
            BatchFilters(id=[UUID(int=0x1), UUID(int=0x2)]),
            # Single string UUID for id
            BatchFilters(id=str(UUID(int=0x1))),
            # List of string UUIDs for id
            BatchFilters(id=[str(UUID(int=0x1)), str(UUID(int=0x2))]),
            # Single UUID for project_id
            BatchFilters(project_id=UUID(int=0x1)),
            # List of UUIDs for project_id
            BatchFilters(project_id=[UUID(int=0x1), UUID(int=0x2)]),
            # Single string UUID for project_id
            BatchFilters(project_id=str(UUID(int=0x1))),
            # List of string UUIDs for project_id
            BatchFilters(project_id=[str(UUID(int=0x1)), str(UUID(int=0x2))]),
            # Single user_id as string
            BatchFilters(user_id="1"),
            # List of user_ids as strings
            BatchFilters(user_id=["1", "2"]),
            # Single UUID for batch_id
            BatchFilters(id=UUID(int=0x2)),
            # Single status
            BatchFilters(status=BatchStatus.DONE),
            # List of statuses
            BatchFilters(status=[BatchStatus.DONE, BatchStatus.PENDING]),
            # Open flag
            BatchFilters(open=False),
            # Start date
            BatchFilters(start_date=datetime(2023, 1, 1)),
            # End date
            BatchFilters(end_date=datetime(2023, 1, 1)),
            # Tag
            BatchFilters(tag="custom_tag_1"),
            # Combined
            BatchFilters(
                id=[UUID(int=0x1), str(UUID(int=0x2))],
                project_id=[UUID(int=0x1), UUID(int=0x2)],
                user_id=["1", "2"],
                status=BatchStatus.DONE,
                open=False,
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 1),
            ),
        ],
    )
    def test_get_batches_with_filters_success(
        self,
        mock_request: Any,
        filters: Union[BatchFilters, None],
    ):
        """
        As a user using the SDK with proper credentials,
        I can get a list of jobs with specific filters.
        The resulting request will retrieve the jobs that match the filters.
        """
        response = self.sdk.get_batches(filters=filters)
        assert isinstance(response, PaginatedResponse)
        assert isinstance(response.total, int)
        assert isinstance(response.results, List)
        for item in response.results:
            assert isinstance(item, Batch)
        assert mock_request.last_request.method == "GET"
        # Convert filters to the appropriate format for query parameters
        query_params = build_query_params(
            filters.model_dump(exclude_unset=True) if filters is not None else None,
            PaginationParams().model_dump(),
        )
        # Check that the correct url was requested with query params
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches{query_params}"
        )

    @pytest.mark.parametrize(
        "pagination",
        [
            None,
            PaginationParams(),
            PaginationParams(limit=1),
            PaginationParams(offset=50, limit=1),
            PaginationParams(offset=100, limit=100),
            PaginationParams(offset=1000, limit=100),
        ],
    )
    def test_get_batches_with_pagination_success(
        self, mock_request: Any, pagination: PaginationParams
    ):
        """
        As a user using the SDK with proper credentials,
        I can get a list of jobs with pagination parameters.
        The resulting request will retrieve the jobs that match
        the pagination parameters.
        """
        response = self.sdk.get_batches(pagination_params=pagination)
        assert isinstance(response, PaginatedResponse)
        assert isinstance(response.total, int)
        assert isinstance(response.results, List)
        for item in response.results:
            assert isinstance(item, Batch)
        assert mock_request.last_request.method == "GET"
        # Convert filters to the appropriate format for query parameters
        query_params = build_query_params(
            pagination_params=(
                pagination.model_dump()
                if pagination
                else PaginationParams().model_dump()
            )
        )
        # Check that the correct url was requested with query params
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches{query_params}"
        )

    def test_get_batches_sdk_error(
        self, mock_request_exception: Generator[Any, Any, None]
    ):
        """
        As a user using the SDK with proper credentials,
        if my request for getting jobs returns a status code different from 200,
        I am faced with the JobFetchingError.
        """
        with pytest.raises(BatchFetchingError):
            _ = self.sdk.get_batches()
        assert mock_request_exception.last_request.method == "GET"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches?offset=0&limit=100"
        )

    def test_get_batches_raises_value_error_on_invalid_filters(self):
        """
        As a user using the SDK with proper credentials,
        if I pass a dictionary instead of BatchFilters, a ValueError should be raised.
        """
        with pytest.raises(
            TypeError, match="Filters needs to be a BatchFilters instance"
        ):
            _ = self.sdk.get_batches(filters={"open": True})

    def test_get_batches_raises_value_error_on_invalid_pagination_params(self):
        """
        As a user using the SDK with proper credentials,
        if I pass a dictionary instead of PaginationParams, a ValueError should
        be raised.
        """
        with pytest.raises(
            TypeError,
            match="Pagination parameters needs to be a PaginationParams instance",
        ):
            _ = self.sdk.get_batches(pagination_params={"offset": 100, "limit": 100})

    def test_get_batches_raises_value_error_on_invalid_value_for_offset(self):
        """
        As a user using the SDK with proper credentials,
        if I pass a 'from_index' inferior to 0, it raises a ValueError to the user.
        """
        with pytest.raises(
            ValueError, match="Input should be greater than or equal to 0"
        ):
            _ = self.sdk.get_batches(pagination_params=PaginationParams(offset=-1))

    @pytest.mark.parametrize(
        "limit",
        [-1, 0, 101],
    )
    def test_get_batches_raises_value_error_on_invalid_value_for_limit(
        self, limit: int
    ):
        """
        As a user using the SDK with proper credentials,
        if I pass a 'limit' inferior to 1 or superior to 100,
        it raises a ValueError to the user.
        """
        with pytest.raises(ValueError, match="limit"):
            _ = self.sdk.get_batches(pagination_params=PaginationParams(limit=limit))

    @pytest.mark.parametrize(
        "batch_ids",
        [
            # No batch id provided
            [],
            # Single string UUID for id
            [str(UUID(int=0x1))],
            # List of string UUIDs for id
            [str(UUID(int=0x1)), str(UUID(int=0x2))],
        ],
    )
    def test_cancel_batches_success(
        self,
        mock_request: Any,
        batch_ids: Any,
    ):
        """
        As a user using the SDK with proper credentials,
        I can cancel of a group of batches from a batch with specific batch ids.
        The resulting request will retrieve the batches that were cancelled and
        the errors for those that could not be cancelled.
        """
        response = self.sdk.cancel_batches(batch_ids=batch_ids)
        assert isinstance(response, BatchCancellationResponse)

        for item in response.batches:
            assert isinstance(item, Batch)

        assert isinstance(response.errors, Dict)

        assert mock_request.last_request.method == "PATCH"

        # Check that the correct url was requested with query params
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches/cancel"
        )

        assert mock_request.last_request.json() == {"batch_ids": batch_ids}

    def test_sequence_builder_field_is_accessible(
        self,
        mock_request: Any,
    ):
        """Test verifying that the sequence_builder property of a job
        is accessible when we need to get it.

        The get_batches endpoint doesn't return the sequence_builder of jobs,
        but when accessing the attribute, it automatically triggers
        a get_batch call to retrieve the sequence_builder from the APIs.
        """
        response = self.sdk.get_batches()
        first_batch = response.results[0]
        assert mock_request.last_request.method == "GET"
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches?offset=0&limit=100"
        )
        assert first_batch.sequence_builder == self.pulser_sequence
        assert mock_request.last_request.method == "GET"
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v2/batches/{first_batch.id}"
        )

    @pytest.mark.parametrize(
        ("exception", "expected_exception"),
        [
            (requests.Timeout, requests.Timeout),
            (
                requests.HTTPError(
                    "500 Server Error", response=mock_500_http_error_response()
                ),
                BatchFetchingError,
            ),
            (requests.ConnectionError("Connection refused"), requests.ConnectionError),
        ],
        ids=["timeout", "http_500", "connection_error"],
    )
    def test_create_and_get_batch_retries_on_transient_errors(
        self,
        mock_request,
        exception,
        expected_exception,
    ):
        """Test that GET batch call retries on transient errors
        after we create a batch."""
        mock_request.reset_mock()

        # Register the URI with the appropriate exception
        mock_request.register_uri(
            "GET",
            f"https://apis.pasqal.cloud/core-fast/api/v2/batches/{self.batch_id}",
            exc=exception,
        )

        with contextlib.suppress(expected_exception):
            self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
                jobs=[self.simple_job_args],
                device_type=DeviceTypeName.EMU_MPS,
                wait=True,
            )

        # Assertions to verify retry behavior
        # There is one call to create the batch, then 6 calls
        # to get the batch, 5 of which are retries
        assert mock_request.call_count == 7
        assert mock_request.last_request.method == "GET"
        assert (
            mock_request.last_request.path
            == f"/core-fast/api/v2/batches/{self.batch_id}"
        )
        assert mock_request.last_request.matcher.call_count == 6

    @pytest.mark.parametrize(
        ("exception", "expected_exception"),
        [
            (requests.Timeout, requests.Timeout),
            (
                requests.HTTPError(
                    "500 Server Error", response=mock_500_http_error_response()
                ),
                BatchFetchingError,
            ),
            (requests.ConnectionError("Connection refused"), requests.ConnectionError),
        ],
        ids=["timeout", "http_500", "connection_error"],
    )
    def test_add_and_get_jobs_retries_on_transient_errors(
        self,
        mock_request,
        exception,
        expected_exception,
    ):
        """Test that GET batch call retries on transient errors
        after we add jobs to a batch."""
        mock_request.reset_mock()

        # Register the URI with the appropriate exception
        mock_request.register_uri(
            "GET",
            f"https://apis.pasqal.cloud/core-fast/api/v2/batches/{self.batch_id}",
            exc=exception,
        )

        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[self.simple_job_args],
            device_type=DeviceTypeName.EMU_MPS,
        )

        with contextlib.suppress(expected_exception):
            batch.add_jobs(jobs=[self.simple_job_args], wait=True)

        # Assertions to verify retry behavior
        # There is one call to create the batch, one call to add a job,
        # then 6 calls to add the job, 5 of which are retries
        assert mock_request.call_count == 8
        assert mock_request.last_request.method == "GET"
        assert (
            mock_request.last_request.path
            == f"/core-fast/api/v2/batches/{self.batch_id}"
        )
        assert mock_request.last_request.matcher.call_count == 6

    @pytest.mark.parametrize(
        ("exception", "expected_exception"),
        [
            (requests.Timeout, requests.Timeout),
            (
                requests.HTTPError(
                    "500 Server Error", response=mock_500_http_error_response()
                ),
                BatchFetchingError,
            ),
            (requests.ConnectionError("Connection refused"), requests.ConnectionError),
        ],
        ids=["timeout", "http_500", "connection_error"],
    )
    def test_get_batch_retries_on_transient_errors(
        self,
        mock_request,
        exception,
        expected_exception,
    ):
        """Test that GET batch call retries on transient errors"""
        mock_request.reset_mock()

        # Register the URI with the appropriate exception
        mock_request.register_uri(
            "GET",
            f"https://apis.pasqal.cloud/core-fast/api/v2/batches/{self.batch_id}",
            exc=exception,
        )

        with contextlib.suppress(expected_exception):
            self.sdk.get_batch(self.batch_id)

        # Assertions to verify retry behavior
        # there are 6 calls to get the batch, 5 of which are retries
        assert mock_request.call_count == 6
        assert mock_request.last_request.method == "GET"
        assert (
            mock_request.last_request.path
            == f"/core-fast/api/v2/batches/{self.batch_id}"
        )
        assert mock_request.last_request.matcher.call_count == 6

    def test_set_tags_by_using_batch_method_success(
        self,
        mock_request: requests_mock.mocker.Mocker,
    ):
        mock_request.reset_mock()

        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[self.simple_job_args],
            device_type=DeviceTypeName.EMU_MPS,
        )
        batch.set_tags(self.tags)
        assert batch.tags == self.tags
        assert mock_request.last_request.method == "PATCH"
        assert (
            mock_request.last_request.path
            == f"/core-fast/api/v1/batches/{self.batch_id}/tags"
        )
        # One call to create the batch, one to set the tags
        assert mock_request.last_request.matcher.call_count == 2

    def test_set_tags_by_using_client_method_success(
        self,
        mock_request: requests_mock.mocker.Mocker,
    ):
        mock_request.reset_mock()

        batch = self.sdk.set_batch_tags(self.batch_id, self.tags)
        assert batch.tags == self.tags
        assert mock_request.last_request.method == "PATCH"
        assert (
            mock_request.last_request.path
            == f"/core-fast/api/v1/batches/{self.batch_id}/tags"
        )
        assert mock_request.last_request.matcher.call_count == 1
