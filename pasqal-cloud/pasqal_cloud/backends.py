# Copyright 2023 Pulser Development Team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Defines Pasqal specific backends."""

from __future__ import annotations

import logging
import warnings
from typing import Any, ClassVar

import pulser
from pasqal_cloud.device.device_types import DeviceTypeName
from pulser.backend import BitStrings, EmulationConfig, EmulatorBackend
from pulser.backend.remote import JobParams, RemoteBackend, RemoteResults

from pasqal_cloud.pasqal_cloud_connection import PasqalCloudConnection

logger = logging.getLogger(__name__)


class RemoteEmulatorBackend(RemoteBackend, EmulatorBackend):  # type: ignore[misc]
    _device_type: ClassVar[DeviceTypeName]

    def __init__(
        self,
        sequence: pulser.Sequence,
        connection: PasqalCloudConnection,
        *,
        config: EmulationConfig | None = None,
        mimic_qpu: bool = False,
    ) -> None:
        RemoteBackend.__init__(
            self,
            sequence=sequence,
            connection=connection,
            mimic_qpu=mimic_qpu,
        )
        EmulatorBackend.__init__(
            self,
            sequence,
            config=config,
            mimic_qpu=mimic_qpu,
        )

    def run(
        self, job_params: list[JobParams] | None = None, wait: bool = False
    ) -> RemoteResults:
        """Runs the sequence on this remote emulator and returns the result.

        Args:
            job_params: A list of parameters for each job to execute. If the
                sequence is parametrized, the values for all the variables
                necessary to build the sequence must be given for
                each job, under the 'variables' field. If not given, a single
                job is executed.
            wait: Whether to wait until the results of the jobs become
                available.  If set to False, the call is non-blocking and the
                obtained results' status can be checked using their `status`
                property.

        Note on 'runs':
            Unlike a QPU backend, emulator backends do not use 'runs'
            directly. Within an open_batch, 'runs' is ignored and a
            warning is emitted. Outside an open_batch, the highest
            'runs' value across all jobs is used to set
            'default_num_shots' on this backend's config (unless a
            'BitStrings' observable with a custom 'num_shots' is
            already configured, in which case 'runs' has no effect).
            To control the number of bitstring samples explicitly,
            provide a 'BitStrings' observable with the desired
            'num_shots' via this backend's 'config'.

        Returns:
            The results, which can be accessed once all sequences have been
            successfully executed.
        """
        _job_params: list[JobParams]
        if job_params is None:
            # Assume a single job
            _job_params = [{"runs": 1}]
        else:
            runs_values: list[int] = [
                j["runs"] for j in job_params if j.get("runs") is not None
            ]

            # Inside an open_batch: runs has no effect on emulators.
            # Reset runs to 1 and warn the user.
            if self._batch_id and runs_values:
                warnings.warn(
                    "The 'runs' parameter is ignored on jobs executed on "
                    f"{self.__class__.__name__!r} within an open_batch "
                    "for now. It uses BitStrings observable 'num_shots' "
                    f"or 'default_num_shots' of {self.__class__.__name__!r}'s config.",
                    stacklevel=2,
                )
            elif runs_values:
                max_runs = max(runs_values)
                if not self._apply_default_num_shots(max_runs):
                    warnings.warn(
                        "The 'runs' parameter has no effect on "
                        f"{self.__class__.__name__!r} because a "
                        "'BitStrings' observable with a custom "
                        "'num_shots' is already configured. The "
                        "existing 'num_shots' value will be used.",
                        stacklevel=2,
                    )
                elif len(runs_values) > 1:
                    warnings.warn(
                        "Passing multiple jobs with 'runs' is not "
                        "supported on emulator backends for now. "
                        f"'default_num_shots' has been set to "
                        f"{max_runs} (the highest 'runs' value) on "
                        f"{self.__class__.__name__!r}'s config.",
                        stacklevel=2,
                    )

            # TODO: Stop defaulting runs=1 once it is optional on pasqal-cloud
            _job_params = [{"runs": 1, **j} for j in job_params]

        return super().run(job_params=_job_params, wait=wait)

    def _apply_default_num_shots(self, max_runs: int) -> bool:
        """Set config.default_num_shots from the highest 'runs' value.

        Returns True if default_num_shots was updated, False if a
        BitStrings observable already has a custom num_shots (in which
        case runs has no effect).
        """
        has_custom_num_shots = any(
            isinstance(obs, BitStrings) and obs.num_shots is not None
            for obs in self._config.observables
        )
        if has_custom_num_shots:
            return False

        self._config = self._config.with_changes(
            default_num_shots=max_runs,
        )
        logger.info(
            "Setting 'default_num_shots' to %d on %s's config "
            "(derived from the highest 'runs' value).",
            max_runs,
            self.__class__.__name__,
        )
        return True

    def _submit_kwargs(self) -> dict[str, Any]:
        """Keyword arguments given to any call to RemoteConnection.submit()."""
        return dict(
            batch_id=self._batch_id,
            backend_configuration=self._config,
            device_type=self._device_type,
        )


class EmuMPSBackend(RemoteEmulatorBackend):
    """
    Backend for executing quantum programs using the EMU-MPS emulator.

    The config supports various fields. For a complete list of accepted
    parameters (passed as `**kwargs`), refer to the official EMU-MPS documentation:
    https://pasqal-io.github.io/emulators/latest/emu_mps/api/#mpsconfig

    Args:
        sequence: The quantum sequence to execute on the backend.
        connection: An open PasqalCloud connection.
        config: An EmulationConfig object to configure the backend. If not provided,
            the default configuration will be used.
        mimic_qpu: Whether to mimic the validations required for
            execution on a QPU.
    """

    default_config = EmulationConfig(
        observables=[BitStrings()],
        num_gpus_to_use=1,
        autosave_dt=float("inf"),
        optimize_qubit_ordering=True,
    )
    _device_type = DeviceTypeName.EMU_MPS


class EmuSVBackend(RemoteEmulatorBackend):
    """
    Backend for executing quantum programs using the EMU-SV emulator.

    The config supports various fields. For a complete list of accepted
    parameters (passed as `**kwargs`), refer to the official EMU-SV documentation:
    https://pasqal-io.github.io/emulators/latest/emu_sv/api/#svconfig

    Args:
        sequence: The quantum sequence to execute on the backend.
        connection: An open PasqalCloud connection.
        config: An EmulationConfig object to configure the backend. If not provided,
            the default configuration will be used.
        mimic_qpu: Whether to mimic the validations required for
            execution on a QPU.
    """

    default_config = EmulationConfig(
        observables=[BitStrings()],
    )
    _device_type = DeviceTypeName.EMU_SV


class EmuFreeBackend(RemoteEmulatorBackend):
    """
    Backend for executing quantum programs using pulser-simulation (QuTiP).

    The config supports various fields. For a complete list of accepted
    parameters (passed as `**kwargs`), refer to the official documentation:
    https://pulser.readthedocs.io/en/stable/apidoc/_autosummary/pulser_simulation.QutipConfig.html#pulser_simulation.QutipConfig

    Args:
        sequence: The quantum sequence to execute on the backend.
        connection: An open PasqalCloud connection.
        config: An EmulationConfig object to configure the backend. If not provided,
            the default configuration will be used.
        mimic_qpu: Whether to mimic the validations required for
            execution on a QPU.
    """

    default_config = EmulationConfig(observables=[BitStrings()])
    _device_type = DeviceTypeName.EMU_FREE
