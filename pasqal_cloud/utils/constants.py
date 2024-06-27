from enum import Enum


class Status(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"
    CANCELED = "CANCELED"


class BatchStatus(Status):
    pass


class JobStatus(Status):
    pass


class QueuePriority(Enum):
    """
    Values represent the queue a value will be written to, each priority
    represents the order of preference batches will be executed.

    HIGH being the quickest
    MEDIUM being a lower tier
    LOW being the lowest tier
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
