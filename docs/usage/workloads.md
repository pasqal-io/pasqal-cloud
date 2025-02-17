A workload is a unit of work to be executed on Pasqal Cloud Services infrastructure.

## Create a workload

To submit a new workload, select a type, target one of the available
backends and provide a configuration object to execute it.

You can create a [`Workload`][pasqal_cloud.Workload] through the [`SDK`][pasqal_cloud.SDK] with the following command:

```python
workload = sdk.create_workload(workload_type="<WORKLOAD_TYPE>", backend="<BACKEND>", config={"config_param_1": "value"})
```

You can cancel the workload by doing:

```python
sdk.cancel_workload(workload.id)
```

Or refresh the workload status/results by with the following:

```python
workload = sdk.get_workload(workload.id)
```

Once the workload has been processed, you can fetch the result like this:

```python
print(f"workload-id: {workload.id}, status: {workload.status}, result: {workload.result}")
```
