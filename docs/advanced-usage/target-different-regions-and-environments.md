# Target different regions and environments

## Access a different region

By default, the connection targets the European (`fr`) platform. To access the
Saudi-Arabia (`sa`) platform, pass the `region` parameter:

```python
from pasqal_cloud import PasqalCloudConnection

connection = PasqalCloudConnection(..., region="sa")
```

Available regions are `"fr"` (default) and `"sa"`.


## Target a non-production environment

This is intended for package developers or users who have been given access to non-prod
environments of the Pasqal cloud platform.

To target a specific environment (`preprod` or `dev`), instantiate the connection
by passing `endpoints` with a value from `pasqal_cloud.endpoints.PASQAL_ENDPOINTS`
and `auth_config` with a value from `pasqal_cloud.endpoints.AUTH_CONFIG`.

The keys follow the format `<region>-<env>` (e.g. `fr-preprod`, `fr-dev`, `sa-preprod`).

Example targeting the European preprod environment:

```python
from pasqal_cloud import PasqalCloudConnection
from pasqal_cloud.endpoints import PASQAL_ENDPOINTS, AUTH_CONFIG

connection = PasqalCloudConnection(
  ...,
  endpoints=PASQAL_ENDPOINTS["fr-preprod"],
  auth_config=AUTH_CONFIG["fr-preprod"]
)
```

Example targeting the Saudi-Arabia preprod environment:

```python
from pasqal_cloud import PasqalCloudConnection
from pasqal_cloud.endpoints import PASQAL_ENDPOINTS, AUTH_CONFIG

connection = PasqalCloudConnection(
  ...,
  endpoints=PASQAL_ENDPOINTS["sa-preprod"],
  auth_config=AUTH_CONFIG["sa-preprod"]
)
```
