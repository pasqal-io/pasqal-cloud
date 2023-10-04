class BatchException(BaseException):
    """
    Base Exception class for batches
    """


class BatchCreationError(BatchException):
    """
    Exception class when batch creation failed
    """

    def __init__(self, e: Exception):
        super().__init__(f"Batch creation failed: {e}")


class BatchFetchingError(BatchException):
    """
    Exception class raised when batch fetching failed.
    """

    def __init__(self, e: Exception):
        super().__init__(f"Batch fetching failed: {e}")


class BatchCancellingError(BatchException):
    """
    Exception class raised when batch cancelling failed.
    """

    def __init__(self, e: Exception):
        super().__init__(f"Batch cancelling failed: {e}")


class BatchSetCompleteError(BatchException):
    """
    Exception class raised when setting batch to complete failed.
    """

    def __init__(self, e: Exception):
        super().__init__(f"Batch setting to complete failed: {e}")


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

    def __init__(self, e: Exception):
        super().__init__(f"Job fetching failed: {e}")


class JobCancellingError(JobException):
    """
    Exception class raised when job cancelling failed.
    """

    def __init__(self, e: Exception):
        super().__init__(f"Job cancelling failed: {e}")


class WorkloadException(BaseException):
    """
    Base exception class for workloads.
    """


class WorkloadFetchingError(WorkloadException):
    """
    Exception class raised when workload fetching failed.
    """

    def __init__(self, e: Exception):
        super().__init__(f"Workload fetching failed: {e}")


class WorkloadCreationError(WorkloadException):
    """
    Exception class raised when workload creation failed.
    """

    def __init__(self, e: Exception):
        super().__init__(f"Job creation failed: {e}")


class WorkloadCancellingError(WorkloadException):
    """
    Exception class raised when cancelling workload failed.
    """

    def __init__(self, e: Exception):
        super().__init__(f"Workload cancelling failed: {e}")


class DeviceSpecsException(BaseException):
    """
    Base Exception class for device specs
    """


class DeviceSpecsFetchingError(DeviceSpecsException):
    """
    Exception class raised when fetching of device specs failed.
    """

    def __init__(self, e: Exception):
        super().__init__(f"Device specs fetching failed: {e}")
