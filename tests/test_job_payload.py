import json

import numpy as np
import pytest
from pasqal_cloud.job import create_jobs_to_api_payload, make_json_compatible


def test_make_json_compatible_handles_numpy_values():
    value = {
        "integer": np.int64(100),
        "floating": np.float32(1.5),
        "boolean": np.bool_(True),
        "array": np.array([1, 2]),
    }

    converted = make_json_compatible(value)

    assert converted == {
        "integer": 100,
        "floating": 1.5,
        "boolean": True,
        "array": [1, 2],
    }
    json.dumps(converted)


def test_make_json_compatible_rejects_unsupported_values():
    with pytest.raises(TypeError, match="Object of type set is not JSON serializable"):
        make_json_compatible({"runs": {10}})


def test_create_jobs_to_api_payload_makes_numpy_values_json_compatible():
    jobs = [
        {
            "runs": np.int64(1000),
            "variables": {
                "time": np.int64(100),
                "detuning": np.float32(1.5),
                "weights": np.array([1, 2]),
            },
            "serialized_sequence": "sequence",
        }
    ]

    payload = create_jobs_to_api_payload(jobs)

    assert payload == [
        {
            "runs": 1000,
            "variables": {
                "time": 100,
                "detuning": 1.5,
                "weights": [1, 2],
            },
            "sequence": "sequence",
        }
    ]
    json.dumps(payload)
