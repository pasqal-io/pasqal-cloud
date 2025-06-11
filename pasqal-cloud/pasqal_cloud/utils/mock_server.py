import abc
from typing import Any

import requests_mock

from pasqal_cloud.endpoints import Endpoints


class BaseMockServer(abc.ABC):
    """
    A mock server used as a replacement for the Pasqal HTTP server during testing.

    Intended use:
    ```py
    class MyMockServer(BaseMockServer):
        ...

    with MyMockServer():
        client = Client()
        # ... perform usual operations on the client
    ```
    """

    def __init__(self, endpoints: Endpoints | None = None):
        self.mocker = requests_mock.Mocker()
        self.endpoints = endpoints
        if self.endpoints is None:
            self.endpoints = Endpoints()

        # Install mocks for each endpoint.
        self.mocker.post(self.endpoints.core + "/api/v1/batches", text=self.post_batch)
        self.mocker.get(
            self.endpoints.core + "/api/v1/batches/{batch_id}", text=self.get_batch
        )
        self.mocker.get(self.endpoints.core + "/api/v2/jobs", text=self.get_jobs)
        self.mocker.get(
            self.endpoints.core + "/api/v1/jobs/{job_id}/results_link",
            text=self.get_job_results,
        )

    @abc.abstractmethod
    def post_batch(self, request: Any, context: Any) -> Any:
        """
        Mock for POST /api/v1/batches
        """
        ...

    @abc.abstractmethod
    def get_batch(self, request: Any, context: Any) -> Any:
        """
        Mock for GET /api/v1/batches/{batch_id}
        """
        ...

    @abc.abstractmethod
    def get_jobs(self, request: Any, context: Any) -> Any:
        """
        Mock for GET /api/v2/jobs
        """
        ...

    @abc.abstractmethod
    def get_job_results(self, request: Any, context: Any) -> Any:
        """
        Mock for GET /api/v1/jobs/{job_id}/results_link
        """
        ...
