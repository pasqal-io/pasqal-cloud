from __future__ import annotations

import os
from typing import Any, Dict

import pasqal_cloud
from pasqal_cloud.authentication import TokenProvider
from pasqal_cloud.client import Client

from pulser_pasqal.pasqal_cloud import PasqalCloud


class OvhClient(Client):
    """OVH specific client that uses different API endpoints."""

    @property
    def project_id(self) -> str:
        """
        Override property of class Client to prevent
        ValueError to be raised as OvhClient does not need
        a project_id
        """
        return ""

    @project_id.setter
    def project_id(self, _project_id: str) -> None:
        self._project_id = ""

    def _get_api_urls(self) -> Dict[str, str]:
        base_url = f"{self.endpoints.core}/api/v1/third-party-access/ovh"
        return {
            # Batch endpoints
            "send_batch": f"{base_url}/batches",
            "get_batch": f"{base_url}/batches/{{batch_id}}",
            # Job endpoints
            "get_jobs": f"{base_url}/jobs",
            "get_job_results_link": f"{base_url}/jobs/{{job_id}}/results_link",
            # Device endpoints
            "get_public_devices_specs": f"{self.endpoints.core}"
            f"/api/v1/devices/public-specs",
        }

    @property
    def unknown_endpoint_message(self) -> str:
        return (
            "Endpoint '{endpoint}' does not exist or "
            "is not supported by the OVH client."
        )

    def get_device_specs_dict(self) -> Dict[str, str]:
        # We cannot just swap the endpoint with `get_public_device_specs()`,
        # because `get_device_specs` returns a dict (device : spec),
        # while `get_public_device_specs` returns a list of devices
        return self.get_public_device_specs()


class MissingEnvironmentVariableError(RuntimeError):
    pass


class OVHConnection(PasqalCloud):
    """PasqalCloud connection designed for OVH users.

    This connection class enables OVH users to access Pasqal Cloud services.
    Authentication is handled via a token that must be provided
    through the PASQAL_PULSER_ACCESS_TOKEN environment variable.

    Raises:
       MissingEnvironmentVariableError: If PASQAL_PULSER_ACCESS_TOKEN
       environment variable is not set.
    """

    def __init__(self, **kwargs: Any) -> None:
        try:
            token = os.environ["PASQAL_PULSER_ACCESS_TOKEN"]
        except KeyError:
            raise MissingEnvironmentVariableError(
                "Missing PASQAL_PULSER_ACCESS_TOKEN environment variable"
            )

        class OvhTokenProvider(TokenProvider):
            def get_token(self) -> str:
                return token

        self._sdk_connection = pasqal_cloud.SDK(
            token_provider=OvhTokenProvider(), client_class=OvhClient, **kwargs
        )

    def supports_open_batch(self) -> bool:
        """Flag to confirm this class cannot support creating an open batch."""
        return False
