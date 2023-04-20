import warnings


def pasqal_sdk_not_updated():
    warnings.warn(
        "pasqal-sdk package is deprecated, please use pasqal_cloud instead: `pip install pasqal-cloud`",
        DeprecationWarning,
    )


pasqal_sdk_not_updated()
from pasqal_cloud import *
