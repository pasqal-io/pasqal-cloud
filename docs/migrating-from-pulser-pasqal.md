Replace your `pulser_pasqal` imports with `pasqal_cloud` and use the new classes names:

| `pulser_pasqal` (old) | `pasqal_cloud` (new) |
|---|---|
| `PasqalCloud` | `PasqalCloudConnection` |
| `OVHConnection` | `OVHConnection` |
| `EmuMPSBackend` | `RemoteMPSBackend` |
| `EmuSVBackend` | `RemoteSVBackend` |
| `EmuFreeBackendV2` | `RemoteFreeBackend` |

For example:

```python
# Before
from pulser_pasqal import PasqalCloud

# After
from pasqal_cloud import PasqalCloudConnection
```

!!! note
    Deprecated classes in `pulser-pasqal` were not migrated in `pasqal-cloud`, eg: `EmuFreeBackend` and `EmuTNBackend` aren't available anymore.
