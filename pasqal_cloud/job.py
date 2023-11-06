from typing import Any, Dict, List, Optional, TypedDict, Union

from pydantic import BaseModel, Extra
from requests import HTTPError

from pasqal_cloud.client import Client
from pasqal_cloud.errors import JobCancellingError


class Job(BaseModel):
    """Class for job data.

    Attributes:
        - runs: Number of times the job should be run.
        - batch_id: ID of the batch which the job belongs to.
        - id: Unique identifier for the job.
        - project_id: ID of the project which the users scheduling the job belong to.
        - status: Status of the job. Possible values are:
            PENDING, RUNNING, DONE, CANCELED, TIMED_OUT, ERROR, PAUSED.
        - _client: A Client instance to connect to PCS.
        - created_at: Timestamp of the creation of the job.
        - updated_at: Timestamp of the last update of the job.
        - errors: Error messages that occurred while processing job.
        - start_timestamp: The timestamp of when the job began processing.
        - end_timestamp: The timestamp of when the job finished processing.
        - full_result: Dictionnary of all the results obtained after complete execution
            of the job. It maps the type of results (e.g. "counter", "raw")
            to the associated execution result.
        - result: Bitstring counter result. Should be equal to `full_results["counter"]`
        - variables: Dictionary of variables of the job.
            None if the associated batch is non-parametrized.
        - group_id (deprecated): Use project_id instead.
    """

    runs: int
    batch_id: str
    id: str
    project_id: str
    status: str
    _client: Client
    created_at: str
    updated_at: str
    errors: Optional[List[str]] = None
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    full_result: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    # Ticket (#622)
    group_id: Optional[str] = None

    class Config:
        extra = Extra.allow
        arbitrary_types_allowed = True

    def cancel(self) -> Dict[str, Any]:
        """Cancel the current job on the PCS."""
        try:
            job_rsp = self._client._cancel_job(self.id)
        except HTTPError as e:
            raise JobCancellingError(e) from e
        self.status = job_rsp.get("status", "CANCELED")
        return job_rsp


class CreateJob(TypedDict, total=False):
    runs: int
    variables: Union[Dict[str, Any], None]
