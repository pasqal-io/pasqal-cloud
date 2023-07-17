from pydantic import BaseModel
from pasqal_cloud.client import Client
from typing import List,Dict,Any
class Workload(BaseModel) :
    """Class for workload data.

        Attributes:
            - id: Unique identifier for the workload.
            - project_id: ID of the project which the users scheduling the workload belong to.
            - status: Status of the workload. Possible values are:
                PENDING, RUNNING, DONE, CANCELED, TIMED_OUT, ERROR, PAUSED.
            - _client: A Client instance to connect to PCS.
            - backend: The backend used for the workload.
            - workload_type: The type of the workload.
            - config: The config containing all the necessary information for the workload to run.
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
    _client: Client
    backend: str | None = None
    workload_type: str | None = None
    config: Dict[str, Any] | None = None
    created_at: str
    updated_at: str
    errors: List[str] = None
    start_timestamp: str | None = None
    end_timestamp: str | None = None
    result: Dict[str, Any] | None = None
