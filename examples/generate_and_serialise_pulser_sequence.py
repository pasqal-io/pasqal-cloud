from pulser import Pulse, Register, Sequence
from pulser.devices import Chadoq2

# Define a register for your sequence
register = Register.square(2, spacing=5, prefix="q")
# Create a sequence for that register
sequence = Sequence(register, Chadoq2)
# Add a channel to your sequence
sequence.declare_channel("rydberg", "rydberg_global")
# Declare a variable
omega_max = sequence.declare_variable("omega_max")
# Add a pulse to that channel with the amplitude omega_max
generic_pulse = Pulse.ConstantPulse(100, omega_max, 2, 0.0)
sequence.add(generic_pulse, "rydberg")

# When you are done building your sequence, serialize it into a string
serialized_sequence = sequence.to_abstract_repr()
