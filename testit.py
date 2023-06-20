from pasqal_cloud import Auth0Conf, Endpoints, SDK, EmulatorType
from pulser.devices._devices import Chadoq2
from pulser.pulse import Pulse
from pulser.register.register import Register
from pulser.sequence.sequence import Sequence

endpoints = Endpoints(
    core="https://apis.dev.pasqal.cloud/core-fast",
)

auth0conf = Auth0Conf(
    domain="pasqal-dev.eu.auth0.com",
    public_client_id="5QtfSu1UV118Iz6By6IJRSNoDrLbAiOv",
    audience="https://apis.dev.pasqal.cloud/account/api/v1",
    realm="pcs-users",
)

sdk = SDK(
    project_id="72e65e92-ab57-4ef2-b184-ad49ac7d94a0",
    username="bat@goodguy.com",
    password="super_secret",
    endpoints=endpoints,
    auth0=auth0conf,
)


def non_parametrized_sequence():
    """A non-parametrized sequence with 2 constant pulses.

    The sequence is serialized to JSON and returned.
    Used to test the execution time of a job emulation.
    """
    reg = Register.square(2, prefix="q")
    seq = Sequence(reg, Chadoq2)

    seq.declare_channel("analog", "rydberg_local")

    const_pulse1 = Pulse.ConstantPulse(duration=200, amplitude=2, detuning=10, phase=0)
    const_pulse2 = Pulse.ConstantPulse(duration=400, amplitude=4, detuning=-10, phase=0)

    seq.target("q0", "analog")
    seq.add(const_pulse1, "analog")
    seq.add(const_pulse2, "analog")

    serialized_seq = seq.to_abstract_repr(seq_name="test-sequence")
    return serialized_seq


batch = sdk.create_batch(
    serialized_sequence=non_parametrized_sequence(),
    jobs=[{"runs": 100, "name": "test-job"}],
    emulator=EmulatorType.EMU_FREE,
    wait=True,
)

for job in batch.jobs.values():
    print(job.result)
    print(job.full_result)
