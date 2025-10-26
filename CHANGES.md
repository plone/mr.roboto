# Changelog

## 1.2.12 (unreleased)

- Run tests with Python 3.12 @gforcada

- Split subscriber module @gforcada

- Use `plone.releaser`'s `add-checkout` command to update `checkouts.cfg` file @gforcada

## 1.2.11 (2025-09-08)

- Do not ask for contributors agreement or changelog entries for bots @mauritsvanrees

## 1.2.10 (2025-05-29)

- Ignore weblate user on contributing agreement check (2nd change) @erral @fredvd

- Add locally added debug patch on the live server for #168 to git. @fredvd

## 1.2.9 (2025-03-31)

- Ignore weblate user on contributing agreement check @mauritsvanrees

## 1.2.8 (2024-10-25)

- Improve wording @davisagli @stevepiercy

## 1.2.7 (2024-09-15)

- Do not add Jenkins comment on plone.releaser PRs @mauritsvanrees

- Bump dependencies @gforcada

## 1.2.6 (2023-10-14)

- Bump dependencies @gforcada

## 1.2.5 (2023-09-16)

- Bump dependencies @gforcada

## 1.2.4 (2023-06-04)

- Bump dependencies @gforcada

## 1.2.3 (2023-06-02)

- Get the merge commit rather than the last commit on the PR @gforcada

## 1.2.2 (2023-06-02)

- Re-apply and fix the changes from 1.2.0 @gforcada

## 1.2.1 (2023-06-02)

- Revert last release @gforcada

## 1.2.0 (2023-06-02)

- Do not update `buildout.coredev` when a PR is merged
  if the commit message has `[ci-skip]` or `[ci skip]` on it @gforcada

## 1.1.2 (2023-05-30)

- Forgot another place where we still were referencing a mail related dependency @gforcada

## 1.1.1 (2023-05-30)

- Cleanup settings and dependencies related to mailing @gforcada

## 1.1.0 (2023-05-28)

- Stop sending emails when packages are not in `checkouts.cfg` @gforcada

- Stop sending emails for each commit to `plone-cvs@lists.sourceforge.net` @gforcada

## 1.0.3 (2023-05-28)

- Fix log parsing @gforcada

- Bump dependencies @gforcada

## 1.0.2 (2023-05-28)

- Remove `buildout.cfg` and clean up settings in `setup.cfg` @gforcada

- Play with GitHub workflows @gforcada

- The web hook that call directly to jenkins is only meant for `buildout.coredev`.
  Ensure that all other repositories do not get it @gforcada

## 1.0.1

- Add GHA to run the test suite and gather coverage info @gforcada

- Add GHA to lint our code @gforcada

## 1.0.0

- Plenty of features by plenty of contributors
