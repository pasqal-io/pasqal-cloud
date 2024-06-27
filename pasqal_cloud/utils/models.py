from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator

from pasqal_cloud.utils.constants import JobStatus


class BaseFilters(BaseModel):
    @staticmethod
    def convert_to_list(value: Any) -> Any:
        if not value:
            return None
        if isinstance(value, list):
            return value
        return [value]

    @staticmethod
    def convert_str_to_uuid(value: Any) -> Any:
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                raise ValueError(f"Cannot convert {value} to UUID.")
        return value

    @field_serializer("start_date", "end_date", check_fields=False)
    def serialize_datetime_to_isoformat(self, date: datetime) -> str:
        return date.isoformat()


class RebatchFilters(BaseFilters):
    """
    Class to provide filters for querying jobs to re-create.

    Setting a value for any attribute of this class will add a filter to the query.

    When using several filters at the same time, the API will return elements who pass
    all filters at the same time:
        - If the filter value is a single element, the API will return jobs whose
          attribute matches the provided value.
        - If the filter value is a list, the API will return jobs whose value for
          this attribute is contained in that list.

    Attributes:
        id: Filter by job IDs
        status: Filter by job statuses,
        min_runs: Minimum number of runs.
        max_runs: Maximum number of runs.
        start_date: Retry jobs created at or after this datetime.
        end_date: Retry jobs created at or before this datetime.
    """

    id: Optional[Union[List[Union[UUID, str]], Union[UUID, str]]] = None
    status: Optional[Union[List[JobStatus], JobStatus]] = None
    min_runs: Optional[int] = None
    max_runs: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("id", "status", mode="before")
    @classmethod
    def single_item_to_list_validator(cls, values: Dict[str, Any]) -> Any:
        return cls.convert_to_list(values)

    @field_validator("id", mode="after")
    @classmethod
    def str_to_uuid_validator(cls, values: Dict[str, Any]) -> Dict[str, UUID]:
        for item in values:
            cls.convert_str_to_uuid(item)
        return values

    @field_serializer("status", check_fields=False)
    def status_enum_to_string(self, job_statuses: List[JobStatus]) -> List[str]:
        return [job_status.value for job_status in job_statuses]


class JobFilters(BaseFilters):
    """
    Class to provide filters for querying jobs.

    Setting a value for any attribute of this class will add a filter to the query.

    When using several filters at the same time, the API will return elements who pass
    all filters at the same time:
        - If the filter value is a single element, the API will return jobs whose
          attribute matches the provided value.
        - If the filter value is a list, the API will return jobs whose value for
          this attribute is contained in that list.

    Attributes:
        id: Filter by job IDs.
        project_id: Filter by project IDs.
        user_id: Filter by user IDs.
        batch_id: Filter by batch IDs.
        status: Filter by job statuses.
        min_runs: Minimum number of runs.
        max_runs: Maximum number of runs.
        errors: Filter by presence of errors.
        start_date: Retry jobs created at or after this datetime.
        end_date: Retry jobs created at or before this datetime.
    """

    id: Optional[Union[List[Union[UUID, str]], Union[UUID, str]]] = None
    project_id: Optional[Union[List[Union[UUID, str]], Union[UUID, str]]] = None
    user_id: Optional[Union[List[str], str]] = None
    batch_id: Optional[Union[List[Union[UUID, str]], Union[UUID, str]]] = None
    status: Optional[Union[List[JobStatus], JobStatus]] = None
    min_runs: Optional[int] = None
    max_runs: Optional[int] = None
    errors: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("id", "project_id", "user_id", "batch_id", "status", mode="before")
    @classmethod
    def single_item_to_list_validator(cls, values: Dict[str, Any]) -> Any:
        return cls.convert_to_list(values)

    @field_validator("id", "project_id", "batch_id", mode="after")
    @classmethod
    def str_to_uuid_validator(cls, values: Dict[str, Any]) -> Dict[str, UUID]:
        for item in values:
            cls.convert_str_to_uuid(item)
        return values

    @field_serializer("status", check_fields=False)
    def status_enum_to_string(self, job_statuses: List[JobStatus]) -> List[str]:
        return [job_status.value for job_status in job_statuses]


class PaginationParams(BaseFilters):
    """
    Class providing parameters for paginating query results.

    Attributes:
        offset: The starting index of the items to return (must be 0 or greater).
        limit: The maximum number of items to return (must be greater than 0 and
               less than or equal to 100).
    """

    offset: int = Field(default=0, strict=True, ge=0)
    limit: int = Field(default=100, strict=True, gt=0, le=100)


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
