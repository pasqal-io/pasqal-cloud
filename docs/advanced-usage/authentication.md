## Log in with the `pasqal-cloud` command

The recommended way to authenticate is to log in once from a terminal, with the usual
Pasqal Cloud login page:

```bash
pasqal-cloud auth login            # opens the browser
pasqal-cloud auth login --device   # no browser: shows a code to enter on a phone or laptop
```

`--device` prints a URL and a code: open the URL on any device with a browser, enter the
code and log in there. The command waits until the login completes.

After that, Python code needs no credentials, only a project ID you are a member of. The
jobs created through the connection are billed to this project:

```python
from pasqal_cloud import PasqalCloudConnection

connection = PasqalCloudConnection(project_id="your_project_id")
```

To manage your login:

```bash
pasqal-cloud auth status   # show who you are logged in as
pasqal-cloud auth logout   # log out
```

`pasqal-cloud` is also available as `python -m pasqal_cloud`, e.g. when the scripts
folder of your Python environment is not on your `PATH`.

Your login is stored in `~/.pasqal/cloud-credentials.json`, readable only by you. Use
`pasqal-cloud auth logout` rather than deleting it.

If you are not logged in, or your login expired or was revoked, the SDK raises an error
giving the command to run to log in again.

### Which login to use where

| Situation | How to log in |
| --- | --- |
| Laptop | `pasqal-cloud auth login` |
| Remote machine without browser (SSH) | `pasqal-cloud auth login --device` |
| HPC / Slurm jobs | `pasqal-cloud auth login --device` on the login node, before submitting |
| Jupyter notebook | `!pasqal-cloud auth login --device` in a cell |
| Automated tests, CI | username and password, see [below](#log-in-with-a-username-and-password) |

!!! tip "Long Slurm jobs"

    To be safe, log in just before submitting your jobs. If the queue is long, keep an eye
    on it and log in again before your jobs start.

## Log in with a username and password

Logging in with a password is still supported, e.g. for automated tests. It does not work
for accounts enrolled in MFA: use `pasqal-cloud auth login` instead.

```python
from pasqal_cloud import PasqalCloudConnection

connection = PasqalCloudConnection(
    username="your_username",  # Your username or email on the Pasqal platform.
    password="your_password",  # Your password on the Pasqal platform.
    project_id="your_project_id",
)
```

!!! warning

    Never put your password directly in code. Use environment variables
    to avoid leaking passwords by mistake when pushing your code.

The password can be omitted: you are then prompted for it in your terminal when running
your script.

```python
connection = PasqalCloudConnection(username="your_username", project_id="your_project_id")
```

## Use a custom token provider (developers only)

You can define a custom class to provide the token.
For example, if you have a token, you can use it to authenticate with our APIs:

```python
from pasqal_cloud import PasqalCloudConnection
from pasqal_cloud.authentication import TokenProvider

class CustomTokenProvider(TokenProvider):
    def get_token(self):
        return "your-token"  # Replace this value with your token


connection = PasqalCloudConnection(token_provider=CustomTokenProvider(), project_id="your_project_id")
```

## OVHConnection

For OVH users, authentication is handled via the `PASQAL_PULSER_ACCESS_TOKEN` environment variable.
No username or password is required.

```bash
export PASQAL_PULSER_ACCESS_TOKEN="your-access-token"
```

```python
from pasqal_cloud import OVHConnection

connection = OVHConnection()
```
