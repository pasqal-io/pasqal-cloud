import pytest
from pasqal_cloud.cli import main
from pasqal_cloud.endpoints import LOGIN_PRESETS, resolve_login_target


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("PASQAL_CLOUD_REGION", raising=False)
    monkeypatch.delenv("PASQAL_CLOUD_ENV", raising=False)


def test_defaults():
    target = resolve_login_target()
    assert (target.region, target.env) == ("fr", "prod")
    assert target.preset == LOGIN_PRESETS[("fr", "prod")]


def test_env_vars(monkeypatch):
    monkeypatch.setenv("PASQAL_CLOUD_REGION", "sa")
    monkeypatch.setenv("PASQAL_CLOUD_ENV", "preprod")
    target = resolve_login_target()
    assert (target.region, target.env) == ("sa", "preprod")


def test_flag_wins_over_env_var(monkeypatch):
    monkeypatch.setenv("PASQAL_CLOUD_REGION", "sa")
    target = resolve_login_target("fr")
    assert target.region == "fr"


@pytest.mark.parametrize(
    ("var", "value"), [("PASQAL_CLOUD_REGION", "us"), ("PASQAL_CLOUD_ENV", "staging")]
)
def test_invalid_values_raise(monkeypatch, var, value):
    monkeypatch.setenv(var, value)
    with pytest.raises(ValueError, match=r"\(env var\), expected one of"):
        resolve_login_target()


def test_invalid_explicit_region_raises():
    with pytest.raises(ValueError, match="fr, sa"):
        resolve_login_target("us")


def test_cli_reports_invalid_env(monkeypatch, capsys):
    monkeypatch.setenv("PASQAL_CLOUD_ENV", "staging")
    assert main(["auth", "status"]) == 1
    assert "prod, preprod, dev" in capsys.readouterr().err
