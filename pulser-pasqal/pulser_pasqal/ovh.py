import os

import pasqal_cloud
from pasqal_cloud import TokenProvider
from pasqal_cloud.ovh_client import OvhClient

from pulser_pasqal.pasqal_cloud import PasqalCloud


class OVHConnection(PasqalCloud):
    """PasqalCloud connection designed for OVH users.

    This connection class enables OVH users to access Pasqal Cloud services.
    Authentication is handled via a delegated token that must be provided
    through the PASQAL_DELEGATED_TOKEN environment variable.

    Raises:
       EnvironmentError: If PASQAL_DELEGATED_TOKEN environment variable is not set.
    """

    def __init__(self):
        token = os.environ.get("PASQAL_DELEGATED_TOKEN")
        if not token:
            raise EnvironmentError(
                "Missing PASQAL_DELEGATED_TOKEN environment variable"
            )

        class OvhTokenProvider(TokenProvider):
            def get_token(self):
                return token

        self._sdk_connection = pasqal_cloud.SDK(
            token_provider=OvhTokenProvider(), client_class=OvhClient
        )

    def supports_open_batch(self) -> bool:
        """Flag to confirm this class cannot support creating an open batch."""
        return False
