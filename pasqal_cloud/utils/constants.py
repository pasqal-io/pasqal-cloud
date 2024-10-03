from enum import Enum


class BatchStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"
    CANCELED = "CANCELED"
    TIMED_OUT = "TIMED_OUT"


class JobStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"
    CANCELED = "CANCELED"


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
