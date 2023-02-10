import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type, Union

from sdk.client import Client
from sdk.job import Job
from sdk.device.configuration import BaseConfig, EmuTNConfig, EmuFreeConfig
from sdk.device.device_types import DeviceType

RESULT_POLLING_INTERVAL = 2  # seconds


@dataclass
class Batch:
    """Class for batch data.

    A batch groups up several jobs with the same sequence. When a batch is assigned to
    a QPU, all its jobs are ran sequentially and no other batch can be assigned to the
    device until all its jobs are done and it is declared complete.

    Attributes:
        - complete: Whether the batch has been declared as complete.
        - created_at: Timestamp of the creation of the batch.
        - updated_at: Timestamps of the last update of the batch.
        - device_type: Type of device to run the batch on.
        - group_id: Id of the owner group of the batch.
        - id: Unique identifier for the batch.
        - user_id: Unique identifier of the user that created the batch.
        - priority: Level of priority of the batch.
        - status: Status of the batch.
        - webhook: Webhook where the job results are automatically sent to.
        - sequence_builder: Pulser sequence of the batch.
        - start_datetime: Timestamp of the time the batch was sent to the QPU.
        - end_datetime: Timestamp of when the  batch process was finished.
        - device_status: Status of the device where the batch is running.
        - jobs: Dictionary of all the jobs added to the batch.
        - jobs_count: number of jobs added to the batch.
        - jobs_count_per_status: number of jobs per status.
        - configuration: Further configuration for certain emulators.

    """

    complete: bool
    created_at: str
    updated_at: str
    device_type: str
    group_id: str
    id: str
    user_id: int
    priority: int
    status: str
    webhook: str
    _client: Client
    sequence_builder: str
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    device_status: Optional[str] = None
    jobs: Dict[str, Job] = field(default_factory=dict)
    jobs_count: int = 0
    jobs_count_per_status: Dict[str, int] = field(default_factory=dict)
    configuration: Optional[Union[BaseConfig, dict]] = None

    def __post_init__(self) -> None:
        """Post init method to convert the configuration to a BaseConfig object."""
        if not isinstance(self.configuration, dict):
            return
        conf_class: Type[BaseConfig] = BaseConfig
        if self.device_type == DeviceType.EMU_TN.value:
            conf_class = EmuTNConfig
        elif self.device_type == DeviceType.EMU_FREE.value:
            conf_class = EmuFreeConfig

        self.configuration = conf_class.from_dict(self.configuration)

    def add_job(
        self,
        runs: int = 100,
        variables: Optional[Dict[str, Any]] = None,
        wait: bool = False,
    ) -> Job:
        """Add and send a new job for this batch.

        Args:
            runs: number of times the job is ran on the QPU.
            variables (optional): values for variables if sequence is parametrized.
            wait: Whether to wait for the job to be done.

        Returns:
            - Job: the created job.
        """
        job_data: Dict[str, Any] = {"runs": runs, "batch_id": self.id}
        if variables:
            job_data["variables"] = variables
        job_rsp = self._client._send_job(job_data)
        job = Job(**job_rsp)
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
            wait: Whether to wait for the batch to be done
            fetch_results: Whether to download the results. Implies waiting for the batch.

        A batch that is complete awaits no extra jobs. All jobs previously added
        will be executed before the batch is terminated. When all its jobs are done,
        the complete batch is unassigned to its running device.
        """
        self.complete = True
        batch_rsp = self._client._complete_batch(self.id)
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
