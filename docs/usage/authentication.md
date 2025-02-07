To authenticate with the [`SDK`][pasqal_cloud.SDK], you need to enter the credentials of your account as well as a project ID you are a member of. The jobs created with the SDK will then be billed to this project.

There are several ways to authenticate using the SDK:

```python
from pasqal_cloud import SDK

project_id = "your_project_id"  # Replace this value with your project_id on the Pasqal platform. It can be found on the user-portal, in the 'project' section.
username = "your_username"  # Replace this value with your username or email on the Pasqal platform.
```

## Method 1: Username + Password

Authenticate with the SDK with your email and password directly:

```python
password = "your_password"  # Replace this value with your password on the Pasqal platform.
sdk = SDK(username=username, password=password, project_id=project_id)
```

!!! warning

    Never put your password directly in code. Use environment variables
    to avoid leaking passwords by mistake when pushing your code.

## Method 2: Interactive

The password can be omitted from the arguments. You will be prompted to input your password directly in your terminal when running your script.
This method is an alternative to setting your password as an environment variable when running your script manually.

```python
sdk = SDK(username=username, project_id=project_id)
```

## Method 3: Use a custom token provider (developers only)

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
