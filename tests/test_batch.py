from collections import OrderedDict
import json
import re
from datetime import datetime
from typing import Any, Dict
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from pasqal_cloud import Batch, Job, SDK
from pasqal_cloud.device import BaseConfig, EmuFreeConfig, EmulatorType, EmuTNConfig
from pasqal_cloud.errors import (
    BatchCancellingError,
    BatchCreationError,
    BatchSetCompleteError,
    JobCancellingError,
    JobCreationError,
    JobFetchingError,
    JobRetryError,
    RebatchError,
)
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess
from tests.conftest import mock_core_response


class TestBatch:
    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """Fixture to mock sleep to make tests faster."""
        with patch("time.sleep"):
            yield

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
    def test_create_batch(self, emulator, mock_request):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[self.simple_job_args],
            emulator=emulator,
        )
        assert batch.id == self.batch_id
        assert batch.sequence_builder == self.pulser_sequence
        assert batch.complete
        assert batch.ordered_jobs[0].batch_id == batch.id
        assert mock_request.last_request.method == "POST"

    @pytest.mark.usefixtures("mock_request_exception_batch_creation")
    def test_create_batch_failure(self, batch_creation_error_data):
        dat = batch_creation_error_data
        with pytest.raises(
            BatchCreationError,
            match=(
                re.escape(
                    f"Batch creation failed: {dat['code']}: "
                    f"{dat['data']['description']}\n"
                    f"Details: {json.dumps(dat, indent=2)}"
                )
            ),
        ):
            _ = self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
                jobs=[self.simple_job_args],
            )

    @pytest.mark.filterwarnings(
        "ignore:Argument `fetch_results` is deprecated and will be removed "
        "in a future version. Please use argument `wait` instead"
    )
    @pytest.mark.parametrize("wait,fetch_results", [(True, False), (False, True)])
    def test_create_batch_and_wait(self, mock_request, wait, fetch_results):
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
    def test_get_batch(self, batch):
        batch_requested = self.sdk.get_batch(batch.id)
        assert batch_requested.id == self.batch_id

    def test_batch_add_jobs(self, mock_request):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence, jobs=[self.simple_job_args]
        )
        batch.add_jobs([{"runs": self.n_job_runs, "variables": self.job_variables}])
        assert batch.id in mock_request.last_request.url
        assert len(batch.ordered_jobs) == 2

    def test_batch_add_jobs_failure(self, batch, mock_request_exception):
        with pytest.raises(JobCreationError):
            _ = batch.add_jobs(
                [{"runs": self.n_job_runs, "variables": self.job_variables}]
            )
        assert mock_request_exception.last_request.method == "POST"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches/{batch.id}/jobs"
        )

    def test_batch_add_jobs_and_wait_for_results(self, batch, mock_request):
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

        # Reset history so that we can count calls later
        mock_request.reset_mock()
        batch.add_jobs(
            [{"runs": self.n_job_runs}, {"runs": self.n_job_runs}],
            wait=True,
        )

        assert len(batch.ordered_jobs) == 2
        assert (
            mock_request.call_count == 5
        )  # 1 call to add jobs and 4 get batch calls until jobs are DONE
        assert (
            mock_request.request_history[0].url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches/{batch.id}/jobs"
        )
        assert mock_request.request_history[0].method == "POST"
        assert all(
            [
                (req.method, req.url)
                == (
                    "GET",
                    f"{self.sdk._client.endpoints.core}/api/v1/batches/{batch.id}",
                )
                for req in mock_request.request_history[1:]
            ]
        )
        assert all([job.result == self.job_result for job in batch.ordered_jobs])
        assert all(
            [job.full_result == self.job_full_result for job in batch.ordered_jobs]
        )

    @pytest.mark.usefixtures("mock_request")
    def test_batch_declare_complete(self, batch):
        batch.declare_complete(wait=False)
        assert batch.complete

    def test_batch_declare_complete_failure(self, batch, mock_request_exception):
        with pytest.raises(BatchSetCompleteError):
            _ = batch.declare_complete(wait=False)

        assert batch.status == "PENDING"
        mock_request_exception.stop()

    def test_batch_declare_complete_and_wait_for_results(self, batch, mock_request):
        batch.declare_complete(wait=True)
        assert batch.complete
        assert mock_request.last_request.method == "GET"
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches/{self.batch_id}"
        )
        assert batch.ordered_jobs[0].batch_id == batch.id
        assert batch.ordered_jobs[0].result == self.job_result
        assert batch.ordered_jobs[0].full_result == self.job_full_result
        assert len(batch.ordered_jobs) == 1

    def test_cancel_batch_self(self, mock_request, batch):
        batch.cancel()
        assert batch.status == "CANCELED"
        assert mock_request.last_request.method == "PUT"
        assert (
            mock_request.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/batches/{self.batch_id}/cancel"
        )

    def test_cancel_batch_self_error(self, mock_request_exception, batch):
        with pytest.raises(BatchCancellingError):
            batch.cancel()
        assert batch.status == "PENDING"
        assert mock_request_exception.last_request.method == "PUT"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/batches/{self.batch_id}/cancel"
        )

    def test_cancel_batch_sdk(self, mock_request):
        client_rsp = self.sdk.cancel_batch(self.batch_id)
        assert type(client_rsp) == Batch
        assert client_rsp.status == "CANCELED"
        assert mock_request.last_request.method == "PUT"
        assert (
            mock_request.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/batches/{self.batch_id}/cancel"
        )

    def test_cancel_batch_sdk_error(self, mock_request_exception):
        with pytest.raises(BatchCancellingError):
            _ = self.sdk.cancel_batch(self.batch_id)

        assert mock_request_exception.last_request.method == "PUT"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/batches/{self.batch_id}/cancel"
        )

    @pytest.mark.usefixtures("mock_request")
    def test_get_job(self, job):
        job_requested = self.sdk.get_job(job.id)
        print(self.sdk)
        assert job_requested.id == job.id

    def test_get_job_error(self, job, mock_request_exception):
        with pytest.raises(JobFetchingError):
            _ = self.sdk.get_job(job.id)
        assert mock_request_exception.last_request.method == "GET"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/jobs/{job.id}"
        )

    def test_cancel_job_self(self, mock_request, job):
        job.cancel()
        assert job.status == "CANCELED"
        assert mock_request.last_request.method == "PUT"
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/jobs/{self.job_id}/cancel"
        )

    def test_cancel_job_self_error(self, mock_request_exception, job):
        with pytest.raises(JobCancellingError):
            job.cancel()
        assert job.status == "PENDING"
        assert mock_request_exception.last_request.method == "PUT"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/jobs/{self.job_id}/cancel"
        )

    def test_cancel_job_sdk(self, mock_request):
        client_rsp = self.sdk.cancel_job(self.job_id)
        assert type(client_rsp) == Job
        assert client_rsp.status == "CANCELED"
        assert mock_request.last_request.method == "PUT"
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/jobs/{self.job_id}/cancel"
        )

    def test_cancel_job_sdk_error(self, mock_request_exception, job):
        with pytest.raises(JobCancellingError):
            _ = self.sdk.cancel_job(self.job_id)
        assert mock_request_exception.last_request.method == "PUT"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/jobs/{self.job_id}/cancel"
        )

    @pytest.mark.parametrize(
        "emulator, configuration, expected",
        [
            (EmulatorType.EMU_TN, EmuTNConfig(), EmuTNConfig()),
            (None, None, None),
            (
                EmulatorType.EMU_FREE,
                EmuFreeConfig(),
                EmuFreeConfig(extra_config={"dt": 10.0, "precision": "normal"}),
            ),
            (
                "SomethingElse",
                BaseConfig(),
                BaseConfig(extra_config={"dt": 10.0, "precision": "normal"}),
            ),
        ],
    )
    @pytest.mark.usefixtures("mock_request")
    def test_create_batch_configuration(self, emulator, configuration, expected):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[self.simple_job_args],
            emulator=emulator,
            configuration=configuration,
        )
        assert batch.configuration == expected

    def test_batch_instantiation_with_extra_field(self, batch):
        """Instantiating a batch with an extra field should not raise an error.

        This enables us to add new fields in the API response on the batches endpoint
        without breaking compatibility for users with old versions of the SDK where
        the field is not present in the Batch class.
        """
        batch_dict = batch.dict()  # Batch data expected by the SDK
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
        with pytest.warns(DeprecationWarning):
            self.sdk.get_batch(self.batch_id, fetch_results=True)

    @pytest.mark.parametrize(
        "filters",
        (
            {"job_ids": [str(UUID(int=0x1))]},
            {"start_date": datetime(2023, 1, 1)},
            {"end_date": datetime(2023, 1, 1)},
            {"status": "DONE"},
            {"status": ["DONE", "PENDING"]},
            {"min_runs": 10},
            {"max_runs": 10},
            OrderedDict(
                job_ids=[str(UUID(int=0x1))],
                status=["DONE", "PENDING"],
                min_runs=10,
                max_runs=10,
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 1),
            ),
        ),
    )
    def test_rebatch_success(
        self,
        mock_request,
        filters: Dict[str, Any],
    ):
        """
        As a user using the SDK with proper credentials,
        I can rebatch an existing batch with specific filters.
        The resulting request will create a new batch which includes
        copies of the jobs that match the filters.
        """
        batch = self.sdk.rebatch(self.batch_id, **filters)
        assert mock_request.last_request.method == "POST"

        if ids := filters.pop("job_ids", None):
            filters["id"] = ids
            # Move id to beginning to construct query param string like the sdk does.
            if isinstance(filters, OrderedDict):
                filters.move_to_end("id", last=False)

        # Constructing the query param string
        query_params = "?"
        for filter, value in filters.items():
            if isinstance(value, list):
                for val in value:
                    query_params += f"{filter}={val}&"
            else:
                if isinstance(value, datetime):
                    value = value.isoformat()
                query_params += f"{filter}={value}&"
        # Replace : by %3A for datetimes
        query_params = query_params.replace(":", "%3A")[:-1]

        # Check that correct url was requested with query params
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches/"
            + f"{self.batch_id}/rebatch{query_params}"
        )
        assert batch.parent_id == self.batch_id
        assert batch.ordered_jobs[0].parent_id

    def test_rebatch_sdk_error(self, mock_request_exception):
        """
        As a user using the SDK with proper credentials,
        if my request for rebatching returns a non 200 status code,
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
        mock_request,
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
            == f"{self.sdk._client.endpoints.core}/api/v1/batches/"
            + f"{self.batch_id}/jobs"
        )

    def test_retry_sdk_error(
        self,
        batch: Batch,
        job: Job,
        mock_request_exception,
    ):
        """
        As a user using the SDK with proper credentials,
        if my request for retrying a job returns a non 200 status code,
        I am faced with the JobRetryError exception.
        """
        batch.ordered_jobs = [job]
        with pytest.raises(JobRetryError):
            batch.retry(job)

        assert len(batch.ordered_jobs) == 1
        assert mock_request_exception.last_request.method == "POST"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches/"
            + f"{self.batch_id}/jobs"
        )
