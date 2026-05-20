# Getting Started

This guide will help you install `pasqal-cloud`, authenticate, and submit your first job to Pasqal Cloud Services.

## Prerequisites

- **Python 3.9** or higher
- A **Pasqal Cloud account** with valid credentials (username & password)
- A **project ID** you are a member of (found on the [Pasqal user portal](https://portal.pasqal.cloud), in the _Project_ section)

## Installation

Install the latest release from PyPI:

```bash
pip install pasqal-cloud
```

## Authentication

Create a connection by providing your credentials and project ID:

```python
from pasqal_cloud import PasqalCloudConnection

connection = PasqalCloudConnection(
    username="your_username",       # Your Pasqal platform email
    password="your_password",       # Your Pasqal platform password
    project_id="your_project_id",  # Your project ID from the portal
)
```

!!! warning

    Never hard-code your password in source files. Prefer using environment variables instead

If you omit the `password` argument, you will be prompted to enter it interactively in
your terminal.

For more authentication options (custom token providers, OVH), see [Authentication](advanced-usage/authentication.md).

## Running a sequence on a QPU

See the [Pulser sequence documentation](https://docs.pasqal.com/pulser/sequence/)
for the full sequence-writing reference.

```python
--8<-- "examples/using_qpu.py"
```

## Running on emulators

The package exposes several remote emulator backends:

- [`EmuSVBackend`][pasqal_cloud.EmuSVBackend] — state vector emulator
- [`EmuMPSBackend`][pasqal_cloud.EmuMPSBackend] — matrix product states emulator
- [`EmuFreeBackend`][pasqal_cloud.EmuFreeBackend] — free-tier emulator

Use them in place of `QPUBackend` to run the same sequences without consuming
real QPU time:

```python
--8<-- "examples/using_emulators.py"
```

## Using open batch feature

```python
--8<-- "examples/using_open_batch.py"
```
