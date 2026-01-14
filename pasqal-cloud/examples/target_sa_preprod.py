from pasqal_cloud import SDK
from pasqal_cloud.endpoints import AUTH_CONFIG, PASQAL_ENDPOINTS

username = ""
project_id = "<project-uuid>"

sdk = SDK(
    username=username,
    endpoints=PASQAL_ENDPOINTS["sa-preprod"],
    auth_config=AUTH_CONFIG["sa-preprod"],
)

sdk.get_batches()
