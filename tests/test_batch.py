import json
from datetime import datetime
from typing import Any, Dict, Generator, Optional, Union
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
import requests_mock

from pasqal_cloud import Batch, Job, RebatchFilters, SDK
from pasqal_cloud.batch import Batch as BatchModel
from pasqal_cloud.device import BaseConfig, EmuFreeConfig, EmulatorType, EmuTNConfig
from pasqal_cloud.errors import (
    BatchCancellingError,
    BatchClosingError,
    BatchCreationError,
    JobCreationError,
    JobRetryError,
    OnlyCompleteOrOpenCanBeSet,
    RebatchError,
)
from pasqal_cloud.utils.constants import JobStatus
from tests.conftest import mock_core_response
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess
from tests.utils import build_query_params


class TestBatch:
    @pytest.fixture()
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

    @pytest.mark.parametrize("emulator", [None] + [e.value for e in EmulatorType])
    def test_create_batch(
        self, emulator: Optional[str], mock_request: requests_mock.mocker.Mocker
    ):
        """
        When successfully creating a batch, we should be able to assert
        certain fields and values are in the assigned return object.
        """
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[self.simple_job_args],
            emulator=emulator,
        )
        assert batch.id == self.batch_id
        assert batch.sequence_builder == self.pulser_sequence
        assert not batch.open
        assert batch.complete
        assert batch.ordered_jobs[0].batch_id == batch.id
        assert mock_request.last_request.method == "POST"

    @pytest.mark.parametrize("emulator", [None] + [e.value for e in EmulatorType])
    def test_create_batch_with_complete_raises_warning(
        self, emulator: Optional[str], mock_request: requests_mock.mocker.Mocker
    ):
        """
        Test that using complete at batch definition is still accepted but will
        trigger a deprecation warning.
        """
        with pytest.warns(DeprecationWarning):
            batch = self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
                jobs=[self.simple_job_args],
                emulator=emulator,
                complete=True,
            )
        assert batch.id == self.batch_id
        assert batch.sequence_builder == self.pulser_sequence
        assert not batch.open
        assert mock_request.last_request.method == "POST"

    @pytest.mark.parametrize("emulator", [None] + [e.value for e in EmulatorType])
    def test_create_batch_open_and_complete_raises_error(self, emulator: Optional[str]):
        """
        Test that setting both complete and open values will result in the proper
        error being raised.
        """
        with pytest.raises(OnlyCompleteOrOpenCanBeSet):
            _ = self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
                jobs=[self.simple_job_args],
                emulator=emulator,
                complete=True,
                open=True,
            )

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
        assert type(client_rsp) == Batch
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
        ("emulator", "configuration", "expected"),
        [
            (EmulatorType.EMU_TN, EmuTNConfig(), EmuTNConfig()),
            (None, None, None),
            (
                EmulatorType.EMU_FREE,
                EmuFreeConfig(),
                EmuFreeConfig(extra_config={"dt": 10.0, "precision": "normal"}),
            ),
            (EmulatorType.EMU_FRESNEL, None, None),
            (
                "SomethingElse",
                BaseConfig(),
                BaseConfig(extra_config={"dt": 10.0, "precision": "normal"}),
            ),
        ],
    )
    @pytest.mark.usefixtures("mock_request")
    def test_create_batch_configuration(
        self, emulator: str, configuration: BaseConfig, expected: BaseConfig
    ):
        """
        Assert that when creating a batch with a certain confiuration,
        we create the exected object
        """
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[self.simple_job_args],
            emulator=emulator,
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
                min_runs=10,
                max_runs=10,
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
            ValueError, match="Filters needs to be a RebatchFilters instance"
        ):
            _ = self.sdk.rebatch(id=UUID(int=0x1), filters={"min_runs": 10})
