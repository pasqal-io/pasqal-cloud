from pasqal_cloud.utils.strenum import StrEnum


class ResultType(StrEnum):
    COUNTER = "counter"
    RUN = "run"
    SAMPLE = "sample"
    EXPECTATION = "expectation"
