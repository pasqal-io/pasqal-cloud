# Getting Started

This guide will help you install `pasqal-cloud`, authenticate, and submit your first job to Pasqal Cloud Services.

## Prerequisites

- **Python 3.10** or higher
- A **Pasqal Cloud account**, see the [documentation](https://docs.pasqal.com/cloud/set-up/).
- A **project ID** you are a member of, see the [documentation](https://docs.pasqal.com/cloud/set-up/#find-your-project-id).


## Installation

Install the latest release from PyPI:

```bash
pip install pasqal-cloud
```

## Authentication

Log in once from a terminal, with the usual Pasqal Cloud login page:

```bash
pasqal-cloud auth login            # opens the browser
pasqal-cloud auth login --device   # no browser (SSH, notebook): shows a code to enter on a phone or laptop
```

Then create a connection with your project ID:

```python
from pasqal_cloud import PasqalCloudConnection

connection = PasqalCloudConnection(
    project_id="your_project_id",  # Your project ID from the portal
)
```

For more authentication options (username and password, custom token providers, OVH), see [Authentication](advanced-usage/authentication.md).

## Running a sequence on a QPU

See the [Pulser sequence documentation](https://docs.pasqal.com/pulser/sequence/)
for the full sequence-writing reference.

```python
--8<-- "examples/using_qpu.py"
```

## Running on emulators

The package exposes several remote emulator backends:

- [`RemoteSVBackend`][pasqal_cloud.RemoteSVBackend] — state vector emulator
- [`RemoteMPSBackend`][pasqal_cloud.RemoteMPSBackend] — matrix product states emulator
- [`RemoteEmuFreeBackend`][pasqal_cloud.RemoteEmuFreeBackend] — qutip emulator

Use them in place of `QPUBackend` to run the same sequences without consuming
real QPU time:

```python
--8<-- "examples/using_emulators.py"
```

## Using open batch feature

Open batches let you submit jobs whose variables depend on the results of
previous jobs, all while retaining control of the backend until the batch is
closed. See the [documentation](https://docs.pasqal.com/cloud/batches/#open-batches-for-variational-algorithms).

```python
--8<-- "examples/using_open_batch.py"
```
