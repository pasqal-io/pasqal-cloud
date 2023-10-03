### Description

<!-- What has changed and why has it changed -->

#### Remaining Tasks

<!-- Tasks left to do, either in this MR or as future work -->

#### Related MRs in other projects

<!-- Links of other related MR to this one -->

#### Additional merge criteria

<!-- Here, add any extra criteria you consider mandatory for merging on top of the usual criteria -->

#### Breaking changes

<!-- Here, add all the breaking changes that this MR involves if there is any -->

### Checklist

- [ ] Title of the MR follows the right format (see the internal documentation).

#### Documentation

- [ ] Update the version of pasqal-cloud in `_version.py` following the changes your MR implies. We use an **x**.**y**.**z** versioning, where **x** is not used yet, **y** for a breaking change and **z** for a new feature, bug correction or minor change.
- [ ] Update CHANGELOG.md with a description explaining briefly the changes to the users without using technical vocabulary.

#### Tests

- [ ] Unit tests have been added or adjusted.
- [ ] Local setup was done & tests were run locally.

#### E2E tests
- [ ] In case your MR changes the current logic, update the E2E tests and then launch them while targeting the branch of this MR.
If it is not changing the current code functioning, test the branch of your MR with the E2E to make sure nothing is broken.

#### After merging

- [ ] Open an MR on the E2E that updates the version of the sdk used in dependencies.
