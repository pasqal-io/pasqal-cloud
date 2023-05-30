from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from warnings import warn

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
        - project_id: ID of the project which the users scheduling the job belong to.
        - group_id: This parameter is deprecated, use project_id instead.
        - status: Status of the job. Possible values are: PENDING, RUNNING, DONE, CANCELED, TIMED_OUT, ERROR, PAUSED.
        - _client: A Client instance to connect to PCS.
        - result: Result of the job.
        - variables: Dictionary of variables of the job.
          None if the associated batch is non-parametrized.
    """

    runs: int
    batch_id: str
    id: str
    status: str
    _client: Client
    created_at: str
    updated_at: str
    errors: List[str]
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    # Ticket (#622)
    group_id: Optional[str] = None
    project_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Ticket (#622), used to avoid a breaking change during the group to project renaming.
        Method to be entirely removed"""
        if not (self.project_id or self.group_id):
            raise TypeError("Either a group_id or project_id has to be given as argument")
        if not self.project_id:
            warn('The parameter group_id is deprecated, from now use project_id instead',
                 DeprecationWarning,
                 stacklevel=2
                 )
            self.project_id = self.group_id

    def cancel(self) -> Dict[str, Any]:
        """Cancel the current job on the PCS."""
        job_rsp = self._client._cancel_job(self.id)
        self.status = job_rsp.get("status", "CANCELED")
        return job_rsp
