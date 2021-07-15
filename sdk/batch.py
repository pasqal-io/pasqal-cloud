import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict

from sdk.client import Client
from sdk.job import Job


class DeviceType(Enum):
    EMULATOR = "EMULATOR"
    MOCK = "MOCK_DEVICE"


JOB_RESULT_POLLING_INTERVAL = 60  # 1 minute


@dataclass
class Batch:
    """Class for batch data.

    A batch groups up several jobs with the same sequence. When a batch is assigned to a QPU,
    all its jobs are ran sequentially and no other batch can be assigned to the device
    until all its jobs are done and it is declared complete.

    Attributes:
        - complete: Whether the batch has been declared as complete.
        - created_at: Timestamp of the creation of the batch.
        - updated_at: Timestamps of the last update of the batch.
        - device_type: Type of device To run the batch on.
        - group_id: Id of the owner group of the batch.
        - id: Unique identifier for the batch
        - priority: Level of priority of the batch
        - status: Status of the batch
        - webhook: Webhook where the job results are automatically sent to.
        - jobs: Dictionnary of all the jobs added to the batch.
    """

    complete: bool
    created_at: str
    updated_at: str
    device_type: str
    group_id: int
    id: int
    priority: int
    status: str
    webhook: str
    _client: Client
    jobs: Dict[int, Job] = field(default_factory=lambda: {})

    def add_job(self, runs: int = 100, variables: Dict = None, wait: bool = False):
        """Add and send a new job for this batch.

        Args:
            runs: number of times the job is ran on the QPU.
            variables (optional): values for variables if sequence is parametrized.
            wait: Whether to wait for results to be sent back.

        Returns:
            - Job: the created job.
        """
        job_rsp = self._client._send_job(
            {"runs": runs, "variables": variables, "batch_id": self.id}
        )
        job = Job(**job_rsp)
        self.jobs[job.id] = job
        if wait:
            while job.status == "PENDING":
                time.sleep(JOB_RESULT_POLLING_INTERVAL)
                job_rsp = self._client._get_job(job.id)
                job = Job(**job_rsp)
        return job

    def declare_complete(self, wait: bool = False) -> Dict:
        """Declare to PCS that the batch is complete.

        Args:
            wait: Whether to wait for results to be sent back.

        A batch that is complete awaits no extra jobs. The batch is then unassigned to its running
        device when all its jobs are done.
        """
        self.complete = True
        rsp = self._client._complete_batch(self.id)
        if wait:
            for job_id in self.jobs:
                job = self.jobs[job_id]
                while job.status == "PENDING":
                    job = self._client._get_job(job.id)
                    time.sleep(JOB_RESULT_POLLING_INTERVAL)
        return rsp
