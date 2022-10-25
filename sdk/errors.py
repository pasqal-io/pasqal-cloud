# Copyright 2020 Pasqal Cloud Services development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import json

from sdk.utils.jsend import JSendPayload


class HTTPError(Exception):
    code: int
    message: str
    description: str
    details: JSendPayload

    def __init__(self, data: JSendPayload, *args: object) -> None:
        super().__init__(*args)
        self.code = data["code"]
        # If no error description, display default response message instead
        if data.get("data"):
            self.description = data["data"].get("description", data["message"])
        else:
            self.description = data["message"]
        self.details = data

    def __str__(self) -> str:
        return (
            f"Error {self.code}: {self.description}\n"
            f"Details: {json.dumps(self.details, indent=2)}"
        )
