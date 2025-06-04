"""
Utilities for testing client libraries against the cloud SDK.
"""

import json
from collections import defaultdict
from typing import Any, Union
from unittest.mock import MagicMock
from uuid import uuid4

from pasqal_cloud.batch import Batch
from pasqal_cloud.device import BaseConfig, EmulatorType
from pasqal_cloud.job import CreateJob, Job
from pasqal_cloud.utils.filters import JobFilters
from pasqal_cloud.utils.responses import PaginatedResponse


class MockServer:
    """A mock server to simulate job progress and manage job states.

    This class keeps track of jobs and their progress to simulate real-world
    execution and status updates. It supports setting and retrieving jobs
    while simulating their progress through internal counters.
    """

    def __init__(self) -> None:
        """Initialize the mock server with empty job data and progress counters."""
        self.jobs: dict[str, Job] = {}
        self.jobs_progress_counter: dict[str, int] = defaultdict(int)
        # Set how many progress steps are needed before each batch is marked as done
        self.max_progress_steps = 3

    def get_job(self, id: str) -> Job:
        """Retrieve the job by ID and simulate its progress.

        Args:
            id (str): The ID of the job to retrieve.

        Returns:
            Job: The job object after simulating a progress step.
        """
        self._simulate_job_progress_step(id)
        return self.jobs[id]

    def set_job(self, job: Job) -> None:
        """Store a job in the mock server.

        Args:
            job (Job): The job to store in the server.
        """
        self.jobs[job.id] = job

    def _simulate_job_progress_step(self, id: str) -> None:
        """Update in place the job store to simulate progress.

        Check how many times this function has been called for a given
        job and updates its progress accordingly.
        On the first call, the job status is set to RUNNING.
        After self.max_progress_steps, the job status is set to DONE and
        fake results are set.

        Args:
            id (str): The ID of the job for which progress is being simulated.
        """
        progress_step = self.jobs_progress_counter[id]
        if progress_step == 0:
            self.jobs[id].status = "RUNNING"
        if progress_step >= self.max_progress_steps:
            self.jobs[id].status = "DONE"
            self.jobs[id]._full_result = {
                "counter": {"1001": 50, "1011": 25},
                "raw": [],
            }
        self.jobs_progress_counter[id] += 1


class MockSDK:
    """Helper class to mock the cloud SDK and skip the API calls.

    Warning: This implements only a small subset of the functions available
        in the cloud SDK; focusing on the functions used by qek.
        This should be extended to support all methods and moved to the
        pasqal-cloud repository so that it can be reused for all future
        libraries using the SDK.

    Intended use:
    ```py
        with patch("my_feature.SDK", return_value=MockSDK()):
            qpu_extractor = extractor(
                compiler=ptcfm_compiler,
                device_name="FRESNEL",
                project_id=placeholder,
                username=placeholder,
                password=placeholder,
            )
    ```
    """

    def __init__(self) -> None:
        self.mock_server = MockServer()

    def get_device_specs_dict(self) -> Any:
        """Retrieve the device specifications from a local JSON file."""
        with open("tests/cloud_fixtures/device_specs.json", "r") as f:
            return json.load(f)

    def create_batch(
        self,
        serialized_sequence: str,  # noqa: ARG002
        jobs: list[CreateJob],
        open: Union[bool, None] = None,
        emulator: Union[EmulatorType, None] = None,
        configuration: Union[BaseConfig, None] = None,
        wait: bool = False,  # noqa: ARG002
    ) -> Batch:
        """Create a batch of jobs and simulate its creation in the mock server."""
        batch_id = str(uuid4())
        batch = Batch(
            id=batch_id,
            open=bool(open),
            complete=bool(open),
            created_at="",
            updated_at="",
            device_type=emulator if emulator else "FRESNEL",
            project_id="",
            user_id="",
            status="DONE",
            jobs=[
                {
                    **j,
                    "batch_id": batch_id,
                    "id": str(uuid4()),
                    "project_id": "",
                    "status": "PENDING",
                    "created_at": "",
                    "updated_at": "",
                }
                for j in jobs
            ],
            configuration=configuration,
            _client=MagicMock(),
        )

        self.mock_server.set_job(batch.ordered_jobs[0])
        return batch

    def get_jobs(self, filters: JobFilters) -> PaginatedResponse:
        """Retrieve jobs based on filters, simulating the SDK's get_jobs call."""
        items: list[Job] = []

        # TODO: support cases where the filters is not a list of IDS
        assert isinstance(filters.id, list)
        items = [self.mock_server.get_job(id=str(id)) for id in filters.id]

        return PaginatedResponse(
            results=items,
            total=len(items),
            offset=0,
        )
