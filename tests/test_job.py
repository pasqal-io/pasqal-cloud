from datetime import datetime
from typing import Any, Dict, List, Union
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
import requests_mock

from pasqal_cloud import (
    CancelJobFilters,
    Job,
    JobCancellingError,
    JobFetchingError,
    JobFilters,
    PaginatedResponse,
    PaginationParams,
    SDK,
)
from pasqal_cloud.utils.constants import JobStatus
from pasqal_cloud.utils.responses import JobCancellationResponse
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess
from tests.utils import build_query_params


class TestJob:
    @pytest.fixture(autouse=True)
    @patch(
        "pasqal_cloud.client.Auth0TokenProvider",
        FakeAuth0AuthenticationSuccess,
    )
    def _init_sdk(self):
        self.sdk = SDK(
            username="me@test.com",
            password="password",
            project_id=str(uuid4()),
        )
        self.pulser_sequence = "pulser_test_sequence"
        self.batch_id = "00000000-0000-0000-0000-000000000001"
        self.job_id = "00000000-0000-0000-0000-000000022010"
        self.n_job_runs = 50
        self.job_variables = {
            "Omega_max": 14.4,
            "last_target": "q1",
            "ts": [200, 500],
        }
        self.simple_job_args = {
            "runs": self.n_job_runs,
            "variables": self.job_variables,
        }
        self.job_result = {"1001": 12, "0110": 35, "1111": 1}
        self.job_full_result = {
            "counter": {"1001": 12, "0110": 35, "1111": 1},
            "raw": ["1001", "1001", "0110", "1001", "0110"],
        }

    @pytest.mark.usefixtures("mock_request")
    def test_get_job(self, job: Job):
        """
        Asserting the anticipated object is returned with
        the mocked values when using SDK methods.
        """
        job_requested = self.sdk.get_job(job.id)
        assert job_requested.id == job.id

    def test_get_job_error(
        self, job, mock_request_exception: requests_mock.mocker.Mocker
    ):
        """
        When attempting to execute get_job, we receive an exception
        which prevents any values being returned.
        We then assert all the correct methods and urls were used.
        """
        with pytest.raises(JobFetchingError):
            _ = self.sdk.get_job(job.id)
        assert mock_request_exception.last_request.method == "GET"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}"
            f"/api/v2/jobs/{job.id}"
        )

    def test_cancel_job_self(self, mock_request: requests_mock.mocker.Mocker, job: Job):
        """
        After cancelling a job, we can assert that the status is CANCELED as expected
        and that the correct methods and URLS were used.
        """
        job.cancel()
        assert job.status == "CANCELED"
        assert mock_request.last_request.method == "PATCH"
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v2/jobs/{self.job_id}/cancel"
        )

    def test_cancel_job_self_error(
        self, mock_request_exception: requests_mock.mocker.Mocker, job: Job
    ):
        """
        When trying to cancel a job, we assert that an exception is raised
        while confirming the expected HTTP methods and URLs are used and that
        the job status is still PENDING.
        """
        with pytest.raises(JobCancellingError):
            job.cancel()
        assert job.status == "PENDING"
        assert mock_request_exception.last_request.method == "PATCH"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v2/jobs/{self.job_id}/cancel"
        )

    def test_cancel_job_sdk(self, mock_request: requests_mock.mocker.Mocker):
        """
        After successfully executing the .cancel_job method,
        we further validate the response object is as anticipated,
        while confirming the expected HTTP methods and URLs are used.
        """
        client_rsp = self.sdk.cancel_job(self.job_id)
        assert type(client_rsp) == Job
        assert client_rsp.status == "CANCELED"
        assert mock_request.last_request.method == "PATCH"
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v2/jobs/{self.job_id}/cancel"
        )

    def test_cancel_job_sdk_error(
        self, mock_request_exception: requests_mock.mocker.Mocker
    ):
        """
        When trying to cancel a job, we assert that an exception is raised
        while confirming the expected HTTP methods and URLs are used.
        """
        with pytest.raises(JobCancellingError):
            _ = self.sdk.cancel_job(self.job_id)
        assert mock_request_exception.last_request.method == "PATCH"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v2/jobs/{self.job_id}/cancel"
        )

    def test_job_instantiation_with_extra_field(self, job):
        """Instantiating a job with an extra field should not raise an error.

        This enables us to add new fields in the API response on the jobs endpoint
        without breaking compatibility for users with old versions of the SDK where
        the field is not present in the Job class.
        """
        job_dict = job.model_dump()  # job data expected by the SDK
        # We add an extra field to mimick the API exposing new values to the user
        job_dict["new_field"] = "any_value"

        new_job = Job(**job_dict)  # this should raise no error
        assert (
            new_job.new_field == "any_value"
        )  # The new value should be stored regardless

    @pytest.mark.parametrize(
        "filters",
        [
            # No filters provided
            None,
            # Empty object
            JobFilters(),
            # Single UUID for id
            JobFilters(id=UUID(int=0x1)),
            # List of UUIDs for id
            JobFilters(id=[UUID(int=0x1), UUID(int=0x2)]),
            # Single string UUID for id
            JobFilters(id=str(UUID(int=0x1))),
            # List of string UUIDs for id
            JobFilters(id=[str(UUID(int=0x1)), str(UUID(int=0x2))]),
            # Single UUID for project_id
            JobFilters(project_id=UUID(int=0x1)),
            # List of UUIDs for project_id
            JobFilters(project_id=[UUID(int=0x1), UUID(int=0x2)]),
            # Single string UUID for project_id
            JobFilters(project_id=str(UUID(int=0x1))),
            # List of string UUIDs for project_id
            JobFilters(project_id=[str(UUID(int=0x1)), str(UUID(int=0x2))]),
            # Single user_id as string
            JobFilters(user_id="1"),
            # List of user_ids as strings
            JobFilters(user_id=["1", "2"]),
            # Single UUID for batch_id
            JobFilters(batch_id=UUID(int=0x2)),
            # List of UUIDs for batch_id
            JobFilters(batch_id=[UUID(int=0x1), UUID(int=0x2)]),
            # Single string UUID for batch_id
            JobFilters(batch_id=str(UUID(int=0x1))),
            # List of string UUIDs for batch_id
            JobFilters(batch_id=[str(UUID(int=0x1)), str(UUID(int=0x2))]),
            # Single status
            JobFilters(status=JobStatus.DONE),
            # List of statuses
            JobFilters(status=[JobStatus.DONE, JobStatus.PENDING]),
            # Minimum runs
            JobFilters(min_runs=10),
            # Maximum runs
            JobFilters(max_runs=20),
            # Errors flag
            JobFilters(errors=True),
            # Start date
            JobFilters(start_date=datetime(2023, 1, 1)),
            # End date
            JobFilters(end_date=datetime(2023, 1, 1)),
            # Combined
            JobFilters(
                id=[UUID(int=0x1), str(UUID(int=0x2))],
                project_id=[UUID(int=0x1), UUID(int=0x2)],
                user_id=["1", "2"],
                batch_id=[UUID(int=0x1), UUID(int=0x2)],
                status=JobStatus.DONE,
                min_runs=10,
                max_runs=20,
                errors=True,
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 1),
            ),
        ],
    )
    def test_get_jobs_with_filters_success(
        self,
        mock_request: Any,
        filters: Union[JobFilters, None],
    ):
        """
        As a user using the SDK with proper credentials,
        I can get a list of jobs with specific filters.
        The resulting request will retrieve the jobs that match the filters.
        """
        response = self.sdk.get_jobs(filters=filters)
        assert isinstance(response, PaginatedResponse)
        assert isinstance(response.total, int)
        assert isinstance(response.results, List)
        for item in response.results:
            assert isinstance(item, Job)
        assert mock_request.last_request.method == "GET"

        # Convert filters to the appropriate format for query parameters
        query_params = build_query_params(
            filters.model_dump(exclude_unset=True) if filters is not None else None,
            PaginationParams().model_dump(),
        )
        # Check that the correct url was requested with query params
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v2/jobs{query_params}"
        )

    @pytest.mark.parametrize(
        "pagination",
        [
            None,
            PaginationParams(),
            PaginationParams(limit=1),
            PaginationParams(offset=50, limit=1),
            PaginationParams(offset=100, limit=100),
            PaginationParams(offset=1000, limit=100),
        ],
    )
    def test_get_jobs_with_pagination_success(
        self, mock_request: Any, pagination: PaginationParams
    ):
        """
        As a user using the SDK with proper credentials,
        I can get a list of jobs with pagination parameters.
        The resulting request will retrieve the jobs that match
        the pagination parameters.
        """
        response = self.sdk.get_jobs(pagination_params=pagination)
        assert isinstance(response, PaginatedResponse)
        assert isinstance(response.total, int)
        assert isinstance(response.results, List)
        for item in response.results:
            assert isinstance(item, Job)
        assert mock_request.last_request.method == "GET"

        # Convert filters to the appropriate format for query parameters
        query_params = build_query_params(
            pagination_params=(
                pagination.model_dump()
                if pagination
                else PaginationParams().model_dump()
            )
        )
        # Check that the correct url was requested with query params
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v2/jobs{query_params}"
        )

    def test_get_jobs_sdk_error(
        self, mock_request_exception: requests_mock.mocker.Mocker
    ):
        """
        As a user using the SDK with proper credentials,
        if my request for getting jobs returns a status code different from 200,
        I am faced with the JobFetchingError.
        """
        with pytest.raises(JobFetchingError):
            _ = self.sdk.get_jobs()
        assert mock_request_exception.last_request.method == "GET"
        assert (
            mock_request_exception.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v2/jobs?offset=0&limit=100"
        )

    def test_get_jobs_raises_value_error_on_invalid_filters(self):
        """
        As a user using the SDK with proper credentials,
        if I pass a dictionary instead of JobFilters, a ValueError should be raised.
        """
        with pytest.raises(
            ValueError, match="Filters needs to be a JobFilters instance"
        ):
            _ = self.sdk.get_jobs(filters={"min_runs": 10})

    def test_get_jobs_raises_value_error_on_invalid_pagination_params(self):
        """
        As a user using the SDK with proper credentials,
        if I pass a dictionary instead of PaginationParams, a ValueError should
        be raised.
        """
        with pytest.raises(
            ValueError,
            match="Pagination parameters needs to be a PaginationParams instance",
        ):
            _ = self.sdk.get_jobs(pagination_params={"offset": 100, "limit": 100})

    def test_get_jobs_raises_value_error_on_invalid_value_for_offset(self):
        """
        As a user using the SDK with proper credentials,
        if I pass a 'from_index' inferior to 0, it raises a ValueError to the user.
        """
        with pytest.raises(
            ValueError, match="Input should be greater than or equal to 0"
        ):
            _ = self.sdk.get_jobs(pagination_params=PaginationParams(offset=-1))

    @pytest.mark.parametrize(
        "limit",
        [-1, 0, 101],
    )
    def test_get_jobs_raises_value_error_on_invalid_value_for_limit(self, limit: int):
        """
        As a user using the SDK with proper credentials,
        if I pass a 'limit' inferior to 1 or superior to 100,
        it raises a ValueError to the user.
        """
        with pytest.raises(ValueError, match="limit"):
            _ = self.sdk.get_jobs(pagination_params=PaginationParams(limit=limit))

    @pytest.mark.parametrize(
        "filters",
        [
            # No filters provided
            None,
            # Empty object
            CancelJobFilters(),
            # Single UUID for id
            CancelJobFilters(id=UUID(int=0x1)),
            # List of UUIDs for id
            CancelJobFilters(id=[UUID(int=0x1), UUID(int=0x2)]),
            # Single string UUID for id
            CancelJobFilters(id=str(UUID(int=0x1))),
            # List of string UUIDs for id
            CancelJobFilters(id=[str(UUID(int=0x1)), str(UUID(int=0x2))]),
            # Minimum runs
            CancelJobFilters(min_runs=10),
            # Maximum runs
            CancelJobFilters(max_runs=20),
            # Start date
            CancelJobFilters(start_date=datetime(2023, 1, 1)),
            # End date
            CancelJobFilters(end_date=datetime(2023, 1, 1)),
            # Combined
            CancelJobFilters(
                id=[UUID(int=0x1), str(UUID(int=0x2))],
                min_runs=10,
                max_runs=20,
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 1),
            ),
        ],
    )
    def test_cancel_jobs_success(
        self,
        mock_request: Any,
        filters: Union[CancelJobFilters, None],
    ):
        """
        As a user using the SDK with proper credentials,
        I can cancel of a group of jobs from a batch with specific filters.
        The resulting request will retrieve the jobs that were cancelled and
        the errors for those that could not be cancelled.
        """
        response = self.sdk.cancel_jobs(batch_id=UUID(int=0x1), filters=filters)
        assert isinstance(response, JobCancellationResponse)

        for item in response.jobs:
            assert isinstance(item, Job)

        for k, v in response.errors.items():
            assert isinstance(k, UUID)
            assert isinstance(v, str)

        assert isinstance(response.errors, Dict)

        assert mock_request.last_request.method == "PATCH"

        # Convert filters to the appropriate format for query parameters
        query_params = build_query_params(
            filters.model_dump(exclude_unset=True) if filters is not None else None,
        )
        # Check that the correct url was requested with query params
        assert (
            mock_request.last_request.url
            == f"{self.sdk._client.endpoints.core}/api/v2/batches/{UUID(int=0x1)}"
            f"/cancel/jobs{query_params}"
        )

    def test_cancel_jobs_raises_value_error_on_invalid_filters(self):
        """
        As a user using the SDK with proper credentials,
        if I pass a dictionary instead of CancelJobFilters, a ValueError should
        be raised.
        """
        with pytest.raises(
            ValueError, match="Filters needs to be a CancelJobFilters instance"
        ):
            _ = self.sdk.cancel_jobs(batch_id=UUID(int=0x1), filters={"min_runs": 10})
