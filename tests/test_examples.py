"""Tests for the scripts embedded in the documentation."""

import runpy
from pathlib import Path
from unittest.mock import create_autospec

import pasqal_cloud
import pytest
from pasqal_cloud import PasqalCloudConnection
from pulser import AnalogDevice

EXAMPLES_DIR = Path(__file__).parents[1] / "examples"
EXAMPLE_SCRIPTS = tuple(sorted(EXAMPLES_DIR.glob("*.py")))


@pytest.mark.parametrize("script", EXAMPLE_SCRIPTS, ids=lambda path: path.name)
def test_documentation_example(monkeypatch: pytest.MonkeyPatch, script: Path):
    """Execute each documentation example without contacting cloud services."""
    connection_class = create_autospec(PasqalCloudConnection)
    connection = connection_class.return_value
    connection.fetch_available_devices.return_value = {"FRESNEL_CAN1": AnalogDevice}
    connection.update_sequence_device.side_effect = lambda sequence: sequence
    connection.supports_open_batch.return_value = True

    monkeypatch.setattr(pasqal_cloud, "PasqalCloudConnection", connection_class)

    runpy.run_path(str(script), run_name="__main__")

    connection.fetch_available_devices.assert_called_once_with()
    assert connection.submit.called
