from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator

from pasqal_cloud.utils.constants import BatchStatus, JobStatus, QueuePriority


class BaseFilters(BaseModel):
    """
    Base class used by filters for shared fields.
    """

    id: Optional[Union[List[Union[UUID, str]], Union[UUID, str]]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

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


class BaseJobFilters(BaseFilters):
    """
    Base class used by Job related filters for shared fields.
    """

    min_runs: Optional[int] = None
    max_runs: Optional[int] = None


class RebatchFilters(BaseJobFilters):
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
        start_date: Jobs created at or after this datetime.
        end_date: Jobs created at or before this datetime.
    """

    status: Optional[Union[List[JobStatus], JobStatus]] = None

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


class CancelJobFilters(BaseJobFilters):
    """
    Class to provide filters for cancelling a group of jobs.

    Setting a value for any attribute of this class will add a filter to the query.

    When using several filters at the same time, the API will return elements who pass
    all filters at the same time:
        - If the filter value is a single element, the API will return jobs whose
          attribute matches the provided value.
        - If the filter value is a list, the API will return jobs whose value for
          this attribute is contained in that list.

    Attributes:
        id: Filter by job IDs
        min_runs: Minimum number of runs.
        max_runs: Maximum number of runs.
        start_date: Jobs created at or after this datetime.
        end_date: Jobs created at or before this datetime.
    """

    @field_validator("id", mode="before")
    @classmethod
    def single_item_to_list_validator(cls, values: Dict[str, Any]) -> Any:
        return cls.convert_to_list(values)

    @field_validator("id", mode="after")
    @classmethod
    def str_to_uuid_validator(cls, values: Dict[str, Any]) -> Dict[str, UUID]:
        for item in values:
            cls.convert_str_to_uuid(item)
        return values


class JobFilters(BaseJobFilters):
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
        start_date: Jobs created at or after this datetime.
        end_date: Jobs created at or before this datetime.
    """

    project_id: Optional[Union[List[Union[UUID, str]], Union[UUID, str]]] = None
    user_id: Optional[Union[List[str], str]] = None
    batch_id: Optional[Union[List[Union[UUID, str]], Union[UUID, str]]] = None
    status: Optional[Union[List[JobStatus], JobStatus]] = None
    errors: Optional[bool] = None

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


class BatchFilters(BaseFilters):
    """
    Class to provide filters for querying batches.

    Setting a value for any attribute of this class will add a filter to the query.

    When using several filters at the same time, the API will return elements who pass
    all filters at the same time:
        - If the filter value is a single element, the API will return batches whose
          attribute matches the provided value.
        - If the filter value is a list, the API will return batches whose value for
          this attribute is contained in that list.

    Attributes:
        id: Filter by batch IDs.
        project_id: Filter by project IDs.
        user_id: Filter by user IDs.
        device_type: Filter by device type.
        status: Filter by batch statuses.
        open: If the batch accepts more jobs or not.
        start_date: Batches created at or after this datetime.
        end_date: Batches created at or before this datetime.
        queue_priority: Filter by queue priority value.
        tag: Filter by a specific tag.
    """

    project_id: Optional[Union[List[Union[UUID, str]], Union[UUID, str]]] = None
    user_id: Optional[Union[List[str], str]] = None
    device_type: Optional[Union[List[str], str]] = None
    status: Optional[Union[List[BatchStatus], BatchStatus]] = None
    open: Optional[bool] = None
    queue_priority: Optional[Union[List[QueuePriority], QueuePriority]] = None
    tag: Optional[str] = None

    @field_validator(
        "id",
        "project_id",
        "user_id",
        "device_type",
        "status",
        "queue_priority",
        mode="before",
    )
    @classmethod
    def single_item_to_list_validator(cls, values: Dict[str, Any]) -> Any:
        return cls.convert_to_list(values)

    @field_validator(
        "id",
        "project_id",
        mode="after",
    )
    @classmethod
    def str_to_uuid_validator(cls, values: Dict[str, Any]) -> Dict[str, UUID]:
        for item in values:
            cls.convert_str_to_uuid(item)
        return values

    @field_serializer("status", check_fields=False)
    def status_enum_to_string(self, batch_statuses: List[BatchStatus]) -> List[str]:
        return [batch_status.value for batch_status in batch_statuses]

    @field_serializer("queue_priority", check_fields=False)
    def queue_priority_enum_to_string(
        self, queue_priorities: List[QueuePriority]
    ) -> List[str]:
        return [queue_priority.value for queue_priority in queue_priorities]


class PaginationParams(BaseModel):
    """
    Class providing parameters for paginating query results.

    Attributes:
        offset: The starting index of the items to return (must be 0 or greater).
        limit: The maximum number of items to return (must be greater than 0 and
               less than or equal to 100).
    """

    offset: int = Field(default=0, strict=True, ge=0)
    limit: int = Field(default=100, strict=True, gt=0, le=100)
