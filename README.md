# pasqal-cloud

`pasqal-cloud` is a Python package to run quantum sequences on [Pasqal](https://www.pasqal.com/) neutral atom quantum computers.

It implements the Pulser [`RemoteConnection`](https://docs.pasqal.com/pulser/) interface so any sequence written with Pulser can be submitted to Pasqal QPUs and emulators.

## Version Support & Deprecation Timeline

| Version | Release Date | End of Support |
|---------|--------------|----------------|
| 0.20.4  | 2025-08-27   | 2026-08-27     |
| 0.20.5  | 2025-09-15   | 2026-09-15     |
| 0.20.6  | 2025-10-21   | 2026-10-21     |
| 0.20.7  | 2026-01-13   | 2027-01-13     |
| 0.20.8  | 2026-01-30   | 2027-01-30     |
| 0.21.0  | 2026-02-25   | 2027-02-25     |
| 0.22.0  | 2026-03-17   | 2027-03-17     |
| 0.23.0  | 2026-06-30   | 2027-03-30     |

## Getting started

To install the latest release of the `pasqal-cloud` (formerly pasqal-sdk), have Python 3.10 or higher installed, then
use pip:

```bash
pip install pasqal-cloud
```

If you wish to **install the development version of the pasqal-cloud and from source** instead, do the
following from within
this repository after cloning it:

```bash
pip install -e pasqal-cloud --config-settings editable_mode=compat
```

Bear in mind that this installation will track the contents of your local
pasqal-cloud repository folder, so if you check out a different branch,
your installation will change accordingly.

### Development Requirements (Optional)

To run the tutorials or the test suite locally, run the following to install the development requirements:

```bash
pip install -e "pasqal-cloud[dev]" --config-settings editable_mode=compat
```

We use pre-commit hooks to enforce some code linting, you can install pre-commit with Python pip:

```bash
python3 -m pip install pre-commit
pre-commit install
```

## Basic usage

For an overview of how to use each library, please refer to

- [The `pasqal-cloud` README](https://pasqal-io.github.io/pasqal-cloud/#getting-started)
