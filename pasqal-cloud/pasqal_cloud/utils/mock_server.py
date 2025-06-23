import abc
import re
from typing import Any, Callable, Optional
from uuid import uuid4

import requests_mock

from pasqal_cloud.endpoints import Endpoints


class BaseMockServer(abc.ABC):
    """
    A mock server used as a replacement for the Pasqal HTTP server during testing.

    Intended use:
    ```py
    class MyMockServer(BaseMockServer):
        # Override any endpoints.
        def endpoint_post_batch(self, request: Any, context: Any) -> Any:
            ...

    with MyMockServer():
        client = Client()
        # Perform usual operations on the client
    ```
    """

    def __init__(self, endpoints: Optional[Endpoints] = None):
        self.mocker = requests_mock.Mocker()
        self.endpoints = endpoints
        if self.endpoints is None:
            self.endpoints = Endpoints()

        re_path_variables = re.compile("{([a-z_]+)}")

        # Install mocks for each endpoint.
        for method, relative_url, impl in [
            ("POST", "/api/v1/batches", self.endpoint_post_batch),
            ("GET", "/api/v2/batches/{batch_id}", self.endpoint_get_batch),
            (
                "GET",
                "/api/v1/jobs/{job_id}/results_link",
                self.endpoint_get_job_results,
            ),
            (
                "PATCH",
                "/api/v2/batches/{batch_id}/complete",
                self.endpoint_patch_complete_batch,
            ),
            (
                "PATCH",
                "/api/v2/batches/{batch_id}/cancel",
                self.endpoint_patch_cancel_batch,
            ),
            ("PATCH", "/api/v2/batches/cancel", self.endpoint_patch_cancel_batches),
            ("POST", "/api/v1/batches/{batch_id}/rebatch", self.endpoint_post_rebatch),
            ("GET", "/api/v2/jobs", self.endpoint_get_jobs),
            ("PATCH", "/api/v2/jobs/{job_id}/cancel", self.endpoint_cancel_job),
            (
                "PATCH",
                "/api/v2/batches/{batch_id}/cancel/jobs",
                self.endpoint_cancel_jobs,
            ),
            ("POST", "/api/v1/workloads", self.endpoint_post_workload),
            ("GET", "/api/v2/workloads/{workload_id}", self.endpoint_get_workload),
            (
                "PUT",
                "/api/v1/workloads/{workload_id}/cancel",
                self.endpoint_put_cancel_workload,
            ),
            ("GET", "/api/v1/devices/specs", self.endpoint_get_devices_specs),
            (
                "GET",
                "/api/v1/devices/public-specs",
                self.endpoint_get_devices_public_specs,
            ),
        ]:
            # Rewrite /foo/bar/{ga}/bu into /foo/bar/[^\]*/ga/bu.
            rewritten_relative_url = re.sub(
                pattern=re_path_variables,
                repl=lambda m: f"(?P<{m.group(1)}>[^\\\\]*)",
                string=relative_url,
            )
            escaped_full_url = re.escape(self.endpoints.core) + rewritten_relative_url
            compiled_full_url = re.compile(escaped_full_url)

            # Extract variables from path into `matches`.
            def wrapper(
                request: Any,
                context: Any,
                # Force capture from current loop iteration.
                impl: Callable[[Any, Any, list[str]], Any] = impl,
                compiled_full_url: re.Pattern[str] = compiled_full_url,
            ) -> Any:
                matches: list[str] = compiled_full_url.findall(request.url)
                return impl(request, context, matches)

            self.mocker.request(method=method, url=compiled_full_url, json=wrapper)
        self.mocker.request(
            method="POST",
            url="https://authenticate.pasqal.cloud/oauth/token",
            json=self.endpoint_post_authenticate_token,
        )

    def __enter__(self) -> None:
        self.mocker.__enter__()

    def __exit__(self, type: Any, value: Any, traceback: Any) -> None:
        self.mocker.__exit__(type, value, traceback)

    def endpoint_post_authenticate_token(self, request: Any, context: Any) -> Any:  # noqa: ARG002
        """
        Mock for POST https://authenticate.pasqal.cloud/oauth/token
        """
        token = "mock-token-" + str(uuid4())
        return {
            "expires-in": 100000000,
            "access_token": token,
        }

    def endpoint_post_batch(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for POST /api/v1/batches

        See https://docs.pasqal.com/cloud/api/core/operations/get_all_batches_api_v1_batches_get/ .
        """  # noqa: E501
        raise NotImplementedError

    def endpoint_get_batch(self, request: Any, context: Any, matches: list[str]) -> Any:
        """
        Mock for GET /api/v1/batches/{batch_id}

        See https://docs.pasqal.com/cloud/api/core/operations/get_batch_api_v2_batches__batch_id__get/ .
        """  # noqa: E501
        raise NotImplementedError

    def endpoint_get_job_results(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for GET /api/v1/jobs/{job_id}/results_link

        See https://docs.pasqal.com/cloud/api/core/operations/get_job_results_link_api_v1_jobs__job_id__results_link_get/
        """
        raise NotImplementedError

    def endpoint_patch_complete_batch(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for PATCH /api/v2/batches/{batch_id}/complete

        See https://docs.pasqal.com/cloud/api/core/operations/complete_batch_api_v2_batches__batch__id__complete_patch/
        """
        raise NotImplementedError

    def endpoint_patch_cancel_batch(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for PATCH /api/v2/batches/{batch_id}/cancel

        See https://docs.pasqal.com/cloud/api/core/operations/cancel_batch_api_v2_batches__batch__id__cancel_patch/
        """
        raise NotImplementedError

    def endpoint_patch_cancel_batches(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for PATCH /api/v2/batches/cancel

        See https://docs.pasqal.com/cloud/api/core/operations/cancel_batches_api_v1_batches_cancel_patch
        """
        raise NotImplementedError

    def endpoint_post_rebatch(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for POST /api/v2/batches/{batch_id}/rebatch

        See https://docs.pasqal.com/cloud/api/core/operations/rebatch_jobs_api_v1_batches__batch__id__rebatch_post
        """
        raise NotImplementedError

    def endpoint_get_jobs(self, request: Any, context: Any, matches: list[str]) -> Any:
        """
        Mock for GET /api/v2/jobs

        See https://docs.pasqal.com/cloud/api/core/operations/get_jobs_api_v2_jobs_get
        """
        raise NotImplementedError

    def endpoint_get_batches(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for GET /api/v1/batches

        See https://docs.pasqal.com/cloud/api/core/operations/get_all_batches_api_v1_batches_get
        """
        raise NotImplementedError

    def endpoint_add_jobs(self, request: Any, context: Any, matches: list[str]) -> Any:
        """
        Mock for POST /api/v2/batches/{batch_id}/jobs

        See https://docs.pasqal.com/cloud/api/core/operations/add_jobs_api_v2_batches__batch__id__jobs_post
        """
        raise NotImplementedError

    def endpoint_cancel_job(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for PATCH /api/v2/jobs/{job_id}/cancel

        See https://docs.pasqal.com/cloud/api/core/operations/cancel_job_api_v2_jobs__job_id__cancel_patch
        """
        raise NotImplementedError

    def endpoint_cancel_jobs(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for PATCH /api/v2/batches/{batch_id}/cancel/jobs

        See https://docs.pasqal.com/cloud/api/core/operations/cancel_jobs_api_v2_batches__batch__id__cancel_jobs_patch
        """
        raise NotImplementedError

    def endpoint_post_workload(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for POST /api/v1/workloads

        See https://docs.pasqal.com/cloud/api/core/operations/create_workload_api_v1_workloads_post
        """
        raise NotImplementedError

    def endpoint_get_workload(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for GET /api/v1/workloads/{workload_id}

        See https://docs.pasqal.com/cloud/api/core/operations/get_workload_api_v2_workloads__workload_id__get
        """
        raise NotImplementedError

    def endpoint_put_cancel_workload(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for PUT /api/v1/workloads/{workload_id}/cancel

        See https://docs.pasqal.com/cloud/api/core/operations/cancel_workload_api_v1_workloads__workload_id__cancel_put
        """
        raise NotImplementedError

    def endpoint_get_devices_specs(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for GET /api/v1/devices/specs

        See https://docs.pasqal.com/cloud/api/core/operations/get_all_devices_api_v1_devices_get
        """
        raise NotImplementedError

    def endpoint_get_devices_public_specs(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for GET /api/v1/devices/public-specs

        See https://docs.pasqal.com/cloud/api/core/operations/get_public_device_specs_api_v1_devices_public_specs_get
        """
        raise NotImplementedError

    def endpoint_patch_batch_tags(
        self, request: Any, context: Any, matches: list[str]
    ) -> Any:
        """
        Mock for PATCH /api/v1/batches/{batch_id}/tags

        See https://docs.pasqal.com/cloud/api/core/operations/set_batch_tags_api_v1_batches__batch_id__tags_patch
        """
        raise NotImplementedError
