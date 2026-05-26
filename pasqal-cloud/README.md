# pasqal-cloud

`pasqal-cloud` is a Python package to execute [Pulser](https://pypi.org/project/pulser/) sequences on [Pasqal](https://portal.pasqal.cloud) infrastructure.

## Installation

```bash
pip install pasqal-cloud
```

## Quickstart

```python
# Retrieve all QPU devices
devices = connection.fetch_available_devices()
device = devices["FRESNEL_CAN1"]

# Create a register of trapped atoms before performing operation on them
register = Register.square(5, 5).with_automatic_layout(device)

# Declare the sequence of pulses to perform on the register
sequence = Sequence(register, device)
sequence.declare_channel("rydberg", "rydberg_global")
omega_max = sequence.declare_variable("omega_max")

# Add a pulse to that channel with the amplitude omega_max
generic_pulse = Pulse.ConstantPulse(100, omega_max, 2, 0.0)
sequence.add(generic_pulse, "rydberg")

# Declare a backend based on the sequence and remote connection
backend = QPUBackend(sequence=sequence, connection=connection)

# Run jobs with different arguments over the same sequence and register
results = backend.run(
    job_params=[
        {"runs": 5, "variables": {"omega_max": 12}},
        {"runs": 10, "variables": {"omega_max": 6}},
    ],
    wait=True,
)
print(results.results)
```

## Documentation

For full usage guides, authentication options, emulator configuration, and API reference,
visit the [Github Pages documentation](https://pasqal-io.github.io/pasqal-cloud/)
or the **[Pasqal documentation](https://docs.pasqal.com/cloud/pasqal-cloud/)**.
