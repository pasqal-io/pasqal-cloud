# Change Log

All notable changes to this project will be documented in this file.

## [Unreleased] - yyyy-mm-dd

Here we write upgrading notes for brands. It's a team effort to make them as
straightforward as possible.

### Added

### Changed

- A new version of the "core" microservice, using FastAPI instead of Flask as web framework, was released in the "dev" environment. If using the "dev" environment, you should upgrade the core endpoint you are using to "https://apis.dev.pasqal.cloud/core-fast"

## [0.1.8] - 2023-01-31

### Changed

- Moved the device_types into utils
- Refactored configuration to be split into `BaseConfig`, `EmuSVConfig` and `EmuFreeConfig`, more device-specific configs can be added
- Refactored unit tests to use the proper Config model.
- Updated README with the new Configuration classes.

### Added

- `BaseConfig`: the base configuration class. A dataclass with the same methods as the former `Configuration` model and the `extra_config` param.
- `EmuSVConfig`: the configuration class for `DeviceType.EMU_SV`, inherits from `BaseConfig` with the parameters formerly found on `Configuration`.
- `EmuFreeConfig`: the configuration class for `DeviceType.EMU_FREE`, inherits from `BaseConfig` with the `with_noise` boolean parameter.

## [0.1.7] - 2023-01-04

### Changed

Reworked the `wait` logic when [creating a batch](https://github.com/pasqal-io/cloud-sdk/blob/dev/sdk/__init__.py#L46) or [declaring it as complete](<(https://github.com/pasqal-io/cloud-sdk/blob/dev/sdk/batch.py#L95)>). The old `wait` has been split into
two separate boolean kwargs `wait` and `fetch_results`. - `wait` when set to `True` still makes the python statement blocking until the batch gets assigned a termination status (e.g. `DONE`, `ERROR`, `TIMED_OUT`) but doesn't trigger fetching of results. - `fetch_results` is a boolean which when set to `True` makes the python statement blocking until the batch has a termination status and then fetches the results for all the jobs of the batch.

This enables the user to wait for the results and then implement its own custom logic to retrieve results (e.g. only fetch the results for the last job of the batch).
This also fixes a bug where the user needed an extra call after the batch creation to the `get_batch` function to retrieve results. Now results will be properly populated after batch creation when setting `fetch_results=True`.

### Fixed

## [0.1.6] - 2022-11-02

This is the last released version before the implementation of the changelog.

### Added

See commit history before [this commit](https://github.com/pasqal-io/cloud-sdk/commit/7c703534f55012489550f7df116f3f326e741de5).

### Changed

### Fixed

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).
