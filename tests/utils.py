from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode
from uuid import UUID


def convert_to_serializable(value: Any) -> Any:
    """Convert values to a serializable format."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (List, Tuple)):
        return [convert_to_serializable(v) for v in value]
    if isinstance(value, Dict):
        return {k: convert_to_serializable(v) for k, v in value.items()}
    return value


def build_query_params(
    filters: Optional[Dict[str, Any]] = None,
    pagination_params: Optional[Dict[str, int]] = None,
) -> str:
    """Convert filters to a URL-encoded query parameter string.

    Encode query parameters using doseq=True to handle sequences
    correctly, it ensures that each element of a sequence
    is treated as a separate query parameter.
    """
    serialised_params = {}
    if filters:
        serialised_params.update(convert_to_serializable(filters))
    if pagination_params:
        serialised_params.update(pagination_params)
    # To avoid returning a single interrogation point without query parameters
    return "?" + urlencode(serialised_params, doseq=True) if serialised_params else ""
