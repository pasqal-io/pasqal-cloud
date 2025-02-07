## Extra emulator configuration

Some emulators, such as EMU_TN and EMU_FREE, accept further configuration to control the emulation.
This is because these emulators are more advanced numerical simulation of the quantum system.

By default, validation rules are more permissive for jobs targeting an emulator than on the Fresnel QPU when submitting
jobs to the cloud platform.

You may however wish to validate that your job running on an emulator is compatible with Fresnel.
To that extent, set the `strict_validation` key in the configuration to `True`. Defaults to False.

```python

from pasqal_cloud.device import EmulatorType, EmuFreeConfig, EmuTNConfig

configuration = EmuTNConfig(strict_validation=True)
batch = sdk.create_batch(serialized_sequence, [job1, job2], emulator=EmulatorType.EMU_TN, configuration=configuration)

# or

configuration = EmuFreeConfig(strict_validation=True)
batch = sdk.create_batch(serialized_sequence, [job1, job2], emulator=EmulatorType.EMU_FREE, configuration=configuration)
```

For EMU_TN you may add the integrator timestep in nanoseconds, the numerical accuracy desired in the tensor network
compression, and the maximal bond dimension of tensor network state.

```python
from pasqal_cloud.device import EmulatorType, EmuTNConfig

configuration = EmuTNConfig(dt=10.0, precision="normal", max_bond_dim=100)
batch = sdk.create_batch(serialized_sequence, [job1, job2], emulator=EmulatorType.EMU_TN, configuration=configuration)
```

For EMU_FREE, you may add some default SPAM noise. Beware this makes your job take much longer.

```python
from pasqal_cloud.device import EmulatorType, EmuFreeConfig

configuration = EmuFreeConfig(with_noise=True)
batch = sdk.create_batch(serialized_sequence, [job1, job2], emulator=EmulatorType.EMU_FREE, configuration=configuration)
```

Replace the corresponding section in the code examples above with this to add further configuration.

## List of supported device specifications

The SDK provides a method to retrieve the device specs currently defined on PASQAL's cloud platform.
They define the physical constraints of our QPUs, and these constraints enforce some rules on
the pulser sequence that can be run on QPUs (e.g., max number of atoms, available pulse channels, ...)

```python
sdk.get_device_specs_dict()
```

The method returns a dict object mapping a device type to a serialized device specs. These specs can be used
to instantiate a `Device` instance in the `Pulser` library.

## Target different API endpoints

This is intended for the package developers or users which were given access to non-prod
environments of the PASQAL cloud platform.

To target a specific environment (`prod`, `preprod` or `dev`), instantiate the SDK class using
`PASQAL_ENDPOINTS['env']` for the parameter `endpoints` and `AUTH0_CONFIG['env']` for
`auth0` with env being the environment you want to target.

Example:

```python
from pasqal_cloud import AUTH0_CONFIG, SDK, PASQAL_ENDPOINTS

sdk = SDK(..., endpoints=PASQAL_ENDPOINTS['preprod'], auth0=AUTH0_CONFIG['preprod'])
```

By default, the targeted environment for `endpoints` and `auth0` is `prod`.
