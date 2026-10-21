# Target different regions and environments

## Access a different region

By default, the European (`fr`) platform is targeted. Available regions are `"fr"`
(default) and `"sa"` (Saudi-Arabia).

Select the region for both the SDK and the `pasqal-cloud` command with the
`PASQAL_CLOUD_REGION` environment variable:

```bash
export PASQAL_CLOUD_REGION=sa
pasqal-cloud auth login
```

```python
from pasqal_cloud import PasqalCloudConnection

connection = PasqalCloudConnection(project_id="your_project_id")  # targets sa
```

Or set it explicitly, which takes precedence over the environment variable: the
`--region` flag of the `pasqal-cloud` command, and the `region` argument in Python:

```bash
pasqal-cloud auth login --region sa
```

```python
connection = PasqalCloudConnection(project_id="your_project_id", region="sa")
```

## Target a non-production environment

This is intended for package developers or users who have been given access to non-prod
environments of the Pasqal cloud platform.

Select the environment (`prod` by default, `preprod` or `dev`) with the
`PASQAL_CLOUD_ENV` environment variable, for both the SDK and the `pasqal-cloud` command.
Example targeting the Saudi-Arabia preprod environment:

```bash
export PASQAL_CLOUD_ENV=preprod
pasqal-cloud auth login --region sa
```

```python
from pasqal_cloud import PasqalCloudConnection

connection = PasqalCloudConnection(project_id="your_project_id", region="sa")
```

Each environment has its own login. `pasqal-cloud auth status` lists your logins.

!!! note "Deprecated arguments"

    The `endpoints`, `auth_config` and `auth0` arguments are deprecated: use `region` /
    `PASQAL_CLOUD_REGION` and `PASQAL_CLOUD_ENV` instead.
