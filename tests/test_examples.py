"""Tests for the scripts embedded in the documentation."""

import runpy
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pasqal_cloud
import pulser
import pytest
from pulser import AnalogDevice

EXAMPLES_DIR = Path(__file__).parents[1] / "examples"
EXAMPLE_SCRIPTS = tuple(sorted(EXAMPLES_DIR.glob("*.py")))


class _ExampleBackend:
    """Backend double that keeps documentation examples offline."""

    def __init__(self, *, sequence, connection):
        self.sequence = sequence
        self.connection = connection

    def run(self, **kwargs):
        assert kwargs["wait"] is True
        assert kwargs["job_params"]
        return SimpleNamespace(results=[])

    def open_batch(self):
        return nullcontext()


@pytest.mark.parametrize("script", EXAMPLE_SCRIPTS, ids=lambda path: path.name)
def test_documentation_example(monkeypatch: pytest.MonkeyPatch, script: Path):
    """Execute each documentation example without contacting cloud services."""
    connection = Mock()
    connection.fetch_available_devices.return_value = {"FRESNEL_CAN1": AnalogDevice}

    monkeypatch.setattr(
        pasqal_cloud, "PasqalCloudConnection", Mock(return_value=connection)
    )
    monkeypatch.setattr(pasqal_cloud, "RemoteMPSBackend", _ExampleBackend)
    monkeypatch.setattr(pulser, "QPUBackend", _ExampleBackend)

    runpy.run_path(str(script), run_name="__main__")

    connection.fetch_available_devices.assert_called_once_with()
