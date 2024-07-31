from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel

from pasqal_cloud.job import Job


class PaginatedResponse(BaseModel):
    """
    Class representing a paginated response structure.

    Attributes:
        total: The total number of items matching the query.
        offset: The starting point for the current set of paginated results.
                It indicates the number of items skipped before the current set.
        results: A list of items that match the query and pagination parameters
                 provided.
    """

    total: int
    offset: int
    results: List[Any]


class JobCancellationResponse(BaseModel):
    """
    Class representing a bulk job cancellation response structure.

    Attributes:
        jobs: A list of jobs that were successfully cancelled.
        errors: A dict of jobs id with the errors explaining why they could
        not be cancelled.
    """

    jobs: List[Job]
    errors: Dict[UUID, str]
