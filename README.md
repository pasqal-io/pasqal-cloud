# PASQAL Cloud

SDK to be used to access Pasqal Cloud Services.

## Installation

To install the latest release of the `pasqal-cloud` (formerly pasqal-sdk), have Python 3.8.0 or higher installed, then use pip:

```bash
pip install pasqal-cloud
```

If you wish to **install the development version of the pasqal_cloud from source** instead, do the following from within this repository after cloning it:

```bash
git checkout develop
pip install -e .
```

Bear in mind that this installation will track the contents of your local
pasqal-cloud repository folder, so if you checkout a different branch (e.g. `master`),
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

Once you have created your sequence, you should serialize it as follows:

```python
# sequence should be a pulser Sequence object
serialized_sequence = sequence.to_abstract_repr()
```

Once you have serialized your sequence, you can send it with the SDK with the following code

```python
from pasqal_cloud import SDK
from pulser import devices, Register, Sequence

group_id="your_group_id" # Replace this value by your group_id on the PASQAL platform.
username="your_username" # Replace this value by your username or email on the PASQAL platform.
password="your_password" # Replace this value by your password on the PASQAL platform.

sdk = SDK(username=username, password=password, group_id=group_id)

# When creating a job, select a number of runs and set the desired values for the variables
# defined in the sequence
job1 = {"runs": 20, "variables": {"omega_max": 6} }
job2 = {"runs": 50, "variables": {"omega_max": 10.5} }

# Send the batch of jobs to the QPU and wait for the results
batch = sdk.create_batch(serialized_sequence, [job1,job2], wait=True)

# You can also choose to run your batch on an emulator using the optional argument 'emulator'
# For using a basic single-threaded QPU emulator that can go up to 10 qubits, you can specify the "EMU_FREE" emulator.
from pasqal_cloud.device import EmulatorType
batch = sdk.create_batch(serialized_sequence, [job1,job2], emulator=EmulatorType.EMU_FREE)

# Once the QPU has returned the results, you can access them with the following:
for job in batch.jobs.values():
    print(job.result)

```

## Advanced usage

### Authentication

There are several ways to provide a correct authentication using the SDK.

```python
from pasqal_cloud import SDK

group_id="your_group_id" # Replace this value by your group_id on the PASQAL platform.
username="your_username" # Replace this value by your username or email on the PASQAL platform.
password="your_password" # Replace this value by your password on the PASQAL platform.
# Ideally, do not write this password in a script but provide in through the command-line or as a secret environment variable.

""" Method 1: Username + Password
    If you know your credentials, you can pass them to the SDK instance on creation.
"""
sdk = SDK(username=username, password=password, group_id=group_id)

""" Method 2: Username only
    If you only want to insert your username, but want a solution to have your password being secret
    you can run the SDK without password. A prompt will then ask for your password
"""
sdk = SDK(username=username, group_id=group_id)
> Please, enter your password:

""" Method 3: Use a custom token provider
    You can define a custom class to provide the token.
    For example, if you know your token, you can use that token to authenticate directly to our APIs as follows.
"""
class CustomTokenProvider(TokenProvider):
    def get_token(self):
        return "your-token" # Replace this value with your token


sdk = SDK(token_provider=CustomTokenProvider(), group_id=group_id)
```

### Extra emulator configuration (Soon publicly available)

Some emulators, such as EMU_TN and EMU_FREE, accept further configuration to control the emulation.
This is because these emulators are more advanced numerical simulation of the quantum system.

For EMU_TN you may add the integrator timestep in nanoseconds, the numerical accuracy desired in the tensor network compression, and the maximal bond dimension of tensor network state.

```python
# replace the corresponding section in the above code example with this to
# add further configuration
from pasqal_cloud.device import EmulatorType, EmuTNConfig

configuration = EmuTNConfig(dt = 10.0, precision = "normal", max_bond_dim = 100)
batch = sdk.create_batch(serialized_sequence, [job1,job2], emulator=EmulatorType.EMU_TN, configuration=configuration)
```

For EMU_FREE you may add some default SPAM noise. Beware this makes your job take much longer.

```python
# replace the corresponding section in the above code example with this to
# add further configuration
from pasqal_cloud.device import EmulatorType, EmuFreeConfig

configuration = EmuFreeConfig(with_noise=True)
batch = sdk.create_batch(serialized_sequence, [job1,job2], emulator=EmulatorType.EMU_FREE, configuration=configuration)
```

### List of supported device specifications

The SDK provides a method to retrieve the devices specs currently defined on PASQAL's cloud platform.
They define the physical constraints of our QPUs and these constraints enforce some rules on
the pulser sequence that can be run on QPUs (e.g. max amount of atoms, available pulse channels, ...)

```python
sdk.get_device_specs_list()
```

The method returns a dict object mapping a device type to a serialized device specs. These specs can be used
to instantiate a `Device` instance in the `Pulser` library.


### Target different API endpoints

This is intended to the package developers.

If you want to redefine the APIs used by the SDK, please, do the following.

```python
from pasqal_cloud import SDK, Endpoints, Auth0COnf

endpoints = Endpoints(core = "my_new_core_endpoint")
auth0 = Auth0Conf(
    domain="new_domain",
    public_client_id="public_id",
    audience="new_audience"
)
sdk = SDK(..., endpoints=endpoints, auth0=auth0)
```

This enables you to target backend services running locally on your machine, or other environment like preprod or dev.

