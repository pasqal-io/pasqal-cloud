from unittest.mock import Mock, MagicMock, patch

import pytest

from sdk import SDK
from sdk.batch import Batch


class TestBatch:
    @pytest.fixture(autouse=True)
    @patch("sdk.Client")
    def init_sdk(self, mock_client):
        self.sdk = SDK()
        self.pulser_sequence = "pulser_test_sequence"

    @patch("sdk.Batch")
    def test_create_batch(self, mock_batch):
        self.sdk.create_batch(
            serialized_sequence=self.pulser_sequence,
        )
        self.sdk._client._send_batch.assert_called_once()

    @patch("sdk.batch.Client")
    def test_batch_add_job(self, mock_client):
        batch_id = 2
        mock_client._send_job.return_value = {
            "runs": 1,
            "batch_id": batch_id,
            "id": 1,
            "status": "",
            "created_at": "",
            "updated_at": "",
            "errors": [],
        }
        self.batch = Batch(
            complete=False,
            created_at="",
            updated_at="",
            device_type="",
            group_id=1,
            id=batch_id,
            user_id=1,
            priority=1,
            status="",
            webhook="",
            _client=mock_client,
            sequence_builder=self.pulser_sequence,
        )
        job = self.batch.add_job(runs=50, variables={"var": 2})
        self.batch._client._send_job.assert_called_once()
        assert job.batch_id == batch_id

    @patch("sdk.batch.Job")
    @patch("sdk.batch.Client")
    def test_batch_declare_complete(self, mock_job, mock_client):
        self.batch = Batch(
            complete=False,
            created_at="",
            updated_at="",
            device_type="",
            group_id=1,
            id=1,
            user_id=1,
            priority=1,
            status="",
            webhook="",
            _client=mock_client,
            sequence_builder=self.pulser_sequence,
        )
        self.batch.declare_complete(wait=True)
        self.batch._client._complete_batch.assert_called_once()
