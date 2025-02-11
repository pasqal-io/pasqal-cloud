There are several ways to authenticate using the SDK:

```python
from pasqal_cloud import SDK

project_id = "your_project_id"  # Replace this value with your project_id on the PASQAL platform. It can be found on the user-portal, in the 'project' section.
username = "your_username"  # Replace this value with your username or email on the PASQAL platform.
password = "your_password"  # Replace this value with your password on the PASQAL platform.
```

## Method 1: Username + Password

If you know your credentials, you can pass them to the SDK instance on creation:

```python
sdk = SDK(username=username, password=password, project_id=project_id)
```

## Method 2: Username only

If you only want to insert your username, but want a solution to have your password being secret,
you can run the SDK without a password. A prompt will then ask for your password:

```python
sdk = SDK(username=username, project_id=project_id)
```

## Method 3: Use a custom token provider

You can define a custom class to provide the token.
For example, if you have a token, you can use it to authenticate with our APIs:

```python
class CustomTokenProvider(TokenProvider):
    def get_token(self):
        return "your-token"  # Replace this value with your token


sdk = SDK(token_provider=CustomTokenProvider(), project_id=project_id)
```

Alternatively, create a custom `TokenProvider` that inherits from `ExpiringTokenProvider`.
You should define a custom '\_query_token' method which fetches your token.
See `Auth0TokenProvider` implementation for an example.
