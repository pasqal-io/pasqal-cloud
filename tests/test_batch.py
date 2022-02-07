from unittest.mock import Mock, MagicMock, patch

import json
import os
import pytest
import requests_mock

from sdk import SDK
from sdk.batch import Batch


TEST_API_FIXTURES_PATH = "tests/fixtures/api"
JSON_FILE = "_.{}.json"


class TestBatch:
    @pytest.fixture(autouse=True)
    @requests_mock.Mocker(kw="mock")
    def init_sdk(self, **kwargs):
        def mock_response(request, context):
            path = request.url.split("/api/v1/")[1].split("?")[0]
            json_path = os.path.join(
                TEST_API_FIXTURES_PATH, path, JSON_FILE.format(request.method)
            )
            with open(json_path) as json_file:
                return json.load(json_file)

        # Configure requests to use the local JSON files a response
        kwargs["mock"].register_uri(
            requests_mock.ANY, requests_mock.ANY, json=mock_response
        )
        self.requests_mock = kwargs["mock"]
        self.sdk = SDK(client_id="my_client_id", client_secret="my_client_secret")
        self.pulser_sequence = "pulser_test_sequence"
        self.batch_id = 1
        self.job_result = "result"
        self.n_job_runs = 50

    def test_create_batch(self):
        with self.requests_mock:
            batch = self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
            )
            assert batch.id == self.batch_id
            assert batch.sequence_builder == self.pulser_sequence

    def test_batch_add_job(self):
        with self.requests_mock:
            batch = self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
            )
            job = batch.add_job(
                runs=self.n_job_runs,
                variables={"Omega_max": 14.4, "last_target": "q1", "ts": [200, 500]},
            )
            assert job.batch_id == self.batch_id
            assert job.runs == self.n_job_runs

    def test_batch_add_job_and_wait_for_results(self):
        with self.requests_mock:
            batch = self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
            )
            job = batch.add_job(
                runs=self.n_job_runs,
                variables={"Omega_max": 14.4, "last_target": "q1", "ts": [200, 500]},
                wait=True,
            )
            assert job.batch_id == self.batch_id
            assert job.runs == self.n_job_runs
            assert job.result == self.job_result

    def test_batch_declare_complete(self):
        with self.requests_mock:
            batch = self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
            )
            rsp = batch.declare_complete(wait=False)
            assert rsp["complete"]
            assert len(batch.jobs) == 0

    def test_batch_declare_complete_and_wait_for_results(self):
        job_id = 22010
        with self.requests_mock:
            batch = self.sdk.create_batch(
                serialized_sequence=self.pulser_sequence,
            )
            rsp = batch.declare_complete(wait=True)
            assert rsp["complete"]
            assert batch.jobs[job_id].batch_id == self.batch_id
            assert batch.jobs[job_id].result == self.job_result
