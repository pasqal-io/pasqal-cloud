# Pasqal Cloud

**Pasqal Cloud** is a Python package to run quantum sequences on
[Pasqal](https://www.pasqal.com/) neutral atom quantum computers.

It implements the Pulser
[`RemoteConnection`](https://docs.pasqal.com/pulser/) interface so any sequence
written with Pulser can be submitted to
Pasqal QPUs and emulators.

## Installation

```bash
pip install pasqal-cloud
```

## At a glance

```python
from pasqal_cloud import PasqalCloudConnection

connection = PasqalCloudConnection(
    username="your_username",
    password="your_password",
    project_id="your_project_id",
)

devices = connection.fetch_available_devices()
```

## Where to next?

- [Getting started](getting-started.md) — full end-to-end example
- [API reference](reference/index.md) — auto-generated from the source

## License

Apache 2.0 — see [LICENSE](https://github.com/pasqal-io/pasqal-cloud/blob/main/LICENSE).
