import time
from typing import Any, Dict, Optional, Type, Union

from pydantic import BaseModel, Extra, root_validator, validator

from pasqal_cloud.client import Client
from pasqal_cloud.device import EmulatorType
from pasqal_cloud.device.configuration import (
    BaseConfig,
    EmuFreeConfig,
    EmuTNConfig,
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
        - status: Status of the batch. Possible values are: PENDING, RUNNING, DONE, CANCELED, TIMED_OUT, ERROR, PAUSED.
        - webhook: Webhook where the job results are automatically sent to.
        - _client: A Client instance to connect to PCS.
        - sequence_builder: Pulser sequence of the batch.
        - start_datetime: Timestamp of the time the batch was sent to the QPU.
        - end_datetime: Timestamp of when the batch process was finished.
        - device_status: Status of the device where the batch is running.
        - jobs: Dictionary of all the jobs added to the batch.
        - jobs_count: Number of jobs added to the batch.
        - jobs_count_per_status: Number of jobs per status.
        - configuration: Further configuration for certain emulators.
        - group_id: This parameter is deprecated, use project_id instead.
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
    jobs: Dict[str, Job] = {}
    jobs_count: int = 0
    jobs_count_per_status: Dict[str, int] = {}
    configuration: Union[BaseConfig, Dict[str, Any], None] = None

    class Config:
        extra = Extra.allow
        arbitrary_types_allowed = True

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

    @root_validator(pre=True)
    def _build_job_dict(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        jobs = values.get("jobs", [])
        job_dict = {}
        for job in jobs:
            job_dict[job["id"]] = {**job, "_client": values["_client"]}
        values["jobs"] = job_dict
        return values

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
        job_rsp = self._client._send_job(job_data)
        job = Job(**job_rsp, _client=self._client)
        self.jobs[job.id] = job
        if wait:
            while job.status in ["PENDING", "RUNNING"]:
                time.sleep(RESULT_POLLING_INTERVAL)
                job_rsp = self._client._get_job(job.id)
                job = Job(**job_rsp)
        return job

    def declare_complete(
        self, wait: bool = False, fetch_results: bool = False
    ) -> Dict[str, Any]:
        """Declare to PCS that the batch is complete.

        Args:
            wait: Whether to wait for the batch to be done.
            fetch_results: Whether to download the results. Implies waiting for the batch.

        A batch that is complete awaits no extra jobs. All jobs previously added
        will be executed before the batch is terminated. When all its jobs are done,
        the complete batch is unassigned to its running device.
        """
        batch_rsp = self._client._complete_batch(self.id)
        self.complete = True
        if wait or fetch_results:
            while batch_rsp["status"] in ["PENDING", "RUNNING"]:
                time.sleep(RESULT_POLLING_INTERVAL)
                batch_rsp, jobs_rsp = self._client._get_batch(
                    self.id,
                )
            if fetch_results:
                batch_rsp, jobs_rsp = self._client._get_batch(
                    self.id, fetch_results=True
                )
            for job_rsp in jobs_rsp:
                self.jobs[job_rsp["id"]] = Job(**job_rsp)
        return batch_rsp

    def cancel(self) -> Dict[str, Any]:
        """Cancel the current batch on the PCS."""
        batch_rsp = self._client._cancel_batch(self.id)
        self.status = batch_rsp.get("status", "CANCELED")
        return batch_rsp
