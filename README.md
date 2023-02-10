# Cloud SDK

SDK to be used to access Pasqal Cloud Services.

## Installation

To install the latest release of the `cloud-sdk`, have Python 3.8.0 or higher installed, then use pip:

```bash
pip install pasqal-sdk
```

If you wish to **install the development version of the cloud_sdk from source** instead, do the following from within this repository after cloning it:

```bash
git checkout develop
pip install -e .
```

Bear in mind that this installation will track the contents of your local
cloud_sdk repository folder, so if you checkout a different branch (e.g. `master`),
your installation will change accordingly.

### Development Requirements (Optional)

To run the tutorials or the test suite locally, run the following to install the development requirements:

```bash
pip install -e .[dev]
```

## Basic usage

The package main component is a python object called `SDK` which can be used to create a `Batch` and send it automatically
to Pasqal APIs using an API token generated in the [user portal](https://portal.pasqal.cloud).

A `Batch` is a group of jobs with the same sequence that will run on the same QPU. For each job of a given batch you must set a value for each variable, if any, defined in your sequence.  
The batch sequence can be generated using [Pulser](https://github.com/pasqal-io/Pulser). See their [documentation](https://pulser.readthedocs.io/en/stable/),
for more information on how to install the library and create your own sequence.

Below is an example of the creation of a simple sequence with a single variable and its serialization to a string.

```python
from pulser import devices, Pulse, Register, Sequence
from pulser.register.special_layouts import SquareLatticeLayout

# Define a register for your sequence
register = Register.square(2, spacing=5, prefix="q")
# Create a sequence for that register
sequence = Sequence(register, devices.IroiseMVP)
# Add a channel to your sequence
sequence.declare_channel("rydberg", "rydberg_global")
# Declare a variable
omega_max = sequence.declare_variable("omega_max")
# Add a pulse to that channel with the amplitude omega_max
generic_pulse = Pulse.ConstantPulse(100, omega_max, 2, 0.0)
sequence.add(generic_pulse, "rydberg")

# When you are done building your sequence, serialize it into a string
serialized_sequence = sequence.serialize()
```

Once you have serialized your sequence, you can send it with the SDK with the following code

```python
from sdk import SDK
from pulser import devices, Register, Sequence

client_id="your_client_id" # Replace this value by the client id of your API key
client_secret="your_client_secret" #Replace this value by the client secret of your API key

sdk = SDK(client_id=client_id, client_secret=client_secret)

# When creating a job, select a number of runs and set the desired values for the variables
# defined in the sequence
job1 = {"runs": 20, "variables": {"omega_max": 6} }
job2 = {"runs": 50, "variables": {"omega_max": 10.5} }

# Send the batch of jobs to the QPU and wait for the results
batch = sdk.create_batch(serialized_sequence, [job1,job2], wait=True)

# You can also choose to run your batch on an emulator using the optional argument 'device_type'
# For using a basic single-threaded QPU emulator that can go up to 10 qubits, you can specify the "EMU_FREE" device type.
from sdk import DeviceType
batch = sdk.create_batch(serialized_sequence, [job1,job2], device_type=DeviceType.EMU_FREE)

# Once the QPU has returned the results, you can access them with the following:
for job in batch.jobs.values():
    print(job.result)

```

### Extra emulator configuration (Soon publicly available)

Some emulators, such as EMU_TN and EMU_FREE, accept further configuration to control the emulation.
This is because these emulators are more advanced numerical simulation of the quantum system.

For EMU_TN:

```python
# replace the corresponding section in the above code example with this to
# add further configuration
from sdk.device.device_types import DeviceType
from sdk.device.configuration import EmuTNConfig

configuration = EmuTNConfig(dt = 0.5, precision = "normal")
batch = sdk.create_batch(serialized_sequence, [job1,job2], device_type=DeviceType.EMU_TN, configuration=configuration)
```

For EMU_FREE:

```python
# replace the corresponding section in the above code example with this to
# add further configuration
from sdk.device.device_types import DeviceType
from sdk.device.configuration import EmuFreeConfig

configuration = EmuFreeConfig(with_noise=True)
batch = sdk.create_batch(serialized_sequence, [job1,job2], device_type=DeviceType.EMU_FREE, configuration=configuration)
```
