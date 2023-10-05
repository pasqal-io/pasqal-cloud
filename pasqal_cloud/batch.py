import time
from typing import Any, Dict, List, Optional, Type, Union
from warnings import warn

from pydantic import BaseModel, Extra, root_validator, validator
from requests import HTTPError

from pasqal_cloud.client import Client
from pasqal_cloud.device import EmulatorType
from pasqal_cloud.device.configuration import BaseConfig, EmuFreeConfig, EmuTNConfig
from pasqal_cloud.errors import (
    BatchFetchingError,
    BatchSetCompleteError,
    BatchCancellingError,
    JobCreationError,
    JobFetchingError,
)
from pasqal_cloud.job import Job

RESULT_POLLING_INTERVAL = 2  # seconds


class Batch(BaseModel):
    """Class to load batch data return by the API.

    A batch groups up several jobs with the same sequence. When a batch is assigned to
    a QPU, all its jobs are ran sequentially and no other batch can be assigned to the
    device until all its jobs are done and declared complete.

    Attributes:
        - complete: Whether the batch has been declared as complete.
        - created_at: Timestamp of the creation of the batch.
        - updated_at: Timestamp of the last update of the batch.
        - device_type: Type of device to run the batch on.
        - project_id: ID of the owner project of the batch.
        - id: Unique identifier for the batch.
        - user_id: Unique identifier of the user that created the batch.
        - priority: Level of priority of the batch.
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
        - group_id (deprecated): Use project_id instead.
    """

    complete: bool
    created_at: str
    updated_at: str
    device_type: str
    project_id: str
    id: str
    user_id: str
    priority: int
    status: str
    webhook: Optional[str]
    _client: Client
    sequence_builder: str
    start_datetime: Optional[str]
    end_datetime: Optional[str]
    device_status: Optional[str]
    ordered_jobs: List[Job] = []
    jobs_count: int = 0
    jobs_count_per_status: Dict[str, int] = {}
    configuration: Union[BaseConfig, Dict[str, Any], None] = None

    class Config:
        extra = Extra.allow
        arbitrary_types_allowed = True

    @root_validator(pre=True)
    def _build_ordered_jobs(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """This root validator will modify the 'jobs' attribute which is a list
        of jobs dictionaries ordered by creation time before instantiation.
        It will duplicate the value of 'jobs' in a new attribute 'ordered_jobs'
        to keep the jobs ordered by creation time.
        """
        ordered_jobs_list = []
        jobs_received = values.get("jobs", [])
        for job in jobs_received:
            job_dict = {**job, "_client": values["_client"]}
            ordered_jobs_list.append(job_dict)
        values["ordered_jobs"] = ordered_jobs_list
        return values

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

    @validator("configuration", pre=True)
    def _load_configuration(
        cls,
        configuration: Union[Dict[str, Any], BaseConfig, None],
        values: Dict[str, Any],
    ) -> Optional[BaseConfig]:
        if not isinstance(configuration, dict):
            return configuration
        conf_class: Type[BaseConfig] = BaseConfig
        if values["device_type"] == EmulatorType.EMU_TN.value:
            conf_class = EmuTNConfig
        elif values["device_type"] == EmulatorType.EMU_FREE.value:
            conf_class = EmuFreeConfig
        return conf_class.from_dict(configuration)

    def add_job(
        self,
        runs: int = 100,
        variables: Optional[Dict[str, Any]] = None,
        wait: bool = False,
    ) -> Job:
        """Add and send a new job for this batch.

        Args:
            runs: number of times the job is run on the QPU.
            variables (optional): values for variables if sequence is parametrized.
            wait: Whether to wait for the job to be done.

        Returns:
            - Job: the created job.
        """
        job_data: Dict[str, Any] = {"runs": runs, "batch_id": self.id}
        if variables:
            job_data["variables"] = variables
        try:
            job_rsp = self._client._send_job(job_data)
        except HTTPError as e:
            raise JobCreationError from e
        job = Job(**job_rsp, _client=self._client)
        self.ordered_jobs.append(job)
        if wait:
            while job.status in ["PENDING", "RUNNING"]:
                time.sleep(RESULT_POLLING_INTERVAL)
                try:
                    job_rsp = self._client._get_job(job.id)
                except HTTPError as e:
                    raise JobFetchingError from e
                job = Job(**job_rsp)
        return job

    def declare_complete(
        self, wait: bool = False, fetch_results: bool = False
    ) -> Dict[str, Any]:
        """Declare to PCS that the batch is complete.

        Args:
            wait: Whether to wait for the batch to be done and fetch results.
            fetch_results (deprecated): Whether to wait for the batch \
                to be done and fetch results.

        A batch that is complete awaits no extra jobs. All jobs previously added
        will be executed before the batch is terminated. When all its jobs are done,
        the complete batch is unassigned to its running device.
        """
        try:
            batch_rsp = self._client._complete_batch(self.id)
        except HTTPError as e:
            raise BatchSetCompleteError from e
        self.complete = True
        if wait or fetch_results:
            while batch_rsp["status"] in ["PENDING", "RUNNING"]:
                time.sleep(RESULT_POLLING_INTERVAL)
                try:
                    batch_rsp = self._client._get_batch(
                        self.id,
                    )
                except HTTPError as e:
                    raise BatchFetchingError from e
            self.ordered_jobs = [
                Job(**job, _client=self._client) for job in batch_rsp["jobs"]
            ]

        return batch_rsp

    def cancel(self) -> Dict[str, Any]:
        """Cancel the current batch on the PCS."""
        try:
            batch_rsp = self._client._cancel_batch(self.id)
        except HTTPError as e:
            raise BatchCancellingError from e
        self.status = batch_rsp.get("status", "CANCELED")
        return batch_rsp
