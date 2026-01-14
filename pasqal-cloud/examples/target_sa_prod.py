from pasqal_cloud import SDK

username = ""
project_id = "<project-uuid>"

sdk = SDK(username=username, region="saudi-arabia")

sdk.get_batches()
