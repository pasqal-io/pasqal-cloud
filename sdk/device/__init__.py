import warnings

warnings.warn(
    "cloud-sdk package is deprecated, please use pasqal_cloud instead: `pip install pasqal-cloud`",
    DeprecationWarning,
)

from pasqal_cloud.device.device_types import *
