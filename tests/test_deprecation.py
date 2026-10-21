import warnings
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from pasqal_cloud import endpoints
from pasqal_cloud.authentication import (
    Auth0TokenProvider,
    InsecureAuth0TokenProvider,
    PasswordGrantTokenProvider,
)
from pasqal_cloud.endpoints import (
    Auth0Conf,
    Endpoints,
    KSA_CORE_API_URL,
    SA_KEYCLOAK_TOKEN_ENDPOINT,
    TokenProviderConf,
)
from pasqal_cloud.pasqal_cloud_client import PasqalCloudClient

from tests.test_doubles.authentication import FakeAuth0AuthenticationSuccess


class TestDeprecation:
    # set deprecation to 10 day after today (in warning window)
    @patch(
        "pasqal_cloud.pasqal_cloud_client.deprecation_date",
        (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
    )
    @patch(
        "pasqal_cloud.http_client.PasswordGrantTokenProvider",
        FakeAuth0AuthenticationSuccess,
    )
    def test_soon_to_be_deprecated(self):
        # Set deprecation_date to be 10 days from now (within the warning period)
        with pytest.warns(DeprecationWarning, match="will be deprecated on "):
            _ = PasqalCloudClient(
                username="me@test.com",
                password="password",
                project_id=str(uuid4()),
            )

    # set deprecation to 1 day before today
    @patch(
        "pasqal_cloud.pasqal_cloud_client.deprecation_date",
        (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
    )
    @patch(
        "pasqal_cloud.http_client.PasswordGrantTokenProvider",
        FakeAuth0AuthenticationSuccess,
    )
    def test_already_deprecated(self):
        with pytest.warns(DeprecationWarning, match="is no longer supported."):
            _ = PasqalCloudClient(
                username="me@test.com",
                password="password",
                project_id=str(uuid4()),
            )


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("endpoints", Endpoints()),
        ("auth0", Auth0Conf()),
        ("auth_config", TokenProviderConf._from_auth0_config(Auth0Conf())),
    ],
)
def test_deprecated_constructor_args(name, value):
    with pytest.warns(FutureWarning, match=f"`{name}` is deprecated") as record:
        PasqalCloudClient(project_id=str(uuid4()), **{name: value})

    # Points to the caller, not to the SDK internals.
    assert record[0].filename == __file__


def test_no_future_warning_by_default():
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        PasqalCloudClient(project_id=str(uuid4()))


def test_endpoints_from_region_is_deprecated():
    with pytest.warns(FutureWarning, match=r"from_region\(\) is deprecated"):
        assert Endpoints.from_region("sa").core == KSA_CORE_API_URL


def test_token_provider_conf_from_region_is_deprecated():
    with pytest.warns(FutureWarning, match=r"from_region\(\) is deprecated"):
        conf = TokenProviderConf.from_region("sa")

    assert conf.token_endpoint == SA_KEYCLOAK_TOKEN_ENDPOINT


@pytest.mark.parametrize("name", ["PASQAL_ENDPOINTS", "AUTH0_CONFIG", "AUTH_CONFIG"])
def test_preset_configs_are_deprecated(name):
    with pytest.warns(FutureWarning, match=f"`{name}` is deprecated"):
        assert getattr(endpoints, name)


@pytest.mark.parametrize(
    "statement",
    [
        "from pasqal_cloud.endpoints import PASQAL_ENDPOINTS as value",
        "from pasqal_cloud.endpoints import *; value = AUTH_CONFIG",
        "from pasqal_cloud import AUTH0_CONFIG as value",
        "import pasqal_cloud; value = pasqal_cloud.PASQAL_ENDPOINTS",
    ],
)
def test_preset_configs_import_forms(statement):
    namespace: dict = {}
    with pytest.warns(FutureWarning, match="is deprecated"):
        exec(statement, namespace)

    assert namespace["value"]


def test_token_provider_conf_from_auth0_config_is_deprecated():
    with pytest.warns(FutureWarning, match=r"from_auth0_config\(\) is deprecated"):
        TokenProviderConf.from_auth0_config(Auth0Conf())


@pytest.mark.parametrize("cls", [Auth0TokenProvider, InsecureAuth0TokenProvider])
def test_auth0_token_providers_are_deprecated(cls):
    with (
        patch.object(PasswordGrantTokenProvider, "get_token"),
        pytest.warns(FutureWarning, match=f"{cls.__name__} is deprecated") as record,
    ):
        cls("me@test.com", "password", Auth0Conf())

    assert record[0].filename == __file__
