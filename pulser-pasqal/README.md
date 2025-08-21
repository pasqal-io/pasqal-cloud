# pulser-pasqal

[Pulser](https://pypi.org/project/pulser/) is a framework for composing, simulating and executing **pulse** sequences
for neutral-atom quantum devices.

This is the `pulser-pasqal` extension, which provides the functionalities needed to execute `pulser` sequences
on [Pasqal](https://portal.pasqal.cloud/)'s backends.

## Installation

The standard Pulser installation,

```bash
pip install pulser
```

will automatically install `pulser-pasqal`. If you wish to install it on its own, you can also run

```bash
pip install pulser-pasqal
```

Note that `pulser-core` is a requirement of `pulser-pasqal`, so it will be installed if it hasn't been already.

## Quickstart

pulser-pasqal provides two ways to connect to Pasqal Cloud services:

1. **Direct connection** using `PasqalCloud` with username/password authentication
2. **OVH integration** using `OVHConnection` with token authentication for OVH customers

### Using PasqalCloud

```python
from pulser_pasqal import PasqalCloud
from pulser import QPUBackend

# Authenticate with Pasqal Cloud
connection = PasqalCloud(username="YOUR_USERNAME", password="YOUR_PASSWORD", project_id="YOUR_PROJECT")

# Build a pulser sequence
...

# Submit and retrieve results
backend = QPUBackend(sequence, connection)
job = backend.run(wait=True)
results = job.results
print(results)
```

### OVH Integration

```python
from pulser_pasqal import OVHConnection
from pulser import QPUBackend

# Initiate the appropriate OVH connection
connection = OVHConnection()

# Build a pulser sequence
...

# Submit and retrieve results
backend = QPUBackend(sequence, connection)
job = backend.run(wait=True)
results = job.results
print(results)
```
