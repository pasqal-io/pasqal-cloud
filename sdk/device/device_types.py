from sdk.utils.strenum import StrEnum


class DeviceType(StrEnum):
    QPU = "QPU"
    EMU_FREE = "EMU_FREE"
    EMU_TN = "EMU_TN"

    @property
    def configurable(self) -> bool:
        return self in (DeviceType.EMU_FREE, DeviceType.EMU_TN)
