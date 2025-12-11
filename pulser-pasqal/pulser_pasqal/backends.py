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
from dataclasses import fields
from typing import Any, ClassVar

import pasqal_cloud
import pulser
from pasqal_cloud.device.device_types import DeviceTypeName
from pulser.backend import BitStrings, EmulationConfig, EmulatorBackend, EmulatorConfig
from pulser.backend.remote import JobParams, RemoteBackend, RemoteResults

from pulser_pasqal.pasqal_cloud import PasqalCloud

DEFAULT_CONFIG_EMU_TN = EmulatorConfig(evaluation_times="Final", sampling_rate=0.1)
DEFAULT_CONFIG_EMU_FREE = EmulatorConfig(evaluation_times="Final", sampling_rate=0.25)


class PasqalEmulator(RemoteBackend):
    """The base class for a Pasqal emulator backend."""

    emulator: ClassVar[pasqal_cloud.EmulatorType]
    default_config: ClassVar[EmulatorConfig] = EmulatorConfig()
    configurable_fields: ClassVar[tuple[str, ...]] = ("backend_options",)

    def __init__(
        self,
        sequence: pulser.Sequence,
        connection: PasqalCloud,
        config: EmulatorConfig | None = None,
        mimic_qpu: bool = False,
    ) -> None:
        """Initializes a new Pasqal emulator backend."""
        super().__init__(sequence, connection, mimic_qpu=mimic_qpu)
        config_ = config or self.default_config
        self._validate_config(config_)
        self._config = config_
        if not isinstance(self._connection, PasqalCloud):
            raise TypeError(
                "The connection to the remote backend must be done"
                " through a 'PasqalCloud' instance."
            )

    def run(
        self, job_params: list[JobParams] | None = None, wait: bool = False
    ) -> RemoteResults:
        """Executes on the emulator backend through the Pasqal Cloud.

        Args:
            job_params: A list of parameters for each job to execute. Each
                mapping must contain a defined 'runs' field specifying
                the number of times to run the same sequence. If the sequence
                is parametrized, the values for all the variables necessary
                to build the sequence must be given in it's own mapping, for
                each job, under the 'variables' field.
            wait: Whether to wait until the results of the jobs become
                available.  If set to False, the call is non-blocking and the
                obtained results' status can be checked using their `status`
                property.

        Returns:
            The results, which can be accessed once all sequences have been
            successfully executed.

        """
        suffix = f" when executing a sequence on {self.__class__.__name__}."
        if not job_params:
            raise ValueError("'job_params' must be specified" + suffix)
        self._type_check_job_params(job_params)
        if any("runs" not in j for j in job_params):
            raise ValueError(
                "All elements of 'job_params' must specify 'runs'" + suffix
            )

        return super().run(job_params, wait)

    def _submit_kwargs(self) -> dict[str, Any]:
        """Keyword arguments given to any call to RemoteConnection.submit()."""
        return {
            "batch_id": self._batch_id,
            "emulator": self.emulator,
            "config": self._config,
            "mimic_qpu": self._mimic_qpu,
        }

    def _validate_config(self, config: EmulatorConfig) -> None:
        if not isinstance(config, EmulatorConfig):
            raise TypeError(
                f"'config' must be of type 'EmulatorConfig', not {type(config)}."
            )
        for field in fields(config):
            if field.name in self.configurable_fields:
                continue
            default_value = getattr(self.default_config, field.name)
            if getattr(config, field.name) != default_value:
                raise NotImplementedError(
                    f"'EmulatorConfig.{field.name}' is not configurable in "
                    "this backend. It should not be changed from its default "
                    f"value of '{default_value}'."
                )


class EmuTNBackend(PasqalEmulator):
    """
    DEPRECATED: Use EmuMPSBackend instead. This class will be removed in a future release.

    An emulator backend using tensor network simulation.

    Configurable fields in EmulatorConfig:
        - sampling_rate: Defaults to 0.1. This value must remain low to use
          this backend efficiently.
        - backend_options:
            - precision (str): The precision of the simulation. Can be "low",
              "normal" or "high". Defaults to "normal".
            - max_bond_dim (int): The maximum bond dimension of the Matrix
              Product State (MPS). Defaults to 500.

    All other parameters should not be changed from their default values.

    Args:
        sequence: The sequence to send to the backend.
        connection: An open PasqalCloud connection.
        config: An EmulatorConfig to configure the backend. If not provided,
            the default configuration is used.
        mimic_qpu: Whether to mimic the validations necessary for
            execution on a QPU.
    """

    emulator = pasqal_cloud.EmulatorType.EMU_TN
    default_config = DEFAULT_CONFIG_EMU_TN
    configurable_fields = ("backend_options", "sampling_rate")

    def __init__(
        self,
        sequence: pulser.Sequence,
        connection: PasqalCloud,
        config: EmulatorConfig | None = None,
        mimic_qpu: bool = False,
    ) -> None:
        warnings.warn(
            "EmuTNBackend is deprecated and will be removed in a future release. Use EmuMPSBackend instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(sequence, connection, config, mimic_qpu)


class EmuFreeBackend(PasqalEmulator):
    """
    DEPRECATED: Use EmuFreeBackendV2 instead. This class will be removed in a future release.

    An emulator backend using free Hamiltonian time evolution.

    Configurable fields in EmulatorConfig:
        - backend_options:
            - with_noise (bool): Whether to add noise to the simulation.
              Defaults to False.

    All other parameters should not be changed from their default values.

    Args:
        sequence: The sequence to send to the backend.
        connection: An open PasqalCloud connection.
        config: An EmulatorConfig to configure the backend. If not provided,
            the default configuration is used.
        mimic_qpu: Whether to mimic the validations necessary for
            execution on a QPU.
    """

    emulator = pasqal_cloud.EmulatorType.EMU_FREE
    default_config = DEFAULT_CONFIG_EMU_FREE

    def __init__(
        self,
        sequence: pulser.Sequence,
        connection: PasqalCloud,
        config: EmulatorConfig | None = None,
        mimic_qpu: bool = False,
    ) -> None:
        warnings.warn(
            "EmuFreeBackend is deprecated and will be removed in a future release. Use EmuFreeBackendV2 instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(sequence, connection, config, mimic_qpu)


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
        # To be deleted once this PR is released: https://github.com/pasqal-io/Pulser/pull/890
        self._config = type(self.default_config)(
            **{
                **self.default_config._backend_options,
                **(config._backend_options if config else {}),
            }
        )

    def _submit_kwargs(self) -> dict[str, Any]:
        """Keyword arguments given to any call to RemoteConnection.submit()."""
        return dict(
            batch_id=self._batch_id,
            # To be deleted once this PR is released: https://github.com/pasqal-io/Pulser/pull/888
            mimic_qpu=self._mimic_qpu,
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
    _device_type = pasqal_cloud.DeviceTypeName.EMU_MPS


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
    _device_type = pasqal_cloud.DeviceTypeName.EMU_SV


class EmuFreeBackendV2(RemoteEmulatorBackend):
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
    _device_type = pasqal_cloud.DeviceTypeName.EMU_FREE
