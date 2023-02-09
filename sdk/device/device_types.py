from sdk.utils.strenum import StrEnum


class DeviceType(StrEnum):
    QPU = "QPU"
    EMU_FREE = "EMU_FREE"
    EMU_SV = "EMU_SV"

    @property
    def configurable(self) -> bool:
        return self in (DeviceType.EMU_FREE, DeviceType.EMU_SV)
