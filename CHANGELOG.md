# Change Log

All notable changes to this project will be documented in this file.

## Next release

- Allow skipping the SSL certificate validation when making http requests in test environments by setting the `PASQAL_SKIP_SSL_VERIFY` env variable. Introduce `InsecureAuth0TokenProvider` to fetch a token from auth0 without SSL verification check.

## [0.20.3]

- Use `device_type` parameter to assign the device to the batch.
- Tags can be assigned to batches
- Filter batches by tag
- Add backend_configuration arg to create_batch for serialised configurations

## [0.20.2]

_release `2025-03-05`_

- Synchronizes the version with `pulser-pasqal`. From now on, both packages are released in tandem.
- Added `sdk.user_token()` method to obtain an auth token directly.

## [0.13.0]

_released `2025-02-25`_

### Added

- Drop support for Python 3.8 and update CI

### Changed

- Move documentation to a web-based site using MkDocs

## [0.12.7]

_released `2025-01-14`_

### ✨ Added

- Introduce EMU_MPS device type

## [0.12.6]

_released `2024-12-12`_

### ✨ Added

- Added 'cancel_batches' method, allowing to cancel a group of batches based on a list of batch ids

## [0.12.5]

_released `2024-11-12`_

### ✨ Added

- Added 'get_batches' method, a feature to retrieve a group of batches based on 'BatchFilters'

### Changed

- Now passing the wrong type for Filtering Jobs or Batches will raise a TypeError instead of a ValueError

## [0.12.4]

_released `2024-10-09`_

### Added

- Deprecation warnings on init of SDK, now each version of pasqal-cloud is supported for 1 year after release.
  If your version is not supported anymore you will get a deprecation warning each time you use the SDK.

## [0.12.3]

_released `2024-10-02`_

### Added

- Allow unauthenticated users to access public device specifications

## [0.12.2] - 2024-09-11

### Changed

- Now these methods are using V2 endpoints:
    - Cancel a batch
    - Cancel a job
    - Cancel a group of jobs
    - Add jobs to a batch
    - Close a batch

## [0.12.1] - 2024-09-11

### Added

- Introduce EMU_FRESNEL device type

## [0.12.0] - 2024-09-03

### Breaking change

- 'from pasqal_cloud' import has completely replaced the deprecated import 'from sdk'
- 'group_id' field is now removed, use 'project_id' field instead

## [0.11.4] - 2024-08-28

### Changed

A Batch that does not accept new jobs is now called "closed" instead of "complete". As a result:

- You should create an "open" batch using the "open" argument of the `create_batch` method instead of the `complete`
  argument.
- Close an open batch using the `close_batch` method of the SDK or `close` method of the `Batch` class. They are
  functionally equivalent to the now deprecated `complete_batch` and `declare_complete` functions.
- Batch dataclass parameter `complete` has been replaced by `open`.
- Using the deprecated method and arguments will now raise a warning.

## [0.11.3] - 2024-08-05

### Added

- Introduced the `User-Agent` header.

## [0.11.2] - 2024-07-31

### Added

- Introduced the 'cancel_jobs' method, a feature to cancel a group of jobs from a specific batch,
  based on 'CancelJobFilters'

## [0.11.0] - 2024-06-27

### Added

- Introduced a new filtering system using classes for more flexible and robust filtering options
- Added 'get_jobs' method, a feature to retrieve a group of jobs based on 'JobFilters'

### Breaking change

- Updated the 'rebatch' method to use 'RebatchFilters' for filtering jobs to retry,
  replacing the previous multiple filter parameters

## [0.10.1] - 2024-06-14

### Changed

- Use v2 endpoints for batches and jobs
- Jobs are now downloaded from s3 client-side

## [0.10.0] - 2024-06-05

### Changed

- Expose add_jobs and close_batch functions in the SDK interface
- Refactor non-private methods that were prefixed with \_
- Add test coverage for new functions
- Drop priority from Batch attributes

## [0.9.0] - 2024-05-15

### Changed

- Use the new authentication url: authenticate.pasqal.cloud

## [0.8.1] - 2024-04-15

### Added

- Add a retry mechanism to the HTTP requests on certain status codes
- Add some typehints and basic test descriptions

## [0.8.0] - 2024-04-15

### Added

- Added `strict_validation` option to emulators configuration.

## [0.7.1] - 2024-04-11

### Added

- Upgrading Pydantic requirement from V1.10.x to >= V2.6.0.
- Updated documentation.

## [0.7.0] - 2024-03-05

### Added

- Added feature to retry a job for an open batch.
- Added unit tests.
- Updated documentation.

## [0.6.0] - 2024-02-26

### Added

- Added feature to "rebatch" for a closed batch.
- Added `parent_id` param to batch and job.
- Updated documentation.

## [0.5.0] - 2024-02-05

### Added

- Added feature to create an "open" batch.
    - To create an open batch, set the `complete` argument to `True` in the `create_batch` method of the SDK.
    - To add jobs to an open batch, use the `add_jobs` method.
- Updated documentation to add examples to create open batches.
- The `wait` argument now waits for all the jobs to be terminated instead of waiting for the batch to be terminated.

## [0.4.3] - 2024-12-08

### Added

- CRUCIAL BUGFIX - download results properly from result link.
- Added exception case for results download.

## [0.4.2] - 2023-10-09

### Added

- Added new base error class to inject response context data in exception message.
- Added tests for new base error class.

### Changed

- Updated existing error to inherit from new response context exception class.

## [0.4.1] - 2023-10-09

### Added

- Added `result_link` field to `Workload` object.

### Changed

- `get_workload` now targets v2 of workloads endpoints.
- `result` is built from `result_link` where results are downloaded from temp s3 link.

## [0.4.0] - 2023-10-02

### Added

- Added exception classes for all possible failures (mostly related to client errors).
- Added try-catch to corresponding methods to raise proper error.

### Changed

- Use `raise_for_status` on response from client before returning `data` to get accurate exception.
- Bumped minor as new exceptions are raised.

### Removed

- Removed obsolete `HTTPError` and `LoginError` classes.

## [0.3.5] - 2023-07-21

### Added

Added an `ordered_jobs` list as an attribute to the `Batch` object in which jobs are ordered by creation date.

### Changed

Batch attribute `jobs` is now deprecated, use `ordered_jobs` instead.

## [0.3.4] - 2023-07-18

### Added

Workloads are now supported by the sdk with the create_workload, get_workload and cancel_workload methods.

## [0.3.3] - 2023-07-05

### Added

Reinstated the full functionality for the `fetch_results` argument as well as the corresponding test.

## [0.3.2] - 2023-07-03

### Added

Pre-commit hooks were added for the contributors of pasqal-cloud to enforce some code linting.

### Notes

Pins the dependency on `pydantic` to versions before v2.0 due to conflicts with the current code.

## [0.3.1] - 2023-06-22

### Added

- Added `ResultType` enum and `result_types` config option
- Added validation for result types

### Notes

Currently none of the devices can choose a different result type than `counter`,
hence the feature was not documented.

## [0.3.0] - 2023-06-20

### Added

- Added `full_result` attribute to `Job` schema for unformatted results.
- Updated documentation for `full_result`

### Changed

- `fetch_result` kwarg was removed from all internal functions as the results are by default included with the batch.
  It was marked as deprecated in public functions.
- Refactored to no longer return `batch_rsp` and `jobs_rsp` as the latter is systematically included in the former.
- Changed test payloads to reflect data returned by the api.

## [0.2.8] - 2023-06-19

### Changed

Fixed incorrect type hint of user IDs from int to str which was raising a validation exception when loading the data
returned by the API.

## [0.2.7] - 2023-06-08

### Added

Now you can get the environment configuration for `endpoints` and `auth0` of the SDK class with
`PASQAL_ENDPOINTS['env']`and `AUTH0_CONFIG['env']` with env being `prod`, `preprod` or `dev`.

### Changed

- Batch and Job dataclasses have been replaced by pydantic models, which gives more control to unserialize the API
  response data.
  The SDK is now more resilient to API changes, if a new field is added to the response of the API then the job and
  batch object instantiation will not raise an exception, meaning this SDK version will not become obsolete as soon as
  the API spec is updated.

## [0.2.6] - 2023-05-29

### Changed

"Groups" have been renamed as "Projects", hence URL endpoints and attribute names have been changed accordingly.
For example the `group_id` of a batch has been renamed to `project_id`.
Note that for backwards compatibility, the `group_id` is still exposed by the APIs as a duplicate of the `project_id`.

## [0.2.5] - 2023-04-24

### Added

- Cancel methods added to batches and jobs, from the object itself and the sdk
- Get a job method from sdk added

## [0.2.4] - 2023-04-20

### Changed

- Relax python dependencies version to prevent conflicts.

## [0.2.3] - 2023-04-20

### Fixed

- Fixed bug when using a custom TokenProvider to authenticate to Pasqal Cloud Services

### Changed

- Reorder documentation for clarity
- Clarify instructions to use a custom token provider for authentication

## [0.2.2] - 2023-04-19

### Changed

- Package renamed from **pasqal-sdk** to **pasqal-cloud**
- Import name renamed from **sdk** to **pasqal_cloud** (import sdk is now deprecated but still usable)

## [0.2.0] - 2023-04-06

### Changed

- `device_type` argument replace by `emulator` in sdk create_batch
- `DeviceType` replaced with `EmulatorType`

### Deleted

- QPU device type and related logic

## [0.1.15] - 2023-04-05

### Added

- Added tests to check the login behavior.
- Added tests to check the override Endpoints behavior.

### Changed

- The authentication now directly connects to the Auth0 platform instead of connecting through PasqalCloud.
- Small refactor of files, with the authentication modules in the `authentication.py` file, instead of `client.py`.

### Deleted

- Account endpoint, we now use Auth0.

## [0.1.14] - 2023-03-27

### Changed

- Added a get_device_specs_dict function to the sdk
- Updated Readme for the device specs

## [0.1.13] - 2023-03-02

### Changed

- The default values for the tensor network emulator were updated to better ones.
- the client_id and client_secret was leftover in the Client object even though they are no longer used.
- Updated the README to also supply the group_id which is mandatory.
- Updated the default endpoint to `/core-fast` in accordance with infra changes. All users should use `/core-fast` in
  all environments.
- The PCS APIs Client was refactored to accept any custom token provider for authentication. This can be used by users
  as an alternative to the username/password-based token provider.

## [0.1.12] - 2023-02-27

### Changed

- The group_id field has been added to the Job schema which is now present in some services returning Job data.
- Pytest fixtures updated to accommodate this.

## [0.1.11] - 2023-02-21

### Changed

- The authentication system has been reworked and is now connected to auth0. API keys have been removed
  hence you should now use your email and password to initialize the SDK (see example in Readme).

## [0.1.10] - 2023-02-09

### Added

### Changed

- A new device type, "EMU-TN", corresponding to tensor network-based emulator, was added. The "EMU_SV" type was removed
  as it is not available right now.

- A new version of the "core" microservice, using FastAPI instead of Flask as web framework, was released in the "dev"
  environment. If using the "dev" environment, you should upgrade the core endpoint you are using
  to "https://apis.dev.pasqal.cloud/core-fast"

## [0.1.9] - 2023-02-07

### Changed

- Changed typehints for id fields to be `str` rather than `int` to reflect the switch to `uuid` in our services.
- Updated tests to use UUID strings in the fixtures and tests

## [0.1.8] - 2023-01-31

### Changed

- Moved the device_types into device module
- Refactored configuration to be split into `BaseConfig`, `EmuSVConfig` and `EmuFreeConfig`, more device-specific
  configs can be added
- Refactored unit tests to use the proper Config model.
- Updated README with the new Configuration classes.

### Added

- `BaseConfig`: the base configuration class. A dataclass with the same methods as the former `Configuration` model and
  the `extra_config` param.
- `EmuSVConfig`: the configuration class for `DeviceType.EMU_SV`, inherits from `BaseConfig` with the parameters
  formerly found on `Configuration`.
- `EmuFreeConfig`: the configuration class for `DeviceType.EMU_FREE`, inherits from `BaseConfig` with the `with_noise`
  boolean parameter.

## [0.1.7] - 2023-01-04

### Changed

Reworked the `wait` logic
when [creating a batch](https://github.com/pasqal-io/pasqal-cloud/blob/dev/sdk/__init__.py#L46)
or [declaring it as complete](<(https://github.com/pasqal-io/pasqal-cloud/blob/dev/sdk/batch.py#L95)>). The old `wait`
has been split into
two separate boolean kwargs `wait` and `fetch_results`. - `wait` when set to `True` still makes the python statement
blocking until the batch gets assigned a termination status (e.g. `DONE`, `ERROR`, `TIMED_OUT`) but doesn't trigger
fetching of results. - `fetch_results` is a boolean which when set to `True` makes the python statement blocking until
the batch has a termination status and then fetches the results for all the jobs of the batch.

This enables the user to wait for the results and then implement its own custom logic to retrieve results (e.g. only
fetch the results for the last job of the batch).
This also fixes a bug where the user needed an extra call after the batch creation to the `get_batch` function to
retrieve results. Now results will be properly populated after batch creation when setting `fetch_results=True`.

### Fixed

## [0.1.6] - 2022-11-02

This is the last released version before the implementation of the changelog.

### Added

See commit history
before [this commit](https://github.com/pasqal-io/pasqal-cloud/commit/7c703534f55012489550f7df116f3f326e741de5).

### Changed

### Fixed

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).
