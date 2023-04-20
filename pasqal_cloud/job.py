from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pasqal_cloud.client import Client


@dataclass
class Job:
    """Class for job data.

    Attributes:
        - runs: Number of times the job should be run.
        - created_at: Timestamp of the creation of the job.
        - updated_at: Timestamp of the last update of the job.
        - start_timestamp: The timestamp of when the job began processing.
        - end_timestamp: The timestamp of when the job finished processing.
        - batch_id: ID of the batch which the job belongs to.
        - errors: Error messages that occurred while processing job.
        - id: Unique identifier for the job.
        - group_id: ID of the group which the users scheduling the job belong to.
        - status: Status of the job. Possible values are: PENDING, RUNNING, DONE, CANCELED, TIMED_OUT, ERROR, PAUSED.
        - _client: A Client instance to connect to PCS.
        - result: Result of the job.
        - variables: Dictionary of variables of the job.
          None if the associated batch is non-parametrized.
    """

    runs: int
    batch_id: str
    id: str
    group_id: str
    status: str
    _client : Client
    created_at: str
    updated_at: str
    errors: List[str]
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None

    def cancel(self) -> Dict[str, Any]:
        """Cancel the current job on the PCS."""
        job_rsp = self._client._cancel_job(self.id)
        self.status = job_rsp.get("status", "CANCELED")
        return job_rsp
