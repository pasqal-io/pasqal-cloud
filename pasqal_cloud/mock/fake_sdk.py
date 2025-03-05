"""
This file exposes classes to help testing the integration with the pasqal cloud SDK
"""

from httpx import Client, MockTransport, Request, Response
from typing import Optional, Dict, Any, Union, List

from pasqal_cloud import SDK


class MockServer:
    def __init__(self):
        self.batches = {}
        self.jobs = {}

    @staticmethod
    def _jsend_format(data: Union[Dict[Any, Any], List]):
        return {
            "code": "200",
            "message": "OK",
            "status": "success",
            "data": data,
        }

    def request_handler(self, request: Request, *args):
        if "/api/v1/batches" in request.url.path:
            self.batches.append("coucou")
            return Response(status_code=200, content=self._jsend_format([]))


def default_test_client() -> Client:
    handler = None
    return Client(transport=MockTransport(handler))


def test_sdk(client: Optional[Client] = None) -> SDK:
    if client is None:
        pass
    pass
