A batch is a group of jobs with the same sequence that will run on the same QPU.

## Create a batch of jobs

The package main component is a Python object called [`SDK`][pasqal_cloud.SDK] which can be used to create a [
`Batch`][pasqal_cloud.Batch].

For each [`Job`][pasqal_cloud.Job] of a given batch, you must set a value for each variable, if any, defined in your
sequence.
Once the QPU starts running a batch, only the jobs from that batch will be executed until they all end up in a
termination status (`DONE`, `ERROR`, `CANCELED`).
The batch sequence can be generated using [Pulser](https://github.com/pasqal-io/Pulser). See
their [documentation](https://pulser.readthedocs.io/en/stable/),
for more information on how to install the library and create your own sequence.

The sequence should be a Pulser sequence object. Once it's created, you can serialize like so:

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
from pasqal_cloud.device import DeviceTypeName

# Create an open batch with 1 job
batch = sdk.create_batch(serialized_sequence, [job1], device_type=DeviceTypeName.FRESNEL, open=True)
# Add some jobs to it and wait for the jobs to be terminated
job3 = {"runs": 50, "variables": {"omega_max": 10.5}}
batch.add_jobs([job2, job3], wait=True)
# When you have sent all the jobs to your batch, don't forget to mark it as closed
# Otherwise your batch will be timed out by the scheduler
batch.close()
```

You can assign multiple tags to your batches when creating them to help organize and retrieve them later.

```python
batch = sdk.create_batch(
    serialized_sequence,
    [job1, job2],
    tags=["special_experiment"]
)
```

You can also choose to run your batch on an emulator using the argument `device_type_name`.
For using a basic single-threaded QPU emulator that can go up to 10 qubits, you can specify the "EMU_FREE" emulator:

```python
from pasqal_cloud.device import DeviceTypeName

batch = sdk.create_batch(
    serialized_sequence, [job1, job2], device_type=DeviceTypeName.EMU_FREE
)
```

Once the API has returned the results, you can access them with the following:

```python
for job in batch.ordered_jobs:
    print(f"job-id: {job.id}, status: {job.status}, result: {job.result}")
```

## Get a list of batches

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

# Get batches with a specific tag
sdk.get_batches(filters=BatchFilters(tag="special_experiment"))

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

## Get a list of jobs

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

## Retry a batch of jobs

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

## Retry a job in an open batch

It is possible to retry a single job in a same open batch as an original job using `batch.retry`.
The batch must be open in order for this method to work.

```python

batch = sdk.create_batch(..., open=True)

batch.retry(batch.ordered_jobs[0])

# Like for adding a job you can choose to wait for results.
batch.retry(batch.ordered_jobs[0], wait=True)
```

## Cancel a list of batches

It is possible to cancel a list of batches with the `cancel_batches` method by
providing a list of batch ids.

```python
sdk.cancel_batches(batch_ids=[...])
```

## Cancel a list of jobs

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
