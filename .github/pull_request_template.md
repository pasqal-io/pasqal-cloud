### Description

<!-- What has changed and why has it changed -->

#### Remaining Tasks

<!-- Tasks left to do, either in this PR or as future work -->

#### Related PRs in other projects

<!-- Links of others related PR to this one -->

#### Additional merge criteria

<!-- Here, add any extra criteria you consider mandatory for merging on top of the usual criteria -->

#### Breaking changes

<!-- Here, add all the breaking changes that this PR involves if there is any -->

### Checklist

- [ ] The title of the PR follows the right format (see the internal documentation).

#### Documentation

- [ ] Update the version of pasqal-cloud in `_version.py` following the changes in your PR and by using [semantic versioning](https://semver.org/).
- [ ] Update CHANGELOG.md with a description explaining briefly the changes to the users.

#### Tests

- [ ] Unit tests have been added or adjusted.
- [ ] Tests were run locally.

#### Internal tests pipeline
- [ ] Update the internal tests then launch them while targeting the branch of this PR.
 If your PR hasn't changed any functionality, it still needs to be validated against internal tests.

#### After merging

- [ ] Open a PR on the E2E that updates the version of the sdk used in dependencies.
