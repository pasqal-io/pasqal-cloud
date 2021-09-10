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
cloud_sdk repository folder, so if you checkout a different branch (e.g. ``master``),
your installation will change accordingly.

### Development Requirements (Optional)

To run the tutorials or the test suite locally, after installation first run the following to install the development requirements:

```bash
pip install -e .[dev]
```

## Basic usage

The package main component is a python object called `SDK` which can be used to create a `Batch` and send it automatically 
to Pasqal APIs using an API token generated in the [user portal](https://pasqal.cloud.io) (available soon).

A `Batch` is a group of jobs with the same sequence that run on the same QPU. 
The batch sequence can be generated using [Pulser](https://github.com/pasqal-io/Pulser). See their [documentation](https://pulser.readthedocs.io/en/stable/), 
for more information on how to install the library and create your own sequence.

```python
from sdk import SDK
from pulser import devices, Register, Sequence 

client_id="your_client_id" # Replace this value by the client id of your API key
client_secret="your_client_secret" #Replace this value by the client secret of your API key

sdk = SDK(client_id=client_id, client_secret=client_secret)

# Creation of a sequence
reg = Register.square(2, prefix="q")
sequence = Sequence(reg, devices.Chadoq2)
# You should add channels and variables to your sequence
# See Pulser documentation for details
serialized_sequence = sequence.serialize() # Serialize the sequence in json format

# Create a new batch and send it to Pasqal QPUs
batch = sdk.create_batch(serialized_sequence)

# Add jobs to your batch
job1 = batch.add_job(runs=400)
job2 = batch.add_job(runs=100, wait=True) # You can wait for the job results

results = job2.results # You can retrieve and post-process if wanted the results of the job

# Declare your batch complete, meaning it awaits no new jobs and the QPU can proceed to next batch
batch.declare_complete()
```