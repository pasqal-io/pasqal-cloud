from dataclasses import dataclass, field
from enum import Enum
from typing import Dict

from sdk.client import Client
from sdk.job import Job


class DeviceType(Enum):
    EMULATOR = "EMULATOR"
    MOCK = "MOCK_DEVICE"


# TODO: docstring


@dataclass
class Batch:
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
        self.complete = True
        return self.client._complete_batch(self.id)
