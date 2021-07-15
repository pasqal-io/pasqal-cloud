from dataclasses import dataclass, field
from enum import Enum
from typing import Dict

from sdk.client import Client
from sdk.job import Job


class DeviceType(Enum):
    EMULATOR = "EMULATOR"
    MOCK = "MOCK_DEVICE"


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
        - client: Client object for sending data to PCS API.
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
    client: Client
    jobs: Dict[int, Job] = field(default_factory=lambda: {})

    def add_job(self, runs: int = 100, variables: Dict = None, wait: bool = False):
        """Add and send a new job for this batch.

        Args:
            - runs: number of times the job is ran on the QPU.
            - variables (optional): values for variables if sequence is parametrized.

        Returns:
            - Job: the created job.
        """
        job_rsp = self.client._send_job(
            {"runs": runs, "variables": variables, "batch_id": self.id}
        )
        job = Job(**job_rsp)
        self.jobs[job.id] = job
        if wait:
            # TODO: poll results
            pass
        return job

    def declare_complete(self) -> Dict:
        """Declare to PCS that the batch is complete.

        A batch that is complete awaits no extra jobs. The batch is then unassigned to its running
        device when all its jobs are done.
        """
        self.complete = True
        return self.client._complete_batch(self.id)
