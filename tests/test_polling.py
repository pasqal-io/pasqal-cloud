from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from pasqal_cloud.utils.duration import format_duration
from pasqal_cloud.utils.polling import (
    batch_queue_wait_hint,
    batch_still_running,
    job_still_running,
    NON_TERMINAL_STATUSES,
    poll_status,
)


def _waits_until_done(polls: int, hint: Any) -> List[float]:
    """Poll a fake fetcher that is terminal after `polls` calls, return the waits."""
    results = iter([True] * (polls - 1) + [False])
    with patch("time.sleep") as sleep:
        poll_status(
            fetcher=lambda: next(results),
            should_continue=lambda still_running: still_running,
            wait_hint=lambda _: hint,
        )
    return [call.args[0] for call in sleep.call_args_list]


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (59.9, "59 s"),
        (60, "1 min"),
        (5 * 60 + 30, "5 min"),
        (119 * 60 + 59, "1 h 59 min"),
        (2 * 3600 + 5, "2 h"),
        (86400 + 3 * 60, "1 day"),
        (86400 + 3 * 3600 + 20 * 60, "1 day 3 h"),
        (13 * 86400 + 2 * 3600, "13 days 2 h"),
    ],
)
def test_format_duration(seconds: float, expected: str) -> None:
    """Durations are truncated to seconds under a minute, to minutes under a
    day, then to hours."""
    assert format_duration(seconds) == expected


class TestPollStatusWaitHint:
    def test_hint_only_applies_once_backoff_is_capped(self) -> None:
        """The hint replaces the wait only once the backoff reaches its cap."""
        assert _waits_until_done(polls=7, hint=200) == [2, 4, 8, 16, 200, 200]

    def test_hint_is_capped(self) -> None:
        """A long hint never makes the wait exceed 5 min."""
        assert _waits_until_done(polls=6, hint=10_000)[-1] == 300

    @pytest.mark.parametrize("hint", [None, 5])
    def test_hint_never_shortens_backoff(self, hint: Any) -> None:
        """No hint, or one shorter than the backoff, keeps the backoff."""
        assert _waits_until_done(polls=6, hint=hint) == [2, 4, 8, 16, 30]


class TestBatchQueueWaitHint:
    @staticmethod
    def _hint(batch: Dict[str, Any], status: str = "PENDING") -> Any:
        return batch_queue_wait_hint(lambda: {"status": "PENDING", **batch})(
            {"status": status}
        )

    def test_queued_qpu_batch_waits_half_the_estimate(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A queued QPU batch is checked again after half its estimated start,
        and its queue position and estimate are logged."""
        with caplog.at_level("INFO", logger="pasqal_cloud"):
            hint = self._hint(
                {"id": "batch-1", "queue_position": 4, "estimated_start_seconds": 360}
            )

        assert hint == 180
        assert caplog.messages == [
            "Batch batch-1 is at queue position 4, estimated start in 6 min, "
            "next check in 3 min"
        ]

    @pytest.mark.parametrize(
        ("estimate", "expected_wait"),
        [
            (20, 30),
            (10_000, 300),
        ],
    )
    def test_queued_qpu_batch_wait_stays_within_polling_bounds(
        self, estimate: int, expected_wait: float
    ) -> None:
        """The wait derived from the estimate stays between 30 s and 5 min."""
        hint = self._hint({"queue_position": 1, "estimated_start_seconds": estimate})

        assert hint == expected_wait

    def test_queued_batch_without_estimate_is_fetched_every_5_min(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A queued batch without an estimate, as on emulators, is refetched every
        5 min to log its queue position, and its estimate once it has one."""
        no_estimate = {
            "status": "PENDING",
            "queue_position": 4,
            "estimated_start_seconds": None,
        }
        batches = iter(
            [
                no_estimate,
                {**no_estimate, "queue_position": 2, "estimated_start_seconds": 360},
            ]
        )
        hint = batch_queue_wait_hint(lambda: next(batches))
        pending = {"status": "PENDING"}

        with (
            patch("time.monotonic") as clock,
            caplog.at_level("INFO", logger="pasqal_cloud"),
        ):
            clock.return_value = 1000.0
            first = hint(pending)

            clock.return_value = 1299.0
            before_5_min = hint(pending)

            clock.return_value = 1300.0
            after_5_min = hint(pending)

        assert (first, before_5_min, after_5_min) == (None, None, 180)
        assert "queue position 4" in caplog.text
        assert "queue position 2" in caplog.text

    def test_started_batch_is_not_fetched(self) -> None:
        """A batch that is no longer PENDING has no queue info to fetch."""

        def fetch_batch() -> Dict[str, Any]:
            raise AssertionError("full batch fetched for a running batch")

        hint = batch_queue_wait_hint(fetch_batch)({"status": "RUNNING"})

        assert hint is None

    def test_pending_job_of_started_batch_is_fetched_every_5_min(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A PENDING job of a started batch gives no hint, its batch is refetched
        at most every 5 min, and no queue position is logged."""
        running = {
            "status": "RUNNING",
            "queue_position": 1,
            "estimated_start_seconds": 0,
        }
        fetches = []

        def fetch_batch() -> Dict[str, Any]:
            fetches.append(running)
            return running

        hint = batch_queue_wait_hint(fetch_batch)
        pending = {"status": "PENDING"}

        with (
            patch("time.monotonic") as clock,
            caplog.at_level("INFO", logger="pasqal_cloud"),
        ):
            hints = []
            for now in (1000.0, 1299.0, 1300.0):
                clock.return_value = now
                hints.append(hint(pending))

        assert hints == [None] * 3
        assert len(fetches) == 2
        assert "queue position" not in caplog.text


class TestPredicates:
    @pytest.mark.parametrize(
        ("counts", "expected"),
        [
            ({"PENDING": 1}, True),
            ({"RUNNING": 3}, True),
            ({"PENDING": 1, "RUNNING": 2, "DONE": 5}, True),
            ({"PENDING": 0, "RUNNING": 0, "DONE": 5}, False),
            ({"DONE": 5}, False),
            ({"DONE": 3, "ERROR": 1, "CANCELED": 1, "TIMED_OUT": 1}, False),
            ({}, False),
        ],
    )
    def test_batch_still_running_reads_jobs_count_per_status(
        self, counts: Dict[str, int], expected: bool
    ) -> None:
        assert batch_still_running({"jobs_count_per_status": counts}) is expected

    def test_batch_still_running_handles_missing_jobs_count(self) -> None:
        assert batch_still_running({}) is False
        assert batch_still_running({"jobs_count_per_status": None}) is False

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            ("PENDING", True),
            ("RUNNING", True),
            ("DONE", False),
            ("ERROR", False),
            ("CANCELED", False),
            ("TIMED_OUT", False),
        ],
    )
    def test_job_still_running(self, status: str, expected: bool) -> None:
        assert job_still_running({"status": status}) is expected

    def test_job_still_running_handles_missing_status(self) -> None:
        assert job_still_running({}) is False

    def test_non_terminal_statuses_matches_predicate_semantics(self) -> None:
        assert frozenset({"PENDING", "RUNNING"}) == NON_TERMINAL_STATUSES
