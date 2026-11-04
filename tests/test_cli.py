import pytest
from pasqal_cloud.cli import (
    auth_status,
    build_parser,
    login,
    logout,
    profile_activate,
    profile_create,
    profile_edit,
    profile_list,
    profile_show,
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
        (["profile", "list"], profile_list, {}),
        (["profile", "show"], profile_show, {"name": None}),
        (["profile", "show", "dev"], profile_show, {"name": "dev"}),
        (["profile", "create", "dev"], profile_create, {"name": "dev"}),
        (["profile", "edit", "dev"], profile_edit, {"name": "dev"}),
        (["profile", "activate", "dev"], profile_activate, {"name": "dev"}),
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
        ["config"],
        ["config", "profile", "list"],
        ["profile"],
        ["profile", "create"],
    ],
)
def test_parse_rejects(argv):
    with pytest.raises(SystemExit):
        build_parser().parse_args(argv)
