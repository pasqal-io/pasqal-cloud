import pytest
from pasqal_cloud.cli import (
    auth_status,
    build_parser,
    config_set_or_unset,
    config_show,
    login,
    logout,
    profile_activate,
    profile_create,
    profile_list,
)


@pytest.mark.parametrize(
    ("argv", "func", "expected"),
    [
        (["auth", "login"], login, {"region": None, "device": False}),
        (
            ["auth", "login", "--device", "--region", "sa"],
            login,
            {"region": "sa", "device": True},
        ),
        (["auth", "status", "--region", "fr"], auth_status, {"region": "fr"}),
        (["auth", "logout"], logout, {"region": None}),
        (["config"], config_show, {"profile": None}),
        (["config", "show", "--profile", "dev"], config_show, {"profile": "dev"}),
        (
            ["config", "set", "client_id", "x", "--region", "sa"],
            config_set_or_unset,
            {"key": "client_id", "value": "x", "region": "sa"},
        ),
        (
            ["config", "unset", "default_region"],
            config_set_or_unset,
            {"region": None, "value": None},
        ),
        (["auth", "login", "--profile", "dev"], login, {"profile": "dev"}),
        (["config", "profile", "list"], profile_list, {}),
        (["config", "profile", "create", "dev"], profile_create, {"name": "dev"}),
        (["config", "profile", "activate", "dev"], profile_activate, {"name": "dev"}),
    ],
)
def test_parse(argv, func, expected):
    args = build_parser().parse_args(argv)
    assert args.func is func
    for key, value in expected.items():
        assert getattr(args, key) == value


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["auth"],
        ["login"],
        ["auth", "login", "--region", "us"],
        ["auth", "logout", "--device"],
        ["config", "set", "realm", "x"],
        ["config", "set", "client_id"],
        ["config", "profile"],
        ["config", "--profile", "dev", "set", "client_id", "x"],
        ["config", "profile", "create"],
    ],
)
def test_parse_rejects(argv):
    with pytest.raises(SystemExit):
        build_parser().parse_args(argv)
