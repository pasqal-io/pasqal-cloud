# Target different regions and environments

## Access a different region

By default, the European (`fr`) platform is targeted. Available regions are `"fr"`
(default) and `"sa"` (Saudi-Arabia).

Each config profile targets one deployment. The built-in `default-fr` and `default-sa`
profiles target production. Activate one to select it for both the SDK and the
`pasqal-cloud` command:

```bash
pasqal-cloud profile activate default-sa
pasqal-cloud auth login
```

```python
from pasqal_cloud import PasqalCloudConnection

connection = PasqalCloudConnection(project_id="your_project_id")  # targets sa
```

In Python, the `region` argument selects the built-in profile of that region, even over
the active profile:

```python
connection = PasqalCloudConnection(project_id="your_project_id", region="sa")
```

Leave `region` out to use the active profile.

## Target a non-production environment

This is intended for package developers or users who have been given access to non-prod
environments of the Pasqal cloud platform.

Environments are described by config profiles, stored in `~/.pasqal/config.json`.
Create a profile for another environment, it prompts for its `issuer`,
`client_id`, `audience`, `core_url` and `account_url`:

```bash
pasqal-cloud profile create preprod-sa
```

Then select it like the built-in profiles, for example:

```bash
pasqal-cloud profile activate preprod-sa
pasqal-cloud auth login
```

```python
from pasqal_cloud import PasqalCloudConnection

connection = PasqalCloudConnection(project_id="your_project_id")
```

`pasqal-cloud profile show` shows the values of the active profile,
`pasqal-cloud profile edit <name>` changes them and
`pasqal-cloud profile list` lists the profiles.

Each profile has its own login. `pasqal-cloud auth status` lists the cached logins and
marks the one of the selected profile.

!!! note "Deprecated arguments"

    The `endpoints`, `auth_config` and `auth0` arguments are deprecated: use `region`
    and `pasqal-cloud profile` instead.
