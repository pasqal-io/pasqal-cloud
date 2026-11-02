import pytest
from pasqal_cloud.cli import (
    auth_status,
    build_parser,
    config_show,
    login,
    logout,
    profile_activate,
    profile_create,
    profile_edit,
    profile_list,
)


@pytest.mark.parametrize(
    ("argv", "func", "expected"),
    [
        (["auth", "login"], login, {"profile": None, "device": False}),
        (
            ["auth", "login", "--device", "--profile", "dev"],
            login,
            {"profile": "dev", "device": True},
        ),
        (["auth", "status", "--profile", "dev"], auth_status, {"profile": "dev"}),
        (["auth", "logout"], logout, {"profile": None}),
        (["config"], config_show, {"profile": None}),
        (["config", "show", "--profile", "dev"], config_show, {"profile": "dev"}),
        (["config", "profile", "list"], profile_list, {}),
        (["config", "profile", "create", "dev"], profile_create, {"name": "dev"}),
        (["config", "profile", "edit", "dev"], profile_edit, {"name": "dev"}),
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
        ["auth", "login", "--region", "sa"],
        ["auth", "logout", "--device"],
        ["config", "set", "client_id", "x"],
        ["config", "unset", "client_id"],
        ["config", "profile"],
        ["config", "--profile", "dev", "show"],
        ["config", "profile", "create"],
    ],
)
def test_parse_rejects(argv):
    with pytest.raises(SystemExit):
        build_parser().parse_args(argv)
