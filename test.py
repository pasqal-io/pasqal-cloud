import os
import requests
import base64
import hashlib
from urllib.parse import urlparse, parse_qs

# Auth0 Configuration
AUTH0_DOMAIN = "pasqal-dev.eu.auth0.com"
CLIENT_ID = "5QtfSu1UV118Iz6By6IJRSNoDrLbAiOv"
REDIRECT_URI = "https://portal.dev.pasqal.cloud"
AUTHORIZATION_ENDPOINT = f"https://{AUTH0_DOMAIN}/authorize"
TOKEN_ENDPOINT = f"https://{AUTH0_DOMAIN}/oauth/token"


# Helper function to generate code verifier and challenge
def generate_code_verifier_and_challenge():
    code_verifier = (
        base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8").replace("=", "")
    )
    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = (
        base64.urlsafe_b64encode(code_challenge).decode("utf-8").replace("=", "")
    )
    return code_verifier, code_challenge


code_verifier, code_challenge = generate_code_verifier_and_challenge()

# Step 1: User Authorization Request
params = {
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": "openid profile email",
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
}

authorization_url = (
    requests.Request("GET", AUTHORIZATION_ENDPOINT, params=params).prepare().url
)
print("Please go to the following URL and authorize:", authorization_url)

# Step 2: Prompt for Callback URL
callback_url = input("Please enter the full callback URL you were redirected to: ")

# Extract the code from the callback URL
parsed_url = urlparse(callback_url)
query_params = parse_qs(parsed_url.query)
code = query_params.get("code")[0] if "code" in query_params else None

if not code:
    print("No code found in the URL. Please ensure you copied the URL correctly.")
else:
    # Step 3: Exchange code for a token
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code_verifier": code_verifier,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    token_response = requests.post(TOKEN_ENDPOINT, data=data)
    tokens = token_response.json()
    if "access_token" in tokens:
        print("Access Token:", tokens["access_token"])
    else:
        print("Failed to obtain access token:", tokens.get("error", "Unknown error"))
