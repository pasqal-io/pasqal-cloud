import pytest

from unittest.mock import patch
from sdk import SDK

class TestAuth:
    @patch("sdk.client.getpass")
    def test_module_getpass_success(self, getpass):
        getpass.return_value = "password"
        SDK(group_id = "random", username="hi")
        getpass.assert_called_once()

    @patch("sdk.client.getpass")
    def test_module_getpass_no_password(self, getpass):
        getpass.return_value = ""
        
        with pytest.raises(Exception):
            SDK(group_id = "random", username="hi")
        
        getpass.assert_called_once()

    def test_authentication_success(self):
        user = "user"
        pwd = "password"
        SDK(group_id = "random", username=user, password=pwd)
    
    def test_authentication_no_credentials_provided(self):
        with pytest.raises(ValueError):
            SDK(group_id="random")
