This is intended for the package developers or users which were given access to non-prod
environments of the Pasqal cloud platform.

To target a specific environment (`prod`, `preprod` or `dev`), instantiate the connection
by passing `endpoints` with a value from `pasqal_cloud.endpoints.PASQAL_ENDPOINTS`
and `auth_config` with a value from `pasqal_cloud.endpoints.AUTH_CONFIG`.

Example:

```python
from pasqal_cloud import PasqalCloudConnection
from pasqal_cloud.endpoints import PASQAL_ENDPOINTS, AUTH_CONFIG

connection = PasqalCloudConnection(
  ...,
  endpoints=PASQAL_ENDPOINTS["preprod"],
  auth_config=AUTH_CONFIG["preprod"]
)
```

By default, the targeted environment is `prod`.


## Access Saudi-Arabia platform

```python
connection = PasqalCloudConnection(
  ...,
  endpoints=PASQAL_ENDPOINTS["sa-preprod"],
  auth_config=AUTH_CONFIG["sa-preprod"]
)
```
