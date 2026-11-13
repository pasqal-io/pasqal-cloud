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
import logging
import time
from typing import Any, Callable, Dict, Optional, TypeVar

import tenacity

from pasqal_cloud.utils.duration import format_duration

logger = logging.getLogger(__name__)

# Wait between attempts follows ``POLL_WAIT_INITIAL_SECONDS * 2**(attempt-1)``
# and is capped at ``POLL_WAIT_MAX_SECONDS``. With the values below the
# schedule is: 2s, 4s, 8s, 16s, 30s, 30s, 30s, ...
POLL_WAIT_INITIAL_SECONDS = 2
POLL_WAIT_MAX_SECONDS = 30

# Upper bound on a wait stretched by a wait hint. The queue estimate is rough
# and batches ahead may be canceled, so a batch that starts early is noticed
# at most this late.
POLL_WAIT_HINT_MAX_SECONDS = 300

# Non-terminal statuses shared by both batches and jobs. As soon as neither
# PENDING nor RUNNING jobs remain, the batch/job is considered terminal.
NON_TERMINAL_STATUSES = frozenset({"PENDING", "RUNNING"})

T = TypeVar("T")


def poll_status(
    fetcher: Callable[[], T],
    should_continue: Callable[[T], bool],
    wait_hint: Optional[Callable[[T], Optional[float]]] = None,
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
        wait_hint: Optional callable that receives the value returned by
            ``fetcher`` and returns a suggested wait in seconds, or None.
            Only consulted once the exponential wait has reached
            :data:`POLL_WAIT_MAX_SECONDS`; it can lengthen the wait up to
            :data:`POLL_WAIT_HINT_MAX_SECONDS`, never shorten it.

    Returns:
        The last value returned by ``fetcher`` (the terminal status
        payload).
    """
    backoff = tenacity.wait_exponential(
        multiplier=POLL_WAIT_INITIAL_SECONDS,
        max=POLL_WAIT_MAX_SECONDS,
    )

    def wait(retry_state: tenacity.RetryCallState) -> float:
        seconds = backoff(retry_state)
        if wait_hint is None or seconds < POLL_WAIT_MAX_SECONDS:
            return seconds

        assert retry_state.outcome is not None
        hint = wait_hint(retry_state.outcome.result())
        if hint is None:
            return seconds

        return max(seconds, min(hint, POLL_WAIT_HINT_MAX_SECONDS))

    retryer = tenacity.Retrying(
        wait=wait,
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


def batch_queue_wait_hint(
    fetch_batch: Callable[[], Dict[str, Any]],
) -> Callable[[Dict[str, Any]], Optional[float]]:
    """Build a ``wait_hint`` for :func:`poll_status` from a batch's queue info.

    While the polled batch or job is PENDING, fetches the batch, logs its queue
    position and estimated start, and suggests waiting half the estimated time
    before it starts. A job has no queue info of its own: it uses its batch's.

    When there is no estimate to wait on (always the case on emulators) or the
    batch has already started, the batch is fetched again at most once per
    :data:`POLL_WAIT_HINT_MAX_SECONDS`.

    Args:
        fetch_batch: Zero-argument callable returning the full payload of the
            polled batch, or of the polled job's batch.
    """
    next_fetch = 0.0

    def hint(status_data: Dict[str, Any]) -> Optional[float]:
        nonlocal next_fetch
        if status_data.get("status") != "PENDING" or time.monotonic() < next_fetch:
            return None

        batch = fetch_batch()
        position = batch.get("queue_position")
        estimate = batch.get("estimated_start_seconds")

        # A job stays PENDING while the jobs ahead of it in its started batch run.
        if batch.get("status") != "PENDING":
            next_fetch = time.monotonic() + POLL_WAIT_HINT_MAX_SECONDS
            return None

        if estimate is None:
            next_fetch = time.monotonic() + POLL_WAIT_HINT_MAX_SECONDS
            logger.info("Batch %s is at queue position %s", batch.get("id"), position)
            return None

        wait = min(
            max(float(estimate) / 2, POLL_WAIT_MAX_SECONDS), POLL_WAIT_HINT_MAX_SECONDS
        )
        logger.info(
            "Batch %s is at queue position %s, estimated start in %s, next check in %s",
            batch.get("id"),
            position,
            format_duration(estimate),
            format_duration(wait),
        )
        return wait

    return hint


def job_still_running(status_data: dict[str, Any]) -> bool:
    """Predicate: True while a job status is PENDING or RUNNING."""
    return status_data.get("status") in NON_TERMINAL_STATUSES
