# PASQAL Cloud

Interfaces for the Pasqal Cloud Services, including the `pasqal-cloud` SDK and the `pulser-pasqal` extension.

## Installation

To install the latest release of the `pasqal-cloud` (formerly pasqal-sdk), have Python 3.8.0 or higher installed, then
use pip:

```bash
pip install pasqal-cloud
```

Likewise, with Python 3.9.0 or higher, `pulser-pasqal` is installed with:

```bash
pip install pulser-pasqal
```

If you wish to **install the development version of the pasqal-cloud and pulser-pasqal from source** instead, do the following from within
this repository after cloning it:

```bash
git checkout dev
pip install -e pasqal-cloud -e pulser-pasqal
```

Bear in mind that this installation will track the contents of your local
pasqal-cloud and pulser-pasqal repository folders, so if you check out a different branch (e.g. `master`),
your installation will change accordingly.

### Development Requirements (Optional)

To run the tutorials or the test suite locally, run the following to install the development requirements:

```bash
pip install -e pasqal-cloud[dev] -e pulser-pasqal
```

We use pre-commit hooks to enforce some code linting, you can install pre-commit with Python pip:

```bash
python3 -m pip install pre-commit
pre-commit install
```

## Basic usage

For an overview of how to use each library, please refer to

- [The `pasqal-cloud` README](pasqal-cloud/README.md)
- [The `pulser-pasqal` documentation](https://pulser.readthedocs.io/en/stable/tutorials/backends.html#Backend-Execution-of-Pulser-Sequences)
