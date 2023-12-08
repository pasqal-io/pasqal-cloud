import json
from typing import Optional

from requests import ConnectionError, HTTPError, Response


class ExceptionWithResponseContext(BaseException):
    def __init__(self, msg: str, e: Optional[HTTPError] = None) -> None:
        if not e:
            return super().__init__(msg)
        resp: Response = e.response
        if not resp.content:
            return super().__init__(msg)
        data = resp.json()

        code = data.get("code", 0)

        if data.get("data", ""):
            description = data["data"].get("description", data.get("message"))
        else:
            description = data.get("message", "")

        super().__init__(
            f"{msg}: {code}: {description}\nDetails: {json.dumps(data, indent=2)}"
        )


class BatchException(ExceptionWithResponseContext):
    """
    Base Exception class for batches
    """


class BatchCreationError(BatchException):
    """
    Exception class when batch creation failed
    """

    def __init__(self, e: HTTPError) -> None:
        super().__init__("Batch creation failed", e)


class BatchFetchingError(BatchException):
    """
    Exception class raised when batch fetching failed.
    """

    def __init__(self, e: HTTPError) -> None:
        super().__init__("Batch fetching failed", e)


class BatchCancellingError(BatchException):
    """
    Exception class raised when batch cancelling failed.
    """

    def __init__(self, e: HTTPError) -> None:
        super().__init__("Batch cancelling failed", e)


class BatchSetCompleteError(BatchException):
    """
    Exception class raised when setting batch to complete failed.
    """

    def __init__(self, e: HTTPError) -> None:
        super().__init__("Batch setting to complete failed", e)


class JobException(ExceptionWithResponseContext):
    """
    Base Exception class for jobs.
    """


class JobCreationError(JobException):
    """
    Exception class raised when job creation failed.
    """

    def __init__(self, e: HTTPError) -> None:
        super().__init__("Job creation failed", e)


class JobFetchingError(JobException):
    """
    Exception class raised when job fetching failed.
    """

    def __init__(self, e: HTTPError) -> None:
        super().__init__("Job fetching failed", e)


class JobCancellingError(JobException):
    """
    Exception class raised when job cancelling failed.
    """

    def __init__(self, e: HTTPError) -> None:
        super().__init__("Job cancelling failed", e)


class WorkloadException(ExceptionWithResponseContext):
    """
    Base exception class for workloads.
    """


class WorkloadFetchingError(WorkloadException):
    """
    Exception class raised when workload fetching failed.
    """

    def __init__(self, e: HTTPError) -> None:
        super().__init__("Workload fetching failed", e)


class WorkloadCreationError(WorkloadException):
    """
    Exception class raised when workload creation failed.
    """

    def __init__(self, e: HTTPError) -> None:
        super().__init__("Job creation failed", e)


class WorkloadCancellingError(WorkloadException):
    """
    Exception class raised when cancelling workload failed.
    """

    def __init__(self, e: HTTPError) -> None:
        super().__init__("Workload cancelling failed", e)


class WorkloadResultsDownloadError(WorkloadException):
    """
    Exception class raised when failed to download results.
    """

    def __init__(self, e: HTTPError) -> None:
        super().__init__("Workload results download failed.", e)


class WorkloadResultsConnectionError(BaseException):
    """
    Exception class raised when failed to download results
    for a connection error.
    """

    def __init__(self, e: ConnectionError) -> None:
        super().__init__("Workload results download failed from connection error.", e)


class WorkloadResultsDecodeError(WorkloadException):
    """
    Exception class raised when download results succeeded but decoding failed.
    """

    def __init__(self) -> None:
        super().__init__("Workload results decoding failed.")


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

    def __init__(self, e: HTTPError) -> None:
        super().__init__("Device specs fetching failed", e)
