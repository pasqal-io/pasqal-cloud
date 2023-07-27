from unittest.mock import patch
from uuid import uuid4

import pytest

from pasqal_cloud import Batch, Job, SDK
from pasqal_cloud.device import BaseConfig, EmuFreeConfig, EmulatorType, EmuTNConfig
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess


class TestBatch:
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
    def test_create_batch(self, emulator):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[self.simple_job_args],
            emulator=emulator,
        )
        assert batch.id == self.batch_id
        assert batch.sequence_builder == self.pulser_sequence
        assert batch.complete
        assert batch.ordered_jobs[0].batch_id == batch.id

    @pytest.mark.filterwarnings(
        "ignore:Argument `fetch_results` is deprecated and will be removed "
        "in a future version. Please use argument `wait` instead"
    )
    @pytest.mark.parametrize("wait,fetch_results", [(True, False), (False, True)])
    def test_create_batch_and_wait(self, request_mock, wait, fetch_results):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[self.simple_job_args, self.simple_job_args],
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
        assert request_mock.last_request.method == "GET"

    def test_get_batch(self, batch):
        batch_requested = self.sdk.get_batch(batch.id)
        assert batch_requested.id == self.batch_id

    def test_batch_add_job(self, request_mock):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence, jobs=[self.simple_job_args]
        )
        job = batch.add_job(
            runs=self.n_job_runs,
            variables=self.job_variables,
        )
        assert request_mock.last_request.json()["batch_id"] == batch.id
        assert job.batch_id == batch.id
        assert job.runs == self.n_job_runs
        assert len(batch.ordered_jobs) == 2
        # Ticket (#704)
        with pytest.warns(
            DeprecationWarning,
            match="'jobs' attribute is deprecated, use 'ordered_jobs' instead",
        ):
            assert len(batch.jobs) == 2

    def test_batch_add_job_and_wait_for_results(self, request_mock):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence, jobs=[self.simple_job_args]
        )
        job = batch.add_job(
            runs=self.n_job_runs,
            variables={
                "Omega_max": 14.4,
                "last_target": "q1",
                "ts": [200, 500],
            },
            wait=True,
        )
        assert job.batch_id == batch.id
        assert job.runs == self.n_job_runs
        assert request_mock.last_request.method == "GET"
        assert (
            request_mock.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/jobs/{self.job_id}"
        )
        assert job.result == self.job_result
        assert job.full_result == self.job_full_result

    def test_batch_declare_complete(self):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence, jobs=[self.simple_job_args]
        )
        rsp = batch.declare_complete(wait=False)
        assert rsp["complete"]

    def test_batch_declare_complete_and_wait_for_results(self, request_mock):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[self.simple_job_args, self.simple_job_args],
        )
        rsp = batch.declare_complete(wait=True)
        assert rsp["complete"]
        assert request_mock.last_request.method == "GET"
        assert (
            request_mock.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/batches/{self.batch_id}"
        )
        assert batch.ordered_jobs[0].batch_id == batch.id
        assert batch.ordered_jobs[0].result == self.job_result
        assert batch.ordered_jobs[0].full_result == self.job_full_result
        assert len(batch.ordered_jobs) == 2
        # Ticket (#704)
        with pytest.warns(
            DeprecationWarning,
            match="'jobs' attribute is deprecated, use 'ordered_jobs' instead",
        ):
            assert len(batch.jobs) == 2

    def test_cancel_batch_self(self, request_mock, batch):
        batch.cancel()
        assert batch.status == "CANCELED"
        assert request_mock.last_request.method == "PUT"
        assert (
            request_mock.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/batches/{self.batch_id}/cancel"
        )

    def test_cancel_batch_sdk(self, request_mock):
        client_rsp = self.sdk.cancel_batch(self.batch_id)
        assert type(client_rsp) == Batch
        assert client_rsp.status == "CANCELED"
        assert request_mock.last_request.method == "PUT"
        assert (
            request_mock.last_request.url == f"{self.sdk._client.endpoints.core}"
            f"/api/v1/batches/{self.batch_id}/cancel"
        )

    def test_get_job(self, job):
        job_requested = self.sdk.get_job(job.id)
        print(self.sdk)
        assert job_requested.id == job.id

    def test_cancel_job_self(self, request_mock, job):
        job.cancel()
        assert job.status == "CANCELED"
        assert request_mock.last_request.method == "PUT"
        assert (
            request_mock.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/jobs/{self.job_id}/cancel"
        )

    def test_cancel_job_sdk(self, request_mock):
        client_rsp = self.sdk.cancel_job(self.job_id)
        assert type(client_rsp) == Job
        assert client_rsp.status == "CANCELED"
        assert request_mock.last_request.method == "PUT"
        assert (
            request_mock.last_request.url
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

    def test_create_batch_fetch_results_deprecated(
        self,
    ):
        with pytest.warns(DeprecationWarning):
            self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
                jobs=[self.simple_job_args],
                fetch_results=True,
            )

    def test_get_batch_fetch_results_deprecated(
        self,
    ):
        with pytest.warns(DeprecationWarning):
            self.sdk.get_batch(self.batch_id, fetch_results=True)
