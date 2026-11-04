import json

import pytest
from pasqal_cloud import settings
from pasqal_cloud.cli import main
from pasqal_cloud.endpoints import DeploymentConf, DEPLOYMENTS, REGIONS
from pasqal_cloud.settings import Config, resolve_pasqal_cloud_target


@pytest.fixture(autouse=True)
def config_path(monkeypatch, tmp_path):
    monkeypatch.delenv("PASQAL_CLOUD_PROFILE", raising=False)
    path = tmp_path / ".pasqal" / "config.json"
    monkeypatch.setattr(settings, "CONFIG_PATH", path)
    return path


def deployment(name):
    return {
        "issuer": f"https://{name}/",
        "client_id": name,
        "audience": name,
        "core_url": f"https://{name}/core-fast",
        "account_url": f"https://{name}/account",
    }


def write_config(config_path, **config):
    config_path.parent.mkdir()
    config_path.write_text(json.dumps(config))


def answer_prompts(monkeypatch, *answers):
    prompts = []
    it = iter(answers)
    monkeypatch.setattr(
        "builtins.input", lambda prompt: prompts.append(prompt) or next(it)
    )
    return prompts


def test_defaults_without_config_file():
    target = resolve_pasqal_cloud_target()
    assert target.profile == "default-fr"
    assert target.deployment == DEPLOYMENTS["fr"]


@pytest.mark.parametrize("region", REGIONS)
def test_builtin_profile_per_region(region):
    target = resolve_pasqal_cloud_target(f"default-{region}")
    assert target.deployment == DEPLOYMENTS[region]


def test_named_profile_uses_its_values():
    config = Config.model_validate({"profiles": {"dev": deployment("dev")}})
    target = resolve_pasqal_cloud_target("dev", config)
    assert target.deployment == DeploymentConf(**deployment("dev"))


def test_profile_resolution_order(monkeypatch):
    config = Config.model_validate(
        {
            "active_profile": "dev",
            "profiles": {n: deployment(n) for n in ("dev", "preprod", "ci")},
        }
    )
    assert resolve_pasqal_cloud_target(config=config).profile == "dev"

    monkeypatch.setenv("PASQAL_CLOUD_PROFILE", "ci")
    assert resolve_pasqal_cloud_target(config=config).profile == "ci"
    assert resolve_pasqal_cloud_target("preprod", config).profile == "preprod"


@pytest.mark.parametrize(
    ("config", "error"),
    [
        (
            {"profiles": {"dev": {"issuer": "https://dev/"}}},
            "dev.client_id: Field required",
        ),
        ({"profiles": {"dev": {**deployment("dev"), "issuer": "x"}}}, "https://"),
        ({"profiles": {"dev": {**deployment("dev"), "audience": " "}}}, "audience"),
        ({"profiles": {"default-sa": deployment("x")}}, "can't be redefined"),
    ],
)
def test_invalid_config_raises(config_path, config, error):
    write_config(config_path, **config)
    with pytest.raises(ValueError, match=error):
        settings.load_config()


def test_unknown_keys_survive_load_and_save(monkeypatch, config_path):
    # A config written by a newer version, with keys this one doesn't know.
    newer = {
        "telemetry": False,
        "profiles": {"dev": {**deployment("dev"), "scope": "openid"}},
    }
    write_config(config_path, **newer)
    answer_prompts(monkeypatch, "", "new-id", "", "", "")

    assert main(["profile", "activate", "dev"]) == 0
    assert main(["profile", "edit", "dev"]) == 0

    saved = json.loads(config_path.read_text())
    assert saved["telemetry"] is False
    assert saved["profiles"]["dev"]["scope"] == "openid"
    assert saved["profiles"]["dev"]["client_id"] == "new-id"


def test_unknown_active_profile_raises():
    with pytest.raises(ValueError, match="Unknown profile 'nope'"):
        resolve_pasqal_cloud_target(config=Config(active_profile="nope"))


def test_invalid_json_raises(config_path):
    config_path.parent.mkdir()
    config_path.write_text("{")
    with pytest.raises(ValueError, match="Invalid JSON(.|\n)*Fix these entries"):
        settings.load_config()


def test_unreadable_config_is_a_clean_error(config_path, capsys):
    config_path.mkdir(parents=True)

    assert main(["auth", "login"]) == 1
    assert "Is a directory" in capsys.readouterr().err


def test_http_url_warns_except_on_loopback():
    with pytest.warns(UserWarning, match="core_url .* isn't https"):
        DeploymentConf(**{**deployment("dev"), "core_url": "http://dev/core"})

    DeploymentConf(**{**deployment("dev"), "core_url": "http://localhost:8000/c"})


def test_cli_show(capsys):
    assert main(["profile", "show"]) == 0

    out = capsys.readouterr().out
    assert "profile = default-fr" in out
    assert f"client_id = {DEPLOYMENTS['fr'].client_id}" in out

    assert main(["profile", "show", "default-sa"]) == 0
    assert f"issuer = {DEPLOYMENTS['sa'].issuer}" in capsys.readouterr().out


def test_cli_profile_create_prompts(monkeypatch, config_path, capsys):
    # issuer invalid then valid, client_id empty (required, asked again), then
    # audience, core_url and account_url.
    answer_prompts(
        monkeypatch,
        "not a url",
        "https://dev/",
        "",
        "cloud-sdk",
        "dev-aud",
        "https://dev/core",
        "https://dev/account",
    )

    assert main(["profile", "create", "dev"]) == 0

    err = capsys.readouterr().err
    assert "Invalid issuer" in err
    assert "client_id is required" in err
    assert json.loads(config_path.read_text()) == {
        "profiles": {
            "dev": {
                "issuer": "https://dev/",
                "client_id": "cloud-sdk",
                "audience": "dev-aud",
                "core_url": "https://dev/core",
                "account_url": "https://dev/account",
            }
        }
    }
    assert config_path.stat().st_mode & 0o777 == 0o600
    assert [p.name for p in config_path.parent.iterdir()] == ["config.json"]


def test_cli_profile_edit_keeps_values_on_enter(monkeypatch, config_path):
    write_config(config_path, profiles={"dev": deployment("dev")})
    prompts = answer_prompts(monkeypatch, "", "new-id", "", "", "")

    assert main(["profile", "edit", "dev"]) == 0

    assert prompts[0] == "issuer [https://dev/]: "
    assert resolve_pasqal_cloud_target("dev").deployment == DeploymentConf(
        **{**deployment("dev"), "client_id": "new-id"}
    )


def test_cli_profile_create_checks_name_before_prompting(monkeypatch):
    prompts = answer_prompts(monkeypatch)

    assert main(["profile", "create", "default-fr"]) == 1
    assert prompts == []


def test_cli_profile_create_aborts_without_saving(monkeypatch, config_path):
    monkeypatch.setattr(
        "builtins.input", lambda _prompt: (_ for _ in ()).throw(EOFError)
    )
    assert main(["profile", "create", "dev"]) == 1
    assert not config_path.exists()


def test_cli_profile_switch(capsys, config_path):
    write_config(config_path, profiles={"dev": deployment("dev")})

    assert main(["profile", "activate", "dev"]) == 0
    assert resolve_pasqal_cloud_target().deployment.client_id == "dev"

    assert main(["profile", "list"]) == 0
    assert capsys.readouterr().out == "  default-fr\n  default-sa\n* dev\n"

    assert main(["profile", "delete", "dev"]) == 0
    assert resolve_pasqal_cloud_target().profile == "default-fr"
    assert json.loads(config_path.read_text()) == {"profiles": {}}


@pytest.mark.parametrize(
    ("argv", "error"),
    [
        (["profile", "create", "default-fr"], "already exists"),
        (["profile", "create", " "], "can't be empty"),
        (["profile", "activate", "nope"], "Unknown profile 'nope'"),
        (["profile", "edit", "default-sa"], "can't be changed"),
        (["profile", "delete", "default-fr"], "can't be changed"),
        (["auth", "login", "--profile", "nope"], "Unknown profile"),
    ],
)
def test_cli_profile_errors(capsys, argv, error):
    assert main(argv) == 1
    assert error in capsys.readouterr().err
