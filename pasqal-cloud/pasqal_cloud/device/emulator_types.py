from warnings import simplefilter, warn

from pasqal_cloud.utils.strenum import StrEnum

# Ensure DeprecationWarnings are not filtered out at runtime
simplefilter("always", DeprecationWarning)


class EmulatorType(StrEnum):
    EMU_FREE = "EMU_FREE"
    EMU_TN = "EMU_TN"
    EMU_FRESNEL = "EMU_FRESNEL"
    EMU_MPS = "EMU_MPS"


def __init__(_, *args, **kwargs) -> None:
    warn(
        "EmulatorType is deprecated, use DeviceTypeName instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    super().__init__(args, kwargs)
