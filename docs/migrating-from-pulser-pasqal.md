Replace your `pulser_pasqal` imports with `pasqal_cloud`:

| `pulser_pasqal` (old) | `pasqal_cloud` (new) |
|---|---|
| `PasqalCloud` | `PasqalCloudConnection` |
| `OVHConnection` | `OVHConnection` |
| `EmuMPSBackend` | `EmuMPSBackend` |
| `EmuSVBackend` | `EmuSVBackend` |
| `EmuFreeBackendV2` | `EmuFreeBackend` |

For example:

```python
# Before
from pulser_pasqal import PasqalCloud

# After
from pasqal_cloud import PasqalCloudConnection
```

!!! note
    Most class names are unchanged. The exceptions are `PasqalCloud` → `PasqalCloudConnection` and `EmuFreeBackendV2` → `EmuFreeBackend`.
