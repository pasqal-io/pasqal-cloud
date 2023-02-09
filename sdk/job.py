from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Job:
    """Class for job data.

    Attributes:
        - runs: Number of time the job should be ran.
        - created_at: Timestamp of the creation of the batch.
        - updated_at: Timestamps of the last update of the batch.
        - start_timestamp(optional): The timestamp of when the job began processing.
        - end_timestamp(optional): The timestamp of when the job finished processing.
        - batch_id: Id of the batch which the job belongs to.
        - errors: Error messages that occured while processing job.
        - id: Unique identifier for the batch
        - status: Status of the job
        - result(optional): Result of the job.
        - variables (optional): dictionnary of variables of the job.
            None if the associated batch is non-parametrized
    """

    runs: int
    batch_id: str
    id: str
    status: str
    created_at: str
    updated_at: str
    errors: List[str]
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
