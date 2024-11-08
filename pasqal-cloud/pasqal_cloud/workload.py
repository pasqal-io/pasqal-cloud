from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel, ConfigDict, field_validator, PrivateAttr
from pydantic_core.core_schema import ValidationInfo
from requests import HTTPError

from pasqal_cloud.client import Client
from pasqal_cloud.errors import (
    InvalidWorkloadResultsFormatError,
    WorkloadCancellingError,
    WorkloadResultsConnectionError,
    WorkloadResultsDecodeError,
    WorkloadResultsDownloadError,
)


class Workload(BaseModel):
    """Class for workload data.

    Attributes:
        - id: Unique identifier for the workload.
        - project_id: ID of the project which the users scheduling the workload
         belong to.
        - status: Status of the workload. Possible values are:
            PENDING, RUNNING, DONE, CANCELED, TIMED_OUT, ERROR, PAUSED.
        - _client: A Client instance to connect to PCS.
        - backend: The backend used for the workload.
        - workload_type: The type of the workload.
        - config: The config containing all the necessary information for
         the workload to run.
        - created_at: Timestamp of the creation of the workload.
        - updated_at: Timestamp of the last update of the workload.
        - errors: Error messages that occurred while processing workload.
        - start_timestamp: The timestamp of when the workload began processing.
        - end_timestamp: The timestamp of when the workload finished processing.
        - result: Result of the workload.
    """

    id: str
    project_id: str
    status: str
    _client: Client = PrivateAttr(default=None)
    backend: str
    workload_type: str
    config: Dict[str, Any]
    created_at: str
    updated_at: str
    errors: Optional[List[str]] = None
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None
    result_link: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        extra="allow", arbitrary_types_allowed=True, validate_default=True
    )

    def __init__(self, **data: Any) -> None:
        """
        Workaround to make the private attribute '_client' working
        like we need with Pydantic V2, more information on:
        https://docs.pydantic.dev/latest/concepts/models/#private-model-attributes
        """
        super().__init__(**data)
        self._client = data["_client"]

    def cancel(self) -> Dict[str, Any]:
        """Cancel the current job on the PCS."""
        try:
            workload_rsp = self._client.cancel_workload(self.id)
        except HTTPError as e:
            raise WorkloadCancellingError(e) from e
        self.status = workload_rsp.get("status", "CANCELED")
        return workload_rsp

    @field_validator("result")
    def result_link_to_result(
        cls, result: Optional[Dict[str, Any]], info: ValidationInfo
    ) -> Optional[Dict[str, Any]]:
        result_link: Optional[str] = info.data.get("result_link")
        if result or not result_link:
            return result
        try:
            res = requests.get(result_link)
        except HTTPError as e:
            raise WorkloadResultsDownloadError(e) from e
        except requests.ConnectionError as e:
            raise WorkloadResultsConnectionError(e) from e
        try:
            data = res.json()
        except Exception as e:
            raise WorkloadResultsDecodeError from e
        if not isinstance(data, dict):
            raise InvalidWorkloadResultsFormatError(type(data))
        return data
