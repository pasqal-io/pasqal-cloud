import json

import pytest
from pasqal_cloud import settings
from pasqal_cloud.cli import main
from pasqal_cloud.endpoints import DeploymentConf, DEPLOYMENTS, REGIONS
from pasqal_cloud.settings import resolve_pasqal_cloud_target


@pytest.fixture(autouse=True)
def config_path(monkeypatch, tmp_path):
    monkeypatch.delenv("PASQAL_CLOUD_PROFILE", raising=False)
    path = tmp_path / ".pasqal" / "config.json"
    monkeypatch.setattr(settings, "CONFIG_PATH", path)
    return path


def profiles(**profiles):
    return {"profiles": profiles}


def write_dev_profile(config_path):
    config_path.parent.mkdir()
    config_path.write_text(json.dumps(profiles(dev={})))


def region_conf(name):
    return {
        "issuer": f"https://{name}/",
        "client_id": name,
        "audience": name,
        "core_url": f"https://{name}/core-fast",
        "account_url": f"https://{name}/account",
    }


def active_dev(fr):
    return {"active_profile": "dev", **profiles(dev={"regions": {"fr": fr}})}


def test_defaults_without_config_file():
    target = resolve_pasqal_cloud_target()
    assert (target.profile, target.region) == ("default", "fr")
    assert target.deployment == DEPLOYMENTS["fr"]


@pytest.mark.parametrize("region", REGIONS)
def test_every_region_resolves(region):
    target = resolve_pasqal_cloud_target(region)
    assert target.region == region
    assert target.deployment == DEPLOYMENTS[region]


def test_config_default_region():
    target = resolve_pasqal_cloud_target(
        config=profiles(default={"default_region": "sa"})
    )
    assert target.region == "sa"


def test_flag_wins_over_config():
    target = resolve_pasqal_cloud_target(
        "fr", config=profiles(default={"default_region": "sa"})
    )
    assert target.region == "fr"


def test_default_profile_only_holds_default_region(config_path, capsys):
    assert main(["config", "set", "client_id", "custom"]) == 1
    assert main(["config", "unset", "issuer", "--profile", "default"]) == 1
    assert "uses the prod presets" in capsys.readouterr().err
    assert not config_path.exists()


def test_named_profile_uses_only_its_values():
    config = profiles(dev={"regions": {"fr": region_conf("fr-dev")}})
    deployment = resolve_pasqal_cloud_target("fr", "dev", config).deployment
    assert deployment == DeploymentConf(**region_conf("fr-dev"))


@pytest.mark.parametrize(
    ("regions", "error"),
    [
        ({}, "Profile 'dev' has no config for region 'sa'"),
        (
            {"sa": {"issuer": "https://sa-dev/"}},
            "Profile 'dev' is missing client_id, audience, core_url, account_url "
            "for region 'sa'",
        ),
    ],
)
def test_named_profile_never_falls_back_to_prod(regions, error):
    config = profiles(dev={"regions": {"fr": region_conf("fr-dev"), **regions}})
    with pytest.raises(ValueError, match=error):
        resolve_pasqal_cloud_target("sa", "dev", config)


def test_cli_completes_a_named_profile_region(config_path, capsys):
    write_dev_profile(config_path)

    assert main(["config", "set", "issuer", "https://dev/", "--profile", "dev"]) == 0
    assert main(["auth", "status", "--profile", "dev"]) == 1
    assert "missing client_id, audience" in capsys.readouterr().err

    for key, value in [
        ("client_id", "dev"),
        ("audience", "dev"),
        ("core_url", "https://dev/core"),
        ("account_url", "https://dev/account"),
    ]:
        assert main(["config", "set", key, value, "--profile", "dev"]) == 0
    target = resolve_pasqal_cloud_target(None, "dev")
    assert target.deployment == DeploymentConf(
        "https://dev/", "dev", "dev", "https://dev/core", "https://dev/account"
    )

    assert main(["config", "show", "--profile", "dev"]) == 0
    out = capsys.readouterr().out
    assert "client_id = dev" in out
    assert "[sa]\n# Profile 'dev' has no config for region 'sa'" in out


@pytest.mark.parametrize(
    ("config", "error"),
    [
        (profiles(default={"default_region": "us"}), "Invalid region 'us'"),
        (active_dev({}), "Profile 'dev' has no config for region 'fr'"),
        (
            active_dev({"isuer": "https://fr-dev/"}),
            "Profile 'dev' is missing issuer",
        ),
        (
            active_dev({**region_conf("fr-dev"), "issuer": "http://x/"}),
            "Invalid issuer",
        ),
        ({"active_profile": "nope"}, "Unknown profile 'nope'"),
    ],
)
def test_invalid_config_raises(config, error):
    with pytest.raises(ValueError, match=error):
        resolve_pasqal_cloud_target(config=config)


def test_invalid_json_raises(config_path):
    config_path.parent.mkdir()
    config_path.write_text("{")
    with pytest.raises(ValueError, match="Invalid JSON"):
        settings.load_config()


def test_unreadable_config_is_a_clean_error(config_path, capsys):
    config_path.mkdir(parents=True)

    assert main(["auth", "login"]) == 1
    assert "Is a directory" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("issuer", "not a url"),
        ("issuer", "http://auth.example.com/"),
        ("core_url", "https:///no-host"),
        ("client_id", ""),
    ],
)
def test_cli_rejects_invalid_values(config_path, capsys, key, value):
    write_dev_profile(config_path)

    assert main(["config", "set", key, value, "--profile", "dev"]) == 1
    assert f"Invalid {key}" in capsys.readouterr().err
    assert json.loads(config_path.read_text()) == profiles(dev={})


def test_cli_accepts_http_on_loopback(config_path):
    write_dev_profile(config_path)
    argv = ["config", "set", "core_url", "http://localhost:8000/core"]

    assert main([*argv, "--profile", "dev"]) == 0
    assert json.loads(config_path.read_text()) == profiles(
        dev={"regions": {"fr": {"core_url": "http://localhost:8000/core"}}}
    )


def test_saved_config_is_private(config_path):
    assert main(["config", "set", "default_region", "sa"]) == 0
    assert config_path.stat().st_mode & 0o777 == 0o600
    assert [p.name for p in config_path.parent.iterdir()] == ["config.json"]


def test_cli_set_and_unset(config_path):
    write_dev_profile(config_path)
    dev = ["--profile", "dev"]

    assert main(["config", "set", "default_region", "sa", *dev]) == 0
    assert main(["config", "set", "client_id", "custom", *dev]) == 0
    assert (
        main(["config", "set", "issuer", "https://dev/", "--region", "fr", *dev]) == 0
    )
    assert json.loads(config_path.read_text()) == profiles(
        dev={
            "default_region": "sa",
            "regions": {
                "sa": {"client_id": "custom"},
                "fr": {"issuer": "https://dev/"},
            },
        }
    )

    assert main(["config", "unset", "client_id", *dev]) == 0
    assert main(["config", "unset", "default_region", *dev]) == 0
    assert json.loads(config_path.read_text()) == profiles(
        dev={"regions": {"fr": {"issuer": "https://dev/"}}}
    )


def test_cli_rejects_invalid_default_region(config_path, capsys):
    assert main(["config", "set", "default_region", "us"]) == 1
    assert "expected one of: fr, sa" in capsys.readouterr().err
    assert not config_path.exists()


def test_cli_show(capsys):
    assert main(["config"]) == 0

    out = capsys.readouterr().out
    assert "default_region = fr" in out
    assert f"client_id = {DEPLOYMENTS['fr'].client_id}" in out
    assert f"[sa]\nissuer = {DEPLOYMENTS['sa'].issuer}" in out


def test_profile_resolution_order(monkeypatch):
    fr = {"regions": {"fr": region_conf("fr")}}
    config = {"active_profile": "dev", **profiles(dev=fr, preprod=fr, ci=fr)}
    assert resolve_pasqal_cloud_target(config=config).profile == "dev"

    monkeypatch.setenv("PASQAL_CLOUD_PROFILE", "ci")
    assert resolve_pasqal_cloud_target(config=config).profile == "ci"
    assert resolve_pasqal_cloud_target(None, "preprod", config).profile == "preprod"


def test_cli_profile_create_prompts(monkeypatch, config_path):
    # default_region, then the sa issuer, client_id (empty first: required, so
    # asked again), audience, core_url, account_url, then fr issuer (skipped).
    answers = iter(
        [
            "sa",
            "https://sa-dev/",
            "",
            "cloud-sdk",
            "sa-dev-aud",
            "https://sa-dev/core",
            "https://sa-dev/account",
            "",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert main(["config", "profile", "create", "dev"]) == 0

    assert json.loads(config_path.read_text()) == profiles(
        dev={
            "default_region": "sa",
            "regions": {
                "sa": {
                    "issuer": "https://sa-dev/",
                    "client_id": "cloud-sdk",
                    "audience": "sa-dev-aud",
                    "core_url": "https://sa-dev/core",
                    "account_url": "https://sa-dev/account",
                }
            },
        }
    )


def test_cli_profile_create_requires_the_default_region(monkeypatch, capsys):
    # default_region fr, its issuer left empty (asked again), its other keys,
    # then the sa issuer skipped.
    answers = iter(
        ["", "", "https://fr-dev/", "id", "aud", "https://c/", "https://a/", ""]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert main(["config", "profile", "create", "dev"]) == 0
    assert "fr issuer is required" in capsys.readouterr().err
    assert resolve_pasqal_cloud_target(None, "dev").deployment.issuer == (
        "https://fr-dev/"
    )


def test_cli_profile_create_rejects_invalid_default_region_first(monkeypatch):
    prompts = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "us")

    assert main(["config", "profile", "create", "dev"]) == 1
    assert len(prompts) == 1


def test_cli_profile_create_aborts_without_saving(monkeypatch, config_path):
    monkeypatch.setattr(
        "builtins.input", lambda _prompt: (_ for _ in ()).throw(EOFError)
    )
    assert main(["config", "profile", "create", "dev"]) == 1
    assert not config_path.exists()


def test_cli_profile_switch(capsys, config_path):
    config_path.parent.mkdir()
    config_path.write_text(
        json.dumps(profiles(dev={"regions": {"fr": region_conf("dev-id")}}))
    )

    assert main(["config", "profile", "activate", "dev"]) == 0
    assert resolve_pasqal_cloud_target().deployment.client_id == "dev-id"

    assert main(["config", "set", "audience", "dev-aud"]) == 0
    assert resolve_pasqal_cloud_target().deployment.audience == "dev-aud"
    assert main(["config", "show", "--profile", "default"]) == 0
    assert "dev-aud" not in capsys.readouterr().out

    assert main(["config", "profile", "list"]) == 0
    assert capsys.readouterr().out == "  default\n* dev\n"

    assert main(["config", "profile", "delete", "dev"]) == 0
    assert resolve_pasqal_cloud_target().profile == "default"


@pytest.mark.parametrize(
    ("argv", "error"),
    [
        (["config", "profile", "create", "default"], "already exists"),
        (["config", "profile", "create", " "], "can't be empty"),
        (["config", "profile", "activate", "nope"], "Unknown profile 'nope'"),
        (["config", "profile", "delete", "default"], "can't be deleted"),
        (["config", "set", "client_id", "x", "--profile", "nope"], "Unknown profile"),
    ],
)
def test_cli_profile_errors(capsys, argv, error):
    assert main(argv) == 1
    assert error in capsys.readouterr().err
