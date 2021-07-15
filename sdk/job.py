from dataclasses import dataclass


@dataclass
class Job:
    """Class for job data.

    Attributes:
        - runs: Number of time the job should be ran.
        - created_at: Timestamp of the creation of the batch.
        - updated_at: Timestamps of the last update of the batch.
        - batch_id: Id of the batch which the job belongs to.
        - result: Result of the job.
        - errors: Error messages that occured while processing job.
        - id: Unique identifier for the batch
        - status: Status of the job
    """

    runs: int
    batch_id: int
    id: int
    status: str
    result: str
    created_at: str
    updated_at: str
    errors: str
