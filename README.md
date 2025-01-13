# PASQAL Cloud

SDK to be used to access Pasqal Cloud Services.

## Version Support & Deprecation Timeline

| Version | Release Date | End of Support |
| ------- | ------------ | -------------- |
| 0.5.0   | 2024-02-05   | 2025-02-05     |
| 0.6.0   | 2024-02-26   | 2025-02-26     |
| 0.7.0   | 2024-03-05   | 2025-03-05     |
| 0.8.0   | 2024-04-15   | 2025-04-15     |
| 0.9.0   | 2024-05-15   | 2025-05-15     |
| 0.10.0  | 2024-06-05   | 2025-06-05     |
| 0.11.0  | 2024-06-27   | 2025-06-27     |
| 0.12.0  | 2024-09-03   | 2025-09-03     |
| 0.12.1  | 2024-09-11   | 2025-09-11     |
| 0.12.2  | 2024-09-11   | 2025-09-11     |
| 0.12.3  | 2024-10-02   | 2025-10-02     |
| 0.12.4  | 2024-10-09   | 2025-10-09     |
| 0.12.5  | 2024-11-12   | 2025-11-12     |
| 0.12.6  | 2024-12-12   | 2025-12-12     |
| 0.12.7  | 2025-01-14   | 2026-01-14     |

## Installation

To install the latest release of the `pasqal-cloud` (formerly pasqal-sdk), have Python 3.8.0 or higher installed, then
use pip:

```bash
pip install pasqal-cloud
```

If you wish to **install the development version of the pasqal-cloud from source** instead, do the following from within
this repository after cloning it:

```bash
git checkout dev
pip install -e .
```

Bear in mind that this installation will track the contents of your local
pasqal-cloud repository folder, so if you check out a different branch (e.g. `master`),
your installation will change accordingly.

### Development Requirements (Optional)

To run the tutorials or the test suite locally, run the following to install the development requirements:

```bash
pip install -e .[dev]
```

We use pre-commit hooks to enforce some code linting, you can install pre-commit with Python pip:

```bash
python3 -m pip install pre-commit
pre-commit install
```

## Basic usage

### Authentication

There are several ways to authenticate using the SDK:

```python
from pasqal_cloud import SDK

project_id = "your_project_id"  # Replace this value with your project_id on the PASQAL platform. It can be found on the user-portal, in the 'project' section.
username = "your_username"  # Replace this value with your username or email on the PASQAL platform.
password = "your_password"  # Replace this value with your password on the PASQAL platform.
```

#### Method 1: Username + Password

If you know your credentials, you can pass them to the SDK instance on creation:

```python
sdk = SDK(username=username, password=password, project_id=project_id)
```

#### Method 2: Username only

If you only want to insert your username, but want a solution to have your password being secret,
you can run the SDK without a password. A prompt will then ask for your password:

```python
sdk = SDK(username=username, project_id=project_id)
```

#### Method 3: Use a custom token provider

You can define a custom class to provide the token.
For example, if you have a token, you can use it to authenticate with our APIs:

```python
class CustomTokenProvider(TokenProvider):
    def get_token(self):
        return "your-token"  # Replace this value with your token


sdk = SDK(token_provider=CustomTokenProvider(), project_id=project_id)
```

Alternatively, create a custom `TokenProvider` that inherits from `ExpiringTokenProvider`.
You should define a custom '\_query_token' method which fetches your token.
See `Auth0TokenProvider` implementation for an example.

### Create a batch of jobs

The package main component is a python object called `SDK` which can be used to create a `Batch`.

A `Batch` is a group of jobs with the same sequence that will run on the same QPU. For each job of a given batch, you
must set a value for each variable, if any, defined in your sequence.
Once the QPU starts running a batch, only the jobs from that batch will be executed until they all end up in a
termination status (`DONE`, `ERROR`, `CANCELED`).
The batch sequence can be generated using [Pulser](https://github.com/pasqal-io/Pulser). See
their [documentation](https://pulser.readthedocs.io/en/stable/),
for more information on how to install the library and create your own sequence.

The sequence should be a pulser sequence object. Once it's created, you can serialize like so:

```python
serialized_sequence = sequence.to_abstract_repr()
```

When creating a job, select a number of runs and set the desired values for the variables defined in the sequence:

```python
job1 = {"runs": 20, "variables": {"omega_max": 6}}
job2 = {"runs": 50, "variables": {"omega_max": 10.5}}
```

Batches can either be "open" or "closed".
An "open" batch will accept new jobs after its creation, unlike a "closed" batch.
Open batch may be used to schedule variational algorithm where the next job parameter are derived from the results of
the previous jobs, without losing access to the QPU.

You can create a batch of jobs using the `create_batch` method of the SDK.
By default, this will create a closed batch, so all jobs should be passed as arguments right away.
You may set the `wait` argument to `True` to wait for all the jobs to end up in a termination status before proceeding
to the next statement.

```python
# Create a closed batch with 2 jobs and wait for its termination
batch = sdk.create_batch(serialized_sequence, [job1, job2], wait=True)
```

To create an open batch, set the `open` argument to `True`, you can then add jobs to your batch.
Don't forget to mark your batch as closed when you are done adding new jobs to it.

```python
# Create an open batch with 1 job
batch = sdk.create_batch(serialized_sequence, [job1], open=True)
# Add some jobs to it and wait for the jobs to be terminated
job3 = {"runs": 50, "variables": {"omega_max": 10.5}}
batch.add_jobs([job2, job3], wait=True)
# When you have sent all the jobs to your batch, don't forget to mark it as closed
# Otherwise your batch will be timed out by the scheduler
batch.close()
```

You can also choose to run your batch on an emulator using the optional argument `emulator`.
For using a basic single-threaded QPU emulator that can go up to 10 qubits, you can specify the "EMU_FREE" emulator:

```python
from pasqal_cloud.device import EmulatorType

batch = sdk.create_batch(
    serialized_sequence, [job1, job2], emulator=EmulatorType.EMU_FREE
)
```

Once the API has returned the results, you can access them with the following:

```python
for job in batch.ordered_jobs:
    print(f"job-id: {job.id}, status: {job.status}, result: {job.result}")
```

### Get a list of batches

It is possible to get all batches or a selection of batches with the `get_batches` method.
The method returns by default a page of the 100 most recent batches but can be
configured using the `pagination_params` argument.

Here are few examples of how to use it:

```python
from datetime import datetime
from pasqal_cloud import BatchFilters, BatchStatus, PaginationParams, QueuePriority, EmulatorType

# Get the first 100 batches, no filters applied
sdk.get_batches()

# Get the first 40 batches, no filters applied
sdk.get_batches(pagination_params=PaginationParams(limit=40))

# Get the first 100 batches from a given device
sdk.get_batches(filters=BatchFilters(device_type=EmulatorType.EMU_TN))

# Get the first 100 batches in DONE from a specific project
sdk.get_batches(filters=BatchFilters(status=BatchStatus.DONE, project_id="project_id"))

# Get two batches using two ids
sdk.get_batches(filters=BatchFilters(id=["batch_id_1", "batch_id_2"]))

# Get the first 100 batches with HIGH priority from a specific project
sdk.get_batches(filters=BatchFilters(queue_priority=QueuePriority.HIGH))

# Get the first 20 DONE batches created in a given period from a specific list of users
sdk.get_batches(limit=20,
                filters=BatchFilters(status=BatchStatus.DONE, start_date=datetime(...), end_date=datetime(...),
                                     user_id=["user_id_1", "user_id_2"]))

# Get the total number of batches matching the filters
sdk.get_batches(pagination_params=PaginationParams(offset=0)).total

# Get the first 300 batches, no filters applied
batches = []
batches.extend(sdk.get_batches(pagination_params=PaginationParams(offset=0)).results)
batches.extend(sdk.get_batches(pagination_params=PaginationParams(offset=100)).results)
batches.extend(sdk.get_batches(pagination_params=PaginationParams(offset=200)).results)
```

### Get a list of jobs

It is possible to get all jobs or a selection of jobs with the `get_jobs` method.
The method returns by default a page of the 100 most recent jobs but can be
configured using the `pagination_params` argument.

Here are few examples of how to use it:

```python
from datetime import datetime
from pasqal_cloud import JobFilters, JobStatus, PaginationParams

# Get the first 100 jobs, no filters applied
sdk.get_jobs()

# Get the first 40 jobs, no filters applied
sdk.get_jobs(pagination_params=PaginationParams(limit=40))

# Get the first 100 jobs from a given batch
sdk.get_jobs(filters=JobFilters(batch_id="batch_id"))

# Get the first 100 jobs in error from a specific project
sdk.get_jobs(filters=JobFilters(status=JobStatus.ERROR, project_id="project_id"))

# Get two jobs using two ids
sdk.get_jobs(filters=JobFilters(id=["job_id_1", "job_id_2"]))

# Get the first 20 cancelled jobs created in a given period from a specific list of users
sdk.get_jobs(limit=20,
             filters=JobFilters(status=JobStatus.CANCELED, start_date=datetime(...), end_date=datetime(...),
                                user_id=["user_id_1", "user_id_2"]))

# Get the total number of jobs matching the filters
sdk.get_jobs(pagination_params=PaginationParams(offset=0)).total

# Get the first 300 jobs, no filters applied
jobs = []
jobs.extend(sdk.get_jobs(pagination_params=PaginationParams(offset=0)).results)
jobs.extend(sdk.get_jobs(pagination_params=PaginationParams(offset=100)).results)
jobs.extend(sdk.get_jobs(pagination_params=PaginationParams(offset=200)).results)

```

### Retry a batch of jobs

It is possible to retry a selection of jobs from a CLOSED batch with the `rebatch` method.

```python
from datetime import datetime
from pasqal_cloud import RebatchFilters, JobStatus

# Retry all jobs from a given batch
sdk.rebatch(batch_id)

# Retry the first job of a batch
sdk.rebatch(batch_id, RebatchFilters(id=batch.ordered_jobs[0].id))

# Retry all jobs in error
sdk.rebatch(batch_id, RebatchFilters(status=JobStatus.ERROR))

# Retry cancelled jobs created in a given period
sdk.rebatch(batch_id, RebatchFilters(status=JobStatus.CANCELED, start_date=datetime(...), end_date=datetime(...)))

# Retry jobs that have a run number between 5 and 10
sdk.rebatch(batch_id, RebatchFilters(min_runs=5, max_runs=10))
```

### Retry a job in an open batch

It is possible to retry a single job in a same open batch as an original job using `batch.retry`.
The batch must be open in order for this method to work.

```python

batch = sdk.create_batch(..., open=True)

batch.retry(batch.ordered_jobs[0])

# Like for adding a job you can choose to wait for results.
batch.retry(batch.ordered_jobs[0], wait=True)
```

### Cancel a list of batches

It is possible to cancel a list of batches with the `cancel_batches` method by
providing a list of batch ids.

```python
sdk.cancel_batches(batch_ids=[...])
```

### Cancel a list of jobs

It is possible to cancel a selection of jobs with the `cancel_jobs` method, using the CancelJobFilters class.

Here are few examples of how to use it:

```python
from datetime import datetime
from pasqal_cloud import CancelJobFilters

# Cancel two specific jobs
sdk.cancel_jobs(batch_id="batch_id", filters=CancelJobFilters(id=["job_id_1", "job_id_2"]))

# Cancel jobs created in a given period of time
sdk.cancel_jobs(batch_id="batch_id", filters=CancelJobFilters(start_date=datetime(...), end_date=datetime(...)))
```

### Create a workload

A workload is a unit of work to be executed on Pasqal Cloud Services infrastructure.

To submit a new workload, select a type, target one of the available
backends and provide a configuration object to execute it.

You can create a workload through the SDK with the following command:

```python
workload = sdk.create_workload(workload_type="<WORKLOAD_TYPE>", backend="<BACKEND>", config={"config_param_1": "value"})
```

You can cancel the workload by doing:

```python
sdk.cancel_workload(workload.id)
```

Or refresh the workload status/results by with the following:

```python
workload = sdk.get_workload(workload.id)
```

Once the workload has been processed, you can fetch the result like this:

```python
print(f"workload-id: {workload.id}, status: {workload.status}, result: {workload.result}")
```

## Advanced usage

### Extra emulator configuration

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

### List of supported device specifications

The SDK provides a method to retrieve the device specs currently defined on PASQAL's cloud platform.
They define the physical constraints of our QPUs, and these constraints enforce some rules on
the pulser sequence that can be run on QPUs (e.g., max number of atoms, available pulse channels, ...)

```python
sdk.get_device_specs_dict()
```

The method returns a dict object mapping a device type to a serialized device specs. These specs can be used
to instantiate a `Device` instance in the `Pulser` library.

### Target different API endpoints

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
