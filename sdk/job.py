from dataclasses import dataclass


@dataclass
class Job:
    runs: int
    batch_id: int
    id: int
    status: str
    result: str
    created_at: str
    updated_at: str
    errors: str
