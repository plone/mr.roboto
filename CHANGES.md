# Changelog

## (unreleased)

- _nothing_

## 1.2.1 (2023-06-02)

- Revert last release.
  [gforcada]

## 1.2.0 (2023-06-02)

- Do not update `buildout.coredev` when a PR is merged
  if the commit message has `[ci-skip]` or `[ci skip]` on it.
  [gforcada]

## 1.1.2 (2023-05-30)

- Forgot another place where we still were referencing a mail related dependency.
  [gforcada]

## 1.1.1 (2023-05-30)

- Cleanup settings and dependencies related to mailing.
  [gforcada]

## 1.1.0 (2023-05-28)

- Stop sending emails when packages are not in `checkouts.cfg`
  [gforcada]

- Stop sending emails for each commit to `plone-cvs@lists.sourceforge.net`
  [gforcada]

## 1.0.3 (2023-05-28)

- Fix log parsing.
  [gforcada]

- Bump dependencies.
  [gforcada]

## 1.0.2 (2023-05-28)

- Remove `buildout.cfg` and clean up settings in `setup.cfg`.
  [gforcada]

- Play with GitHub workflows.
  [gforcada]

- The web hook that call directly to jenkins is only meant for `buildout.coredev`.
  Ensure that all other repositories do not get it.
  [gforcada]

## 1.0.1

- Add GHA to run the test suite and gather coverage info.
  [gforcada]

- Add GHA to lint our code.
  [gforcada]

## 1.0.0

- Plenty of features
  [plenty of contributors]
