from pasqal_cloud import SDK

username = ""
project_id = "<project-uuid>"

sdk = SDK(username=username, region="sa")

sdk.get_batches()
