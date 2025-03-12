from typing import Self, Type
from warnings import warn

from pasqal_cloud.utils.strenum import StrEnum


class EmulatorType(StrEnum):
    EMU_FREE = "EMU_FREE"
    EMU_TN = "EMU_TN"
    EMU_FRESNEL = "EMU_FRESNEL"
    EMU_MPS = "EMU_MPS"

    def __new__(cls: Type[Self], value) -> Self:
        instance = super().__new__(cls, value)
        warn(
            "EmulatorType is deprecated, use DeviceTypeName instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return instance
