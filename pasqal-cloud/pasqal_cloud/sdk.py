import warnings
from typing import Any

from pasqal_cloud.pasqal_cloud_client import PasqalCloudClient


class SDK(PasqalCloudClient):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        warnings.warn(
            "'SDK' is an alias to 'PasqalCloudClient' and will be "
            "removed in a future release. "
            "Please use 'PasqalCloudClient' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
