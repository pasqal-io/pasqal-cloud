import time
from typing import Any, Dict, List, Optional, Type, Union
from warnings import warn

from pydantic import BaseModel, ConfigDict, field_validator, PrivateAttr, ValidationInfo
from requests import HTTPError

from pasqal_cloud.client import Client
from pasqal_cloud.device import EmulatorType
from pasqal_cloud.device.configuration import (
    BaseConfig,
    EmuFreeConfig,
    EmuTNConfig,
)
from pasqal_cloud.errors import (
    BatchCancellingError,
    BatchClosingError,
    BatchFetchingError,
    JobCreationError,
    JobRetryError,
)
from pasqal_cloud.job import CreateJob, Job

RESULT_POLLING_INTERVAL = 2  # seconds


class Batch(BaseModel):
    """Class to load batch data return by the API.

    A batch groups up several jobs with the same sequence. When a batch is assigned to
    a QPU, all its jobs are run sequentially and no other batch can be assigned to the
    device until all its jobs are done and declared complete.

    Attributes:
        - open: Whether the batch accepts more jobs or not.
        - complete: Opposite of open, deprecated.
        - created_at: Timestamp of the creation of the batch.
        - updated_at: Timestamp of the last update of the batch.
        - device_type: Type of device to run the batch on.
        - project_id: ID of the owner project of the batch.
        - id: Unique identifier for the batch.
        - user_id: Unique identifier of the user that created the batch.
        - status: Status of the batch. Possible values are:
            PENDING, RUNNING, DONE, CANCELED, TIMED_OUT, ERROR, PAUSED.
        - webhook: Webhook where the job results are automatically sent to.
        - _client: A Client instance to connect to PCS.
        - sequence_builder: Pulser sequence of the batch.
        - start_datetime: Timestamp of the time the batch was sent to the QPU.
        - end_datetime: Timestamp of when the batch process was finished.
        - device_status: Status of the device where the batch is running.
        - jobs (deprecated): Dictionary of all the jobs added to the batch.
        - ordered_jobs: List of all the jobs added to the batch,
            ordered by creation time.
        - jobs_count: Number of jobs added to the batch.
        - jobs_count_per_status: Number of jobs per status.
        - configuration: Further configuration for certain emulators.
    """

    open: bool
    complete: bool
    created_at: str
    updated_at: str
    device_type: str
    project_id: str
    id: str
    user_id: str
    status: str
    _client: Client = PrivateAttr(default=None)
    sequence_builder: str
    _ordered_jobs: Optional[List[Job]] = PrivateAttr(default=None)
    jobs_count: int = 0
    jobs_count_per_status: Dict[str, int] = {}
    webhook: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    device_status: Optional[str] = None
    parent_id: Optional[str] = None
    configuration: Union[BaseConfig, Dict[str, Any], None] = None

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(self, **data: Any) -> None:
        """
        Workaround to make the private attribute '_client' working
        like we need with Pydantic V2, more information on:
        https://docs.pydantic.dev/latest/concepts/models/#private-model-attributes
        """
        super().__init__(**data)
        self._client = data["_client"]
        if data.get("jobs"):
            self._ordered_jobs = [
                Job(**raw_job, _client=self._client) for raw_job in data["jobs"]
            ]

    @property
    def ordered_jobs(self) -> List[Job]:
        if self._ordered_jobs is None:
            raw_jobs = self._client.get_batch_jobs(batch_id=self.id)
            self._ordered_jobs = [
                Job(**raw_job, _client=self._client) for raw_job in raw_jobs
            ]
        return self._ordered_jobs

    @ordered_jobs.setter
    def ordered_jobs(self, value: Any) -> None:
        self._ordered_jobs = value

    # Ticket (#704), to be removed or updated
    @property
    def jobs(self) -> Dict[str, Job]:
        """Once the 'ordered_jobs' is built, we need to keep the 'jobs' attribute
        for backward compatibility with the code written by the users of the sdk
        """
        warn(
            "'jobs' attribute is deprecated, use 'ordered_jobs' instead",
            DeprecationWarning,
            stacklevel=1,
        )
        return {job.id: job for job in self.ordered_jobs}

    @jobs.setter
    def jobs(self, _: Any) -> None:
        # Override the jobs setter to be a no-op.
        # `jobs` is a read-only attribute which is derived from the `ordered_jobs` key.
        pass

    @field_validator("configuration", mode="before")
    def _load_configuration(
        cls,
        configuration: Union[Dict[str, Any], BaseConfig, None],
        info: ValidationInfo,
    ) -> Optional[BaseConfig]:
        if not isinstance(configuration, dict):
            return configuration
        conf_class: Type[BaseConfig] = BaseConfig
        if info.data["device_type"] == EmulatorType.EMU_TN.value:
            conf_class = EmuTNConfig
        elif info.data["device_type"] == EmulatorType.EMU_FREE.value:
            conf_class = EmuFreeConfig
        elif info.data["device_type"] == EmulatorType.EMU_FRESNEL.value:
            return None
        return conf_class.from_dict(configuration)

    def add_jobs(
        self,
        jobs: List[CreateJob],
        wait: bool = False,
    ) -> None:
        """Add some jobs to batch for execution on PCS and returns the updated batch.

        The batch must be `open` otherwise the API will return an error.
        The new jobs are appended to the `ordered_jobs` list attribute.

        Args:
            jobs: List of jobs to be added to the batch.
            wait: If True, blocks until all jobs in the batch are done.

        """
        try:
            batch_rsp = self._client.add_jobs(self.id, jobs)
        except HTTPError as e:
            raise JobCreationError(e) from e
        self._update_from_api_response(batch_rsp)

        if wait:
            while any(
                job.status in {"PENDING", "RUNNING"} for job in self.ordered_jobs
            ):
                time.sleep(RESULT_POLLING_INTERVAL)
                self.refresh()

    def retry(self, job: Job, wait: bool = False) -> None:
        """
        Retry a job in the same batch.
        The batch should not be 'closed'.
        The new job is appended to the `ordered_jobs` list attribute.

        Args:
            job: The job to retry
            wait: Whether to wait for job completion

        Raises:
            JobRetryError if there was an error adding the job to the batch.
        """
        retried_job = CreateJob(runs=job.runs, variables=job.variables)
        try:
            self.add_jobs([retried_job], wait=wait)
        except JobCreationError as e:
            raise JobRetryError from e

    def declare_complete(self, wait: bool = False, fetch_results: bool = False) -> None:
        """
        Deprecated, use close instead.
        """
        warn(
            "This method is deprecated, use close instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.close(wait=wait, fetch_results=fetch_results)

    def close(self, wait: bool = False, fetch_results: bool = False) -> None:
        """Declare to PCS that the batch is closed and returns an updated
        batch instance.

        Args:
            wait: Whether to wait for the batch to be done and fetch results.
            fetch_results (deprecated): Whether to wait for the batch \
                to be done and fetch results.

        A batch that is closed awaits no extra jobs. All jobs previously added
        will be executed before the batch is terminated. When all its jobs are done,
        the closed batch is unassigned to its running device.
        """
        try:
            batch_rsp = self._client.close_batch(self.id)
        except HTTPError as e:
            raise BatchClosingError(e) from e
        self._update_from_api_response(batch_rsp)
        if wait or fetch_results:
            while any(
                job.status in {"PENDING", "RUNNING"} for job in self.ordered_jobs
            ):
                time.sleep(RESULT_POLLING_INTERVAL)
                self.refresh()

    def cancel(self) -> None:
        """Cancel the current batch on the PCS."""
        try:
            batch_rsp = self._client.cancel_batch(self.id)
        except HTTPError as e:
            raise BatchCancellingError(e) from e
        self._update_from_api_response(batch_rsp)

    def refresh(self) -> None:
        """Fetch the batch from the API and update it in place."""
        try:
            batch_rsp = self._client.get_batch(self.id)
        except HTTPError as e:
            raise BatchFetchingError(e) from e
        self._update_from_api_response(batch_rsp)

    def _update_from_api_response(self, data: Dict[str, Any]) -> None:
        """Update the instance in place with the response body of the batch API"""
        updated_batch = Batch(**data, _client=self._client)
        # Private fields are not exposed by the model_fields method, so we need to
        # explicitly add _ordered_jobs to ensure it is copied from the updated_batch
        # model.
        batch_model_fields = [*list(updated_batch.model_fields), "_ordered_jobs"]
        for field in batch_model_fields:
            value = getattr(updated_batch, field)
            setattr(self, field, value)
