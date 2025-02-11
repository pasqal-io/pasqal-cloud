## Latest release

To install the latest release of the `pasqal-cloud` (formerly pasqal-sdk), have Python 3.8.0 or higher installed, then
use pip:

```bash
pip install pasqal-cloud
```

## Development version

If you wish to **install the development version of the pasqal-cloud from source** instead, do the following from within
this repository after cloning it:

```bash
git checkout dev
pip install -e .
```

Bear in mind that this installation will track the contents of your local
pasqal-cloud repository folder, so if you check out a different branch (e.g. `master`),
your installation will change accordingly.

### Development Requirements (Optional)

To run the tutorials or the test suite locally, run the following to install the development requirements:

```bash
pip install -e .[dev]
```

We use pre-commit hooks to enforce some code linting, you can install pre-commit with Python pip:

```bash
python3 -m pip install pre-commit
pre-commit install
```
