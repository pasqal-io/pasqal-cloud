from pasqal_cloud import SDK
from pasqal_cloud.device import EmulatorType

project_id = (
    "your_project_id"  # Replace this value by your project_id on the PASQAL platform.
)
username = "your_username"  # Replace this value by your username or email on the PASQAL platform.
password = (
    "your_password"  # Replace this value by your password on the PASQAL platform.
)

# Initialize the cloud client
sdk = SDK(username=username, password=password, project_id=project_id)

# When creating a job, select a number of runs and set the desired values for the variables
# defined in the sequence
job1 = {"runs": 20, "variables": {"omega_max": 6}}
job2 = {"runs": 50, "variables": {"omega_max": 10.5}}

# You can also choose to run your batch on an emulator using the optional argument 'emulator'
# For using a basic single-threaded QPU emulator that can go up to 10 qubits, you can specify the "EMU_FREE" emulator.
batch = sdk.create_batch(
    serialized_sequence, [job1, job2], emulator=EmulatorType.EMU_FREE
)

# Once the QPU has returned the results, you can access them with the following:
for job in batch.ordered_jobs:
    print(f"job-id: {job.id}, status: {job.status}, result: {job.result}")
