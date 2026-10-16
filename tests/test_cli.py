import pytest
from pasqal_cloud.cli import auth_status, build_parser, login, logout


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
    ],
)
def test_parse_rejects(argv):
    with pytest.raises(SystemExit):
        build_parser().parse_args(argv)
