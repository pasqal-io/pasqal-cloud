from pasqal_cloud.utils.strenum import StrEnum


class EmulatorType(StrEnum):
    """
    Enum for the emulator type, is deprecated.
    Use DeviceTypeName instead.
    """

    EMU_FREE = "EMU_FREE"
    EMU_TN = "EMU_TN"
    EMU_FRESNEL = "EMU_FRESNEL"
    EMU_MPS = "EMU_MPS"
