# Change Log

All notable changes to this project will be documented in this file.

## [0.2.0]

### Changed

- Package renamed from **cloud-sdk** to **pasqal-cloud**
- Import name renamed from **sdk** to **pasqal_cloud** (import sdk is now deprecated but still usable)

## [0.1.16] 2023-04-06

### Changed

    - `device_type` argument replace by `emulator` in sdk create_batch
    - `DeviceType` replaced with `EmulatorType`

### Deleted

    - QPU device type and related logic

## [0.1.15] 2023-03-27

### Added
- Added tests to check the login behavior.
- Added tests to check the override Endpoints behavior.

### Changed
- The authentication now directly connects to the Auth0 platform instead of connecting through PasqalCloud.
- Small refactor of files, with the authentication modules in the `authentication.py` file, instead of `client.py`.

### Deleted
- Account endpoint, we now use Auth0.

## [0.1.14]

### Changed

- Added a get_device_specs_dict function to the sdk
- Updated Readme for the device specs

## [0.1.13]

### Changed

- The default values for the tensor network emulator were updated to better ones.
- the client_id and client_secret was leftover in the Client object even though they are no longer used.
- Updated the README to also supply the group_id which is mandatory.
- Updated the default endpoint to `/core-fast` in accordance with infra changes. All users should use `/core-fast` in all environments.
- The PCS APIs Client was refactored to accept any custom token provider for authentication. This can be used by users as an alternative to the username/password-based token provider.

## [0.1.12] - 2023-02-27

### Changed

- The group_id field has been added to the Job schema which is now present in some services returning Job data.
- Pytest fixtures updated to accomodate this.

## [0.1.11] - 2023-02-21

### Changed

- The authentication system has been reworked and is now connected to auth0. API keys have been removed
  hence you should now use your email and password to initialize the SDK (see example in Readme).

## [0.1.10] - 2023-02-09

### Added

### Changed

- A new device type, "EMU-TN", corresponding to tensor network-based emulator, was added. The "EMU_SV" type was removed as it is not available right now.

- A new version of the "core" microservice, using FastAPI instead of Flask as web framework, was released in the "dev" environment. If using the "dev" environment, you should upgrade the core endpoint you are using to "https://apis.dev.pasqal.cloud/core-fast"

## [0.1.9] - 2023-02-07

### Changed

- Changed typehints for id fields to be `str` rather than `int` to reflect the switch to `uuid` in our services.
- Updated tests to use UUID strings in the fixtures and tests

## [0.1.8] - 2023-01-31

### Changed

- Moved the device_types into device module
- Refactored configuration to be split into `BaseConfig`, `EmuSVConfig` and `EmuFreeConfig`, more device-specific configs can be added
- Refactored unit tests to use the proper Config model.
- Updated README with the new Configuration classes.

### Added

- `BaseConfig`: the base configuration class. A dataclass with the same methods as the former `Configuration` model and the `extra_config` param.
- `EmuSVConfig`: the configuration class for `DeviceType.EMU_SV`, inherits from `BaseConfig` with the parameters formerly found on `Configuration`.
- `EmuFreeConfig`: the configuration class for `DeviceType.EMU_FREE`, inherits from `BaseConfig` with the `with_noise` boolean parameter.

## [0.1.7] - 2023-01-04

### Changed

Reworked the `wait` logic when [creating a batch](https://github.com/pasqal-io/pasqal-cloud/blob/dev/sdk/__init__.py#L46) or [declaring it as complete](<(https://github.com/pasqal-io/pasqal-cloud/blob/dev/sdk/batch.py#L95)>). The old `wait` has been split into
two separate boolean kwargs `wait` and `fetch_results`. - `wait` when set to `True` still makes the python statement blocking until the batch gets assigned a termination status (e.g. `DONE`, `ERROR`, `TIMED_OUT`) but doesn't trigger fetching of results. - `fetch_results` is a boolean which when set to `True` makes the python statement blocking until the batch has a termination status and then fetches the results for all the jobs of the batch.

This enables the user to wait for the results and then implement its own custom logic to retrieve results (e.g. only fetch the results for the last job of the batch).
This also fixes a bug where the user needed an extra call after the batch creation to the `get_batch` function to retrieve results. Now results will be properly populated after batch creation when setting `fetch_results=True`.

### Fixed

## [0.1.6] - 2022-11-02

This is the last released version before the implementation of the changelog.

### Added

See commit history before [this commit](https://github.com/pasqal-io/pasqal-cloud/commit/7c703534f55012489550f7df116f3f326e741de5).

### Changed

### Fixed

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).
