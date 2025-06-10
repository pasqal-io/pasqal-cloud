from abc import ABC
from typing import Any

import requests


class Requester(ABC):
    """
    A class in charge of placing HTTP requests.

    Used to allow clients to inject custom HTTP requester, in particular
    to mock up server responses during testing.
    """

    def request(*args: Any, **kwargs: Any) -> Any:
        pass


class DefaultRequester(Requester):
    """
    The basic implementation of Requester, using `requests`.
    """

    def request(*args: Any, **kwargs: Any) -> Any:
        return requests.request(*args, **kwargs)
