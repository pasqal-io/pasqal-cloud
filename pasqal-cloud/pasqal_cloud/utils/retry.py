import functools
import math
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Callable, Iterable, Optional, Tuple, Type, TypeVar

from requests import HTTPError
from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from requests import Response

Param = ParamSpec("Param")
RT = TypeVar("RT")  # return type


def _retry_after_seconds(response: "Response") -> int | None:
    """Parse Retry-After header (seconds or HTTP-date). None if absent/invalid."""
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        # RFC 9110 Retry-After allows an HTTP-date (RFC 1123 format, e.g.
        # "Sun, 06 Nov 1994 08:49:37 GMT"). parsedate_to_datetime parses that
        # format (plus obsolete RFC 850/asctime variants) locale-independently,
        # unlike strptime which depends on locale for day/month names.
        target = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    now = datetime.now(timezone.utc)
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    return max(math.ceil((target - now).total_seconds()), 0)


def retry_http_error(
    max_retries: int = 5,
    retry_status_code: Optional[Iterable[int]] = None,
    retry_exceptions: Optional[Tuple[Type[Exception]]] = None,
) -> Callable[[Callable[..., RT]], Callable[..., RT]]:
    """
    Decorator to retry an HTTP call when an HTTPError is encountered.

    Args:
        max_retries: The maximum number of retry attempts
        retry_status_code: Specific HTTP status codes to trigger a retry.
            - NB: If None, retries on all HTTP error status codes.
        retry_exceptions:  List of specific Exception classes that trigger a retry.
            - NB: If None, retries will only occur based on status codes, not
            exceptions.
    """

    def decorator(func: Callable[..., RT]) -> Callable[..., RT]:
        @functools.wraps(func)
        def wrapper(*args: Param.args, **kwargs: Param.kwargs) -> RT:
            for iteration in range(max_retries + 1):
                # 2 seconds, 4 seconds, 8 seconds, 16 seconds, 32 seconds
                delay = 2**iteration
                try:
                    response = func(*args, **kwargs)
                except HTTPError as e:
                    if (
                        e.response is None
                        or (
                            retry_status_code is not None
                            and e.response.status_code not in retry_status_code
                        )
                        or iteration == max_retries
                    ):
                        raise e
                    if e.response.status_code == 429:
                        retry_after = _retry_after_seconds(e.response)
                        if retry_after is not None:
                            delay = retry_after
                    time.sleep(delay)
                except Exception as e:
                    if (
                        retry_exceptions
                        and isinstance(e, retry_exceptions)
                        and iteration < max_retries
                    ):
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
