from pasqal_cloud.pasqal_cloud_client import PasqalCloudClient

username = ""
project_id = "<project-uuid>"

sdk = PasqalCloudClient(username=username, project_id=project_id, region="fr")

sdk.get_batches()
