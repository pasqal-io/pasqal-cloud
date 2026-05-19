import warnings
from typing import Any

from pasqal_cloud.http_client import HTTPClient


class Client(HTTPClient):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        warnings.warn(
            "'Client' is an alias to 'HTTPClient' and will be "
            "removed in a future release. "
            "Please use 'HTTPClient' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
