import time
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from pasqal_cloud.utils.polling import (
    NON_TERMINAL_STATUSES,
    batch_still_running,
    job_still_running,
)


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
        assert NON_TERMINAL_STATUSES == frozenset({"PENDING", "RUNNING"})
