"""Backward-compatibility re-exports from pasqal_cloud.

All symbols listed here used to be importable from `pasqal_cloud` directly.
They are still available for now, but **will be removed from the root
``pasqal_cloud`` namespace in a future release**.  Please update your imports
to point to the canonical module instead (shown in the deprecation warning).
"""

import warnings
from typing import Any

# Mapping of deprecated names → (canonical module path, object name)
_DEPRECATED_EXPORTS: dict[str, tuple[str, str]] = {
    # authentication
    "TokenProvider": ("pasqal_cloud.authentication", "TokenProvider"),
    # batch
    "RESULT_POLLING_INTERVAL": ("pasqal_cloud.batch", "RESULT_POLLING_INTERVAL"),
    "Batch": ("pasqal_cloud.batch", "Batch"),
    # client
    "Client": ("pasqal_cloud.client", "Client"),
    # device
    "BaseConfig": ("pasqal_cloud.device", "BaseConfig"),
    "DeviceTypeName": ("pasqal_cloud.device", "DeviceTypeName"),
    "EmulatorType": ("pasqal_cloud.device", "EmulatorType"),
    # endpoints
    "AUTH0_CONFIG": ("pasqal_cloud.endpoints", "AUTH0_CONFIG"),
    "PASQAL_ENDPOINTS": ("pasqal_cloud.endpoints", "PASQAL_ENDPOINTS"),
    "Auth0Conf": ("pasqal_cloud.endpoints", "Auth0Conf"),
    "Endpoints": ("pasqal_cloud.endpoints", "Endpoints"),
    "Region": ("pasqal_cloud.endpoints", "Region"),
    "TokenProviderConf": ("pasqal_cloud.endpoints", "TokenProviderConf"),
    # errors
    "BatchCancellingError": ("pasqal_cloud.errors", "BatchCancellingError"),
    "BatchClosingError": ("pasqal_cloud.errors", "BatchClosingError"),
    "BatchCreationError": ("pasqal_cloud.errors", "BatchCreationError"),
    "BatchFetchingError": ("pasqal_cloud.errors", "BatchFetchingError"),
    "BatchSetTagsError": ("pasqal_cloud.errors", "BatchSetTagsError"),
    "DeviceSpecsFetchingError": ("pasqal_cloud.errors", "DeviceSpecsFetchingError"),
    "InvalidDeviceTypeSet": ("pasqal_cloud.errors", "InvalidDeviceTypeSet"),
    "JobCancellingError": ("pasqal_cloud.errors", "JobCancellingError"),
    "JobCreationError": ("pasqal_cloud.errors", "JobCreationError"),
    "JobFetchingError": ("pasqal_cloud.errors", "JobFetchingError"),
    "OnlyCompleteOrOpenCanBeSet": (
        "pasqal_cloud.errors",
        "OnlyCompleteOrOpenCanBeSet",
    ),
    "ProjectFetchingError": ("pasqal_cloud.errors", "ProjectFetchingError"),
    "ProjectNotFoundError": ("pasqal_cloud.errors", "ProjectNotFoundError"),
    "RebatchError": ("pasqal_cloud.errors", "RebatchError"),
    "WorkloadCancellingError": ("pasqal_cloud.errors", "WorkloadCancellingError"),
    "WorkloadCreationError": ("pasqal_cloud.errors", "WorkloadCreationError"),
    "WorkloadFetchingError": ("pasqal_cloud.errors", "WorkloadFetchingError"),
    # job
    "CreateJob": ("pasqal_cloud.job", "CreateJob"),
    "Job": ("pasqal_cloud.job", "Job"),
    # project
    "Project": ("pasqal_cloud.project", "Project"),
    # sdk
    "SDK": ("pasqal_cloud.sdk", "SDK"),
    # utils.constants
    "BatchStatus": ("pasqal_cloud.utils.constants", "BatchStatus"),
    "JobStatus": ("pasqal_cloud.utils.constants", "JobStatus"),
    "QueuePriority": ("pasqal_cloud.utils.constants", "QueuePriority"),
    # utils.filters
    "BatchFilters": ("pasqal_cloud.utils.filters", "BatchFilters"),
    "CancelJobFilters": ("pasqal_cloud.utils.filters", "CancelJobFilters"),
    "JobFilters": ("pasqal_cloud.utils.filters", "JobFilters"),
    "PaginationParams": ("pasqal_cloud.utils.filters", "PaginationParams"),
    "RebatchFilters": ("pasqal_cloud.utils.filters", "RebatchFilters"),
    # utils.responses
    "BatchCancellationResponse": (
        "pasqal_cloud.utils.responses",
        "BatchCancellationResponse",
    ),
    "JobCancellationResponse": (
        "pasqal_cloud.utils.responses",
        "JobCancellationResponse",
    ),
    "PaginatedResponse": ("pasqal_cloud.utils.responses", "PaginatedResponse"),
    # workload
    "Workload": ("pasqal_cloud.workload", "Workload"),
}


def __getattr__(name: str) -> Any:
    if name in _DEPRECATED_EXPORTS:
        module_path, attr = _DEPRECATED_EXPORTS[name]
        warnings.warn(
            f"Importing '{name}' from 'pasqal_cloud' is deprecated and will be "
            "removed in a future release. "
            f"Please use 'from {module_path} import {attr}' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
