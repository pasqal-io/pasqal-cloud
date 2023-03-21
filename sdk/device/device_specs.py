import json
from typing import Any, Dict, List

from pydantic import BaseModel, validator

from sdk.device.device_types import DeviceType


class DeviceSpecs(BaseModel):

    device_type: DeviceType
    specs: Dict[str, Any]

    @validator("specs", pre=True)
    def _convert_specs_to_dict(cls, v):
        return json.loads(v)


class DeviceSpecsList(BaseModel):

    device_specs_list: List[DeviceSpecs]
