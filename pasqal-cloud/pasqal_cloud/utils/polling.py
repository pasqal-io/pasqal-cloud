# Copyright 2020 Pasqal Cloud Services development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from typing import Any, Callable, Dict, TypeVar

import tenacity

# Wait between attempts follows ``POLL_WAIT_INITIAL_SECONDS * 2**(attempt-1)``
# and is capped at ``POLL_WAIT_MAX_SECONDS``. With the values below the
# schedule is: 2s, 4s, 8s, 16s, 30s, 30s, 30s, ...
POLL_WAIT_INITIAL_SECONDS = 2
POLL_WAIT_MAX_SECONDS = 30

# Non-terminal statuses shared by both batches and jobs. As soon as neither
# PENDING nor RUNNING jobs remain, the batch/job is considered terminal.
NON_TERMINAL_STATUSES = frozenset({"PENDING", "RUNNING"})

T = TypeVar("T")


def poll_status(
    fetcher: Callable[[], T],
    should_continue: Callable[[T], bool],
) -> T:
    """Call ``fetcher`` repeatedly until ``should_continue(result)`` returns False.

    Wait between attempts grows exponentially starting at
    :data:`POLL_WAIT_INITIAL_SECONDS` and is capped at
    :data:`POLL_WAIT_MAX_SECONDS`. There is no total-time or attempt-count
    cap: the loop only exits when the predicate reports that the last
    result is terminal, or when ``fetcher`` raises.

    Args:
        fetcher: Zero-argument callable that returns the current status
            payload for a batch or a job.
        should_continue: Predicate that receives the value returned by
            ``fetcher`` and must return True to keep polling (still
            non-terminal) or False to exit and return that value.

    Returns:
        The last value returned by ``fetcher`` (the terminal status
        payload).
    """
    retryer = tenacity.Retrying(
        wait=tenacity.wait_exponential(
            multiplier=POLL_WAIT_INITIAL_SECONDS,
            max=POLL_WAIT_MAX_SECONDS,
        ),
        stop=tenacity.stop_never,
        retry=tenacity.retry_if_result(should_continue),
        reraise=True,
    )
    return retryer(fetcher)


def batch_still_running(status_data: dict[str, Any]) -> bool:
    """Predicate: True while a batch still has PENDING or RUNNING jobs.

    Mirrors the historical polling condition
    ``any(job.status in {"PENDING", "RUNNING"} for job in ordered_jobs)``
    """
    counts = status_data.get("jobs_count_per_status") or {}
    return any(counts.get(status, 0) > 0 for status in NON_TERMINAL_STATUSES)


def job_still_running(status_data: dict[str, Any]) -> bool:
    """Predicate: True while a job status is PENDING or RUNNING."""
    return status_data.get("status") in NON_TERMINAL_STATUSES
