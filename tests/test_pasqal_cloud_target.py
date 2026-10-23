from itertools import product

import pytest
from pasqal_cloud.authentication import password_grant_config
from pasqal_cloud.cli import main
from pasqal_cloud.endpoints import (
    AUTH0_TOKEN_PROVIDER_GRANT_TYPE,
    DEPLOYMENTS,
    ENVS,
    KEYCLOAK_REALM,
    REALM,
    REGIONS,
    resolve_pasqal_cloud_target,
    TokenProviderConf,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("PASQAL_CLOUD_REGION", raising=False)
    monkeypatch.delenv("PASQAL_CLOUD_ENV", raising=False)


def test_defaults():
    target = resolve_pasqal_cloud_target()
    assert (target.region, target.env) == ("fr", "prod")
    assert target.deployment == DEPLOYMENTS[("fr", "prod")]


def test_env_vars(monkeypatch):
    monkeypatch.setenv("PASQAL_CLOUD_REGION", "sa")
    monkeypatch.setenv("PASQAL_CLOUD_ENV", "preprod")
    target = resolve_pasqal_cloud_target()
    assert (target.region, target.env) == ("sa", "preprod")


@pytest.mark.parametrize(("region", "env"), product(REGIONS, ENVS))
def test_every_target_resolves(monkeypatch, region, env):
    monkeypatch.setenv("PASQAL_CLOUD_ENV", env)

    target = resolve_pasqal_cloud_target(region)

    assert (target.region, target.env) == (region, env)


def test_flag_wins_over_env_var(monkeypatch):
    monkeypatch.setenv("PASQAL_CLOUD_REGION", "sa")
    target = resolve_pasqal_cloud_target("fr")
    assert target.region == "fr"


@pytest.mark.parametrize(
    ("var", "value"), [("PASQAL_CLOUD_REGION", "us"), ("PASQAL_CLOUD_ENV", "staging")]
)
def test_invalid_values_raise(monkeypatch, var, value):
    monkeypatch.setenv(var, value)
    with pytest.raises(
        ValueError, match=rf"Invalid \${var}={value!r}, expected one of"
    ):
        resolve_pasqal_cloud_target()


def test_cli_reports_invalid_env(monkeypatch, capsys):
    monkeypatch.setenv("PASQAL_CLOUD_ENV", "staging")
    assert main(["auth", "status"]) == 1
    assert "prod, preprod, dev" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("region", "env", "realm", "grant_type"),
    [
        ("fr", "dev", REALM, AUTH0_TOKEN_PROVIDER_GRANT_TYPE),
        ("sa", "preprod", KEYCLOAK_REALM, "password"),
    ],
)
def test_password_grant_config(
    requests_mock, monkeypatch, region, env, realm, grant_type
):
    monkeypatch.setenv("PASQAL_CLOUD_ENV", env)
    target = resolve_pasqal_cloud_target(region)
    issuer = target.deployment.issuer.rstrip("/")
    requests_mock.get(
        f"{issuer}/.well-known/openid-configuration",
        json={
            "authorization_endpoint": f"{issuer}/authorize",
            "token_endpoint": f"{issuer}/token",
            "scopes_supported": ["offline_access"],
        },
    )

    config = password_grant_config(target)

    assert config == TokenProviderConf(
        token_endpoint=f"{issuer}/token",
        public_client_id=target.deployment.client_id,
        audience=target.deployment.audience,
        realm=realm,
        grant_type=grant_type,
    )
