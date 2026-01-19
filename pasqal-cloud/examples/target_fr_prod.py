from pasqal_cloud import SDK

username = ""
project_id = "<project-uuid>"

sdk = SDK(username=username, region="france")

sdk.get_batches()
