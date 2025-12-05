from pasqal_cloud import SDK, Endpoints
from pasqal_cloud.authentication import KeycloakTokenProvider, KeycloakConf
import os

os.environ["REQUESTS_CA_BUNDLE"] = "/opt/homebrew/etc/ca-certificates/cert.pem"

username = "TODO"
password = "TODO"
keycloack_config = KeycloakConf()

token_provider = KeycloakTokenProvider(username, password, keycloack_config)

sdk = SDK(
    token_provider=token_provider,
    endpoints=Endpoints(
        core="https://apis-127-0-0-1.nip.io/core-fast",
        account="https://apis-127-0-0-1.nip.io/account/",
    ),
)

print("my token:", sdk.user_token())
