from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest

from pasqal_cloud import SDK
from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess


class TestDeprecation:
    # set deprecation to 10 day after today (in warning window)
    @patch(
        "pasqal_cloud.deprecation_date",
        (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
    )
    @patch(
        "pasqal_cloud.client.Auth0TokenProvider",
        FakeAuth0AuthenticationSuccess,
    )
    def test_soon_to_be_deprecated(self):
        # Set deprecation_date to be 10 days from now (within the warning period)
        with pytest.warns(DeprecationWarning, match="will be deprecated on "):
            _ = SDK(
                username="me@test.com",
                password="password",
                project_id=str(uuid4()),
            )

    # set deprecation to 1 day before today
    @patch(
        "pasqal_cloud.deprecation_date",
        (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
    )
    @patch(
        "pasqal_cloud.client.Auth0TokenProvider",
        FakeAuth0AuthenticationSuccess,
    )
    def test_already_deprecated(self):
        with pytest.warns(DeprecationWarning, match="is no longer supported."):
            _ = SDK(
                username="me@test.com",
                password="password",
                project_id=str(uuid4()),
            )
