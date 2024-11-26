import functools
import time
from typing import Callable, Iterable, Optional, Tuple, Type, TypeVar

from requests import HTTPError
from typing_extensions import ParamSpec

Param = ParamSpec("Param")
RT = TypeVar("RT")  # return type


def retry_http_error(
    max_retries: int = 5,
    retry_status_code: Optional[Iterable[int]] = None,
    retry_exceptions: Optional[Tuple[Type[Exception]]] = None,
) -> Callable[[Callable[..., RT]], Callable[..., RT]]:
    """
    Decorator to retry an HTTP call when an HTTPError is encountered.

    Args:
        max_retries: The maximum number of retry attempts
        retry_status_codes: Specific HTTP status codes to trigger a retry.
            - NB: If None, retries on all HTTP error status codes.
        retry_exceptions:  List of specific Exception classes that trigger a retry.
            - NB: If None, retries will only occur based on status codes, not
            exceptions.
    """

    def decorator(func: Callable[..., RT]) -> Callable[..., RT]:
        @functools.wraps(func)
        def wrapper(*args: Param.args, **kwargs: Param.kwargs) -> RT:
            for iteration in range(max_retries + 1):
                try:
                    response = func(*args, **kwargs)
                except HTTPError as e:  # noqa:  PERF203
                    if (
                        e.response is None
                        or (
                            retry_status_code is not None
                            and e.response.status_code not in retry_status_code
                        )
                        or iteration == max_retries
                    ):
                        raise e
                    delay = (1 * 2) ** iteration
                    time.sleep(delay)
                except Exception as e:
                    if (
                        retry_exceptions
                        and isinstance(e, retry_exceptions)
                        and iteration < max_retries
                    ):
                        delay = (1 * 2) ** iteration
                        time.sleep(delay)
                    else:
                        raise e
                else:
                    return response

            # There is no scenario where we want to reach this
            # so we can raise a generic Exception
            raise Exception(
                "HTTP Client has encountered an issue it is unable to recover from."
            )

        return wrapper

    return decorator
