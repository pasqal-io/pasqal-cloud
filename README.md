# Pasqal Cloud

Interfaces for the Pasqal Cloud Services, including the `pasqal-cloud` SDK and the `pulser-pasqal` extension.

## Version Support & Deprecation Timeline

| Version | Release Date | End of Support |
|---------|--------------|----------------|
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
| 0.13.0  | 2025-02-25   | 2026-02-25     |
| 0.20.2  | 2025-03-05   | 2026-03-05     |
| 0.20.3  | 2025-05-26   | 2026-05-26     |
| 0.20.4  | 2025-08-27   | 2026-08-27     |
| 0.20.5  | 2025-09-15   | 2026-09-15     |
| 0.20.6  | 2025-10-21   | 2026-10-21     |
| 0.20.7  | 2026-01-13   | 2027-01-13     |
| 0.20.8  | 2026-01-30   | 2027-01-30     |

## Getting started

To install the latest release of the `pasqal-cloud` (formerly pasqal-sdk), have Python 3.9.0 or higher installed, then
use pip:

```bash
pip install pasqal-cloud
```

Likewise, with Python 3.9.0 or higher, `pulser-pasqal` is installed with:

```bash
pip install pulser-pasqal
```

If you wish to **install the development version of the pasqal-cloud and pulser-pasqal from source** instead, do the
following from within
this repository after cloning it:

```bash
git checkout dev
pip install -e pasqal-cloud --config-settings editable_mode=compat
pip install -e pulser-pasqal --config-settings editable_mode=compat
```

Bear in mind that this installation will track the contents of your local
pasqal-cloud and pulser-pasqal repository folders, so if you check out a different branch (e.g. `master`),
your installation will change accordingly.

### Development Requirements (Optional)

To run the tutorials or the test suite locally, run the following to install the development requirements:

```bash
pip install -e pulser-pasqal[dev] --config-settings editable_mode=compat
```

We use pre-commit hooks to enforce some code linting, you can install pre-commit with Python pip:

```bash
python3 -m pip install pre-commit
pre-commit install
```

## Basic usage

For an overview of how to use each library, please refer to

- [The `pasqal-cloud` README](https://pasqal-io.github.io/pasqal-cloud/#getting-started)
- [The
  `pulser-pasqal` documentation](https://pulser.readthedocs.io/en/stable/tutorials/backends.html#Backend-Execution-of-Pulser-Sequences)
