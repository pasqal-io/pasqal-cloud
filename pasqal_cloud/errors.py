class BatchException(BaseException):
    """
    Base Exception class for batches
    """


class BatchCreationError(BatchException):
    """
    Exception class when batch creation failed
    """

    def __init__(self) -> None:
        super().__init__("Batch creation failed.")


class BatchFetchingError(BatchException):
    """
    Exception class raised when batch fetching failed.
    """

    def __init__(self) -> None:
        super().__init__("Batch fetching failed.")


class BatchCancellingError(BatchException):
    """
    Exception class raised when batch cancelling failed.
    """

    def __init__(self) -> None:
        super().__init__("Batch cancelling failed.")


class BatchSetCompleteError(BatchException):
    """
    Exception class raised when setting batch to complete failed.
    """

    def __init__(self) -> None:
        super().__init__("Batch setting to complete failed.")


class JobException(BaseException):
    """
    Base Exception class for jobs.
    """


class JobCreationError(JobException):
    """
    Exception class raised when job creation failed.
    """


class JobFetchingError(JobException):
    """
    Exception class raised when job fetching failed.
    """

    def __init__(self) -> None:
        super().__init__("Job fetching failed.")


class JobCancellingError(JobException):
    """
    Exception class raised when job cancelling failed.
    """

    def __init__(self) -> None:
        super().__init__("Job cancelling failed.")


class WorkloadException(BaseException):
    """
    Base exception class for workloads.
    """


class WorkloadFetchingError(WorkloadException):
    """
    Exception class raised when workload fetching failed.
    """

    def __init__(self) -> None:
        super().__init__("Workload fetching failed.")


class WorkloadCreationError(WorkloadException):
    """
    Exception class raised when workload creation failed.
    """

    def __init__(self) -> None:
        super().__init__("Job creation failed.")


class WorkloadCancellingError(WorkloadException):
    """
    Exception class raised when cancelling workload failed.
    """

    def __init__(self) -> None:
        super().__init__("Workload cancelling failed.")


class WorkloadResultsDownloadError(WorkloadException):
    """
    Exception class raised when failed to download results.
    """

    def __init__(self) -> None:
        super().__init__("Workload results download failed.")


class InvalidWorkloadResultsFormatError(WorkloadException):
    """
    Exception class raised when download results succeeded but format
    is not as expected.
    """

    def __init__(self, result_type: type) -> None:
        super().__init__(f"Workload results should be dict but received {result_type}")


class DeviceSpecsException(BaseException):
    """
    Base Exception class for device specs
    """


class DeviceSpecsFetchingError(DeviceSpecsException):
    """
    Exception class raised when fetching of device specs failed.
    """

    def __init__(self) -> None:
        super().__init__("Device specs fetching failed.")
