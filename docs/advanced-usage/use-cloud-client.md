You can get a [`PasqalCloudClient`][pasqal_cloud.pasqal_cloud_client.PasqalCloudClient] either by using the connection's one or instantiate it directly:

```python

# Get it from connection
from pasqal_cloud import PasqalCloudConnection

connection = PasqalCloudConnection(username="username", password="password", project_id="project_id")
cloud_client = connection._sdk_connection

# Instantiate it directly
from pasqal_cloud.pasqal_cloud_client import PasqalCloudClient

cloud_client = PasqalCloudClient(username="username", password="password", project_id="project_id")
```

## Batch

A batch is a group of jobs that will run on the same QPU or emulator. Sequences can be specified at the batch level,
at the job level, or both (jobs with their own sequence override the batch-level one).

### Submit Batch-level sequence

See [Running a sequence on a QPU](../getting-started.md#running-a-sequence-on-a-qpu)

### Submit Job-level sequence

Jobs can define their own `serialized_sequence`, which overrides the batch-level sequence.
This is useful when you want to run different quantum programs in the same batch.

```python
# Create jobs with their own sequences
job1 = {"runs": 20, "serialized_sequence": serialized_sequence1}
job2 = {"runs": 50, "serialized_sequence": serialized_sequence2}

# Create a batch without a batch-level sequence
batch = cloud_client.create_batch(serialized_sequence=None, jobs=[job1, job2], device_type=DeviceTypeName.FRESNEL, wait=True)
```

**Important**: When using job-level sequences, make sure to use non-parametrized sequences. Either use a batch-level
sequence with variables, or use job-level sequences without variables. Additionally, when creating a batch without a
sequence, all jobs must have their own sequences specified.

## Set tags to batches

You can set tags to an existing batch using two different methods.
Note that setting tags completely replace any existing tags of the batch.

```python
batch = cloud_client.set_batch_tags(
    batch_id,
    ["custom_tag_1", "custom_tag_2"]
)
```

## Get a list of batches

It is possible to get all batches or a selection of batches with the `get_batches` method.
The method returns by default a page of the 100 most recent batches but can be
configured using the `pagination_params` argument.

Here are few examples of how to use it:

```python
from datetime import datetime
from pasqal_cloud.utils.filters import BatchFilters, PaginationParams
from pasqal_cloud.utils.constants import BatchStatus, QueuePriority
from pasqal_cloud.device import EmulatorType

# Get the first 100 batches, no filters applied
cloud_client.get_batches()

# Get the first 40 batches, no filters applied
cloud_client.get_batches(pagination_params=PaginationParams(limit=40))

# Get the first 100 batches from a given device
cloud_client.get_batches(filters=BatchFilters(device_type=EmulatorType.EMU_TN))

# Get the first 100 batches in DONE from a specific project
cloud_client.get_batches(filters=BatchFilters(status=BatchStatus.DONE, project_id="project_id"))

# Get all batches with a specific tag
cloud_client.get_batches(filters=BatchFilters(tag="custom_tag_1"))

# Get two batches using two ids
cloud_client.get_batches(filters=BatchFilters(id=["batch_id_1", "batch_id_2"]))

# Get the first 100 batches with HIGH priority from a specific project
cloud_client.get_batches(filters=BatchFilters(queue_priority=QueuePriority.HIGH))

# Get the first 20 DONE batches created in a given period from a specific list of users
cloud_client.get_batches(limit=20,
                filters=BatchFilters(status=BatchStatus.DONE, start_date=datetime(...), end_date=datetime(...),
                                     user_id=["user_id_1", "user_id_2"]))

# Get the total number of batches matching the filters
cloud_client.get_batches(pagination_params=PaginationParams(offset=0)).total

# Get the first 300 batches, no filters applied
batches = []
batches.extend(cloud_client.get_batches(pagination_params=PaginationParams(offset=0)).results)
batches.extend(cloud_client.get_batches(pagination_params=PaginationParams(offset=100)).results)
batches.extend(cloud_client.get_batches(pagination_params=PaginationParams(offset=200)).results)
```

## Get a list of jobs

It is possible to get all jobs or a selection of jobs with the `get_jobs` method.
The method returns by default a page of the 100 most recent jobs but can be
configured using the `pagination_params` argument.

Here are few examples of how to use it:

```python
from datetime import datetime
from pasqal_cloud.utils.filters import JobFilters, PaginationParams
from pasqal_cloud.utils.constants import JobStatus

# Get the first 100 jobs, no filters applied
cloud_client.get_jobs()

# Get the first 40 jobs, no filters applied
cloud_client.get_jobs(pagination_params=PaginationParams(limit=40))

# Get the first 100 jobs from a given batch
cloud_client.get_jobs(filters=JobFilters(batch_id="batch_id"))

# Get the first 100 jobs in error from a specific project
cloud_client.get_jobs(filters=JobFilters(status=JobStatus.ERROR, project_id="project_id"))

# Get two jobs using two ids
cloud_client.get_jobs(filters=JobFilters(id=["job_id_1", "job_id_2"]))

# Get the first 20 cancelled jobs created in a given period from a specific list of users
cloud_client.get_jobs(limit=20,
             filters=JobFilters(status=JobStatus.CANCELED, start_date=datetime(...), end_date=datetime(...),
                                user_id=["user_id_1", "user_id_2"]))

# Get the total number of jobs matching the filters
cloud_client.get_jobs(pagination_params=PaginationParams(offset=0)).total

# Get the first 300 jobs, no filters applied
jobs = []
jobs.extend(cloud_client.get_jobs(pagination_params=PaginationParams(offset=0)).results)
jobs.extend(cloud_client.get_jobs(pagination_params=PaginationParams(offset=100)).results)
jobs.extend(cloud_client.get_jobs(pagination_params=PaginationParams(offset=200)).results)

```

## Retry a batch of jobs

It is possible to retry a selection of jobs from a CLOSED batch with the `rebatch` method.

```python
from datetime import datetime
from pasqal_cloud.utils.filters import RebatchFilters
from pasqal_cloud.utils.constants import JobStatus

# Retry all jobs from a given batch
cloud_client.rebatch(batch_id)

# Retry the first job of a batch
cloud_client.rebatch(batch_id, RebatchFilters(id=batch.ordered_jobs[0].id))

# Retry all jobs in error
cloud_client.rebatch(batch_id, RebatchFilters(status=JobStatus.ERROR))

# Retry cancelled jobs created in a given period
cloud_client.rebatch(batch_id, RebatchFilters(status=JobStatus.CANCELED, start_date=datetime(...), end_date=datetime(...)))

# Retry jobs that have a run number between 5 and 10
cloud_client.rebatch(batch_id, RebatchFilters(min_runs=5, max_runs=10))
```

## Retry a job in an open batch

It is possible to retry a single job in a same open batch as an original job using `batch.retry`.
The batch must be open in order for this method to work.

```python
batch = cloud_client.get_batch(batch_id)

batch.retry(batch.ordered_jobs[0])

# Like for adding a job you can choose to wait for results.
batch.retry(batch.ordered_jobs[0], wait=True)
```

## Cancel a list of batches

It is possible to cancel a list of batches with the `cancel_batches` method by
providing a list of batch ids.

```python
cloud_client.cancel_batches(batch_ids=[...])
```

## Cancel a list of jobs

It is possible to cancel a selection of jobs with the `cancel_jobs` method, using the `CancelJobFilters` class.

Here are few examples of how to use it:

```python
from datetime import datetime
from pasqal_cloud.utils.filters import CancelJobFilters

# Cancel two specific jobs
cloud_client.cancel_jobs(batch_id="batch_id", filters=CancelJobFilters(id=["job_id_1", "job_id_2"]))

# Cancel jobs created in a given period of time
cloud_client.cancel_jobs(batch_id="batch_id", filters=CancelJobFilters(start_date=datetime(...), end_date=datetime(...)))
```

## List of supported device specifications

The [`PasqalCloudClient`][pasqal_cloud.pasqal_cloud_client.PasqalCloudClient] provides a method to retrieve the device specs currently defined on Pasqal's cloud platform.
They define the physical constraints of our QPUs, and these constraints enforce some rules on
the pulser sequence that can be run on QPUs (e.g., max number of atoms, available pulse channels, ...)

```python
cloud_client.get_device_specs_dict()
```

The method returns a dict object mapping a device type to a serialized device specs. These specs can be used
to instantiate a `Device` instance in the `Pulser` library.


## Change the project linked to your Cloud client

When you instantiate an [`PasqalCloudClient`][pasqal_cloud.pasqal_cloud_client.PasqalCloudClient], you set the project it is linked to:

```python
cloud_client = PasqalCloudClient(username=username, password=password, project_id=project_id)
```

If you need to send batches/jobs/workloads to another project, you can do it without
having to instantiate another Cloud client:

```python
cloud_client.switch_to_project("other_project_id")
```

Once switched, all your next actions will target the new chosen project.
