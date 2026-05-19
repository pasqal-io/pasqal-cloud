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

import warnings
from typing import Any, ClassVar

import pulser
from pasqal_cloud.device.device_types import DeviceTypeName
from pulser.backend import BitStrings, EmulationConfig, EmulatorBackend
from pulser.backend.remote import JobParams, RemoteBackend, RemoteResults

from pasqal_cloud.pasqal_cloud_connection import PasqalCloud


class RemoteEmulatorBackend(RemoteBackend, EmulatorBackend):
    _device_type: ClassVar[DeviceTypeName]

    def __init__(
        self,
        sequence: pulser.Sequence,
        connection: PasqalCloud,
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

        Warning:
            Unlike a 'QPUBackend', this backend does not expect a value for
            "runs" in each entry of 'job_params'. If provided, this value is
            ignored. If you wish to set the total number of bitstring counts
            in the Results, please provide a 'BitStrings' observable with the
            desired 'num_shots' via this backend's 'config' instead."

        Returns:
            The results, which can be accessed once all sequences have been
            successfully executed.
        """
        _job_params: list[JobParams]
        if job_params is None:
            # Assume a single job
            _job_params = [{"runs": 1}]
        else:
            if any(
                j.get("runs", None) is not None
                for j in job_params
                if isinstance(j, dict)
            ):
                # Warns whenever runs is defined and not None
                warnings.warn(
                    "The 'runs' parameter is ignored on jobs executed on "
                    f"{self.__class__.__name__!r}. If you wish to set a "
                    "custom number of bitstring counts in the Results, please "
                    "provide a 'BitStrings' observable with the desired "
                    "'num_shots' via this backend's 'config' instead.",
                    stacklevel=2,
                )
            # TODO: Stop defaulting runs=1 once it is optional on pasqal-cloud
            _job_params = [{"runs": 1, **j} for j in job_params]
        return super().run(job_params=_job_params, wait=wait)

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
