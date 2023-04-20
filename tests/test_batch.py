from unittest.mock import patch
from uuid import uuid4

import pytest
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess

from pasqal_cloud import SDK
from pasqal_cloud.device import BaseConfig, EmuFreeConfig, EmulatorType, EmuTNConfig


class TestBatch:
    @pytest.fixture(autouse=True)
    @patch("sdk.client.Auth0TokenProvider", FakeAuth0AuthenticationSuccess)
    def init_sdk(self, start_mock_request):
        self.sdk = SDK(
            username="me@test.com", password="password", group_id=str(uuid4())
        )
        self.pulser_sequence = "pulser_test_sequence"
        self.batch_id = "00000000-0000-0000-0000-000000000001"
        self.job_result = {"1001": 12, "0110": 35, "1111": 1}
        self.n_job_runs = 50
        self.job_id = "00000000-0000-0000-0000-000000022010"
        self.job_variables = {"Omega_max": 14.4, "last_target": "q1", "ts": [200, 500]}

    @pytest.mark.parametrize("emulator", [None] + [e.value for e in EmulatorType])
    def test_create_batch(self, emulator):
        job = {"runs": self.n_job_runs, "variables": self.job_variables}
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[job],
            emulator=emulator,
        )
        assert batch.id == self.batch_id
        assert batch.sequence_builder == self.pulser_sequence
        # TODO: Remove after IROISE MVP
        assert batch.complete
        assert batch.jobs[self.job_id].batch_id == batch.id
        assert batch.jobs[self.job_id].runs == self.n_job_runs

    def test_create_batch_and_wait(self, request_mock):
        job = {"runs": self.n_job_runs, "variables": self.job_variables}
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence, jobs=[job], wait=True
        )
        assert (
            batch.id == "00000000-0000-0000-0000-000000000001"
        )  # the batch_id used in the mock data
        assert batch.sequence_builder == self.pulser_sequence
        assert batch.complete
        assert batch.jobs
        for job_id, job in batch.jobs.items():
            assert self.job_id == job_id
            assert job.result is None
        assert request_mock.last_request.method == "GET"

    def test_create_batch_and_fetch_results(self, request_mock):
        job = {"runs": self.n_job_runs, "variables": self.job_variables}
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[job],
            wait=True,
            fetch_results=True,
        )
        assert (
            batch.id == "00000000-0000-0000-0000-000000000001"
        )  # the batch_id used in the mock data
        assert batch.sequence_builder == self.pulser_sequence
        assert batch.complete
        assert batch.jobs
        for job_id, job in batch.jobs.items():
            assert self.job_id == job_id
            assert job.result == self.job_result
        assert request_mock.last_request.method == "GET"

    @pytest.mark.skip(reason="Not enabled during Iroise MVP")
    def test_batch_add_job(self, request_mock):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
        )
        job = batch.add_job(
            runs=self.n_job_runs,
            variables=self.job_variables,
        )
        assert request_mock.last_request.json()["batch_id"] == batch.id
        assert job.batch_id == batch.id
        assert job.runs == self.n_job_runs

    @pytest.mark.skip(reason="Not enabled during Iroise MVP")
    def test_batch_add_job_and_wait_for_results(self, request_mock):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
        )
        job = batch.add_job(
            runs=self.n_job_runs,
            variables={"Omega_max": 14.4, "last_target": "q1", "ts": [200, 500]},
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

    @pytest.mark.skip(reason="Not enabled during Iroise MVP")
    def test_batch_declare_complete(self):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
        )
        rsp = batch.declare_complete(wait=False)
        assert rsp["complete"]
        assert len(batch.jobs) == 0

    @pytest.mark.skip(reason="Not enabled during Iroise MVP")
    def test_batch_declare_complete_and_wait_for_results(self, request_mock):
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
        )
        rsp = batch.declare_complete(wait=True)
        assert rsp["complete"]
        assert request_mock.last_request.method == "GET"
        assert (
            request_mock.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v1/jobs/{self.job_id}"
        )
        assert batch.jobs[self.job_id].batch_id == batch.id
        assert batch.jobs[self.job_id].result == self.job_result

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
        job = {"runs": self.n_job_runs, "variables": self.job_variables}
        batch = self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
            jobs=[job],
            emulator=emulator,
            configuration=configuration,
        )
        assert batch.configuration == expected
