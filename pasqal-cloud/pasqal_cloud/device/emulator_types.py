from warnings import warn

from pasqal_cloud.utils.strenum import StrEnum


class EmulatorType(StrEnum):
    EMU_FREE = "EMU_FREE"
    EMU_TN = "EMU_TN"
    EMU_FRESNEL = "EMU_FRESNEL"
    EMU_MPS = "EMU_MPS"

    def __init__(self, value: str) -> None:
        warn(
            "EmulatorType is deprecated, use DeviceTypeName instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(value)
