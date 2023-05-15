# mr.roboto

The main goal of mr.roboto is to make sure [Plone's Jenkins CI](http://jenkins.plone.org)
test every single change made by Plone developers.

This way not only Plone contributors will be promptly notified (by Jenkins) that a change broke the tests,
but at the same time,
and most importantly,
they will be able to know exactly what change broke the build.

## Use Cases

Notice that a few URLs below have `token` parameter,
for obvious reasons it is not shared here.

Ask the CI team for it, if you need to it.

### See log

To see the log that's being processed:

http://jenkins.plone.org/roboto/log?token=XXXXX

### Autoconfigure a single repository hooks

mr.roboto needs to get notified whenever a change has been made on a Plone core package,
so it can take all the necessary actions to ensure our CI system gets notified,
if needed,
and runs tests for certain Plone versions.

For that, mr.roboto needs to add a hook to all Plone Github repositories.

At the same time it removes all previously installed hooks to be sure no cruft is left behind.

To do so, call this URL:

http://jenkins.plone.org/roboto/run/githubcommithooks?token=XXXXX&repo=plone.batching

### Autoconfigure hooks

When a massive change on the hooks happens,
it is not practical to run the previous command for each repository.

Removing the `repo` parameter will install the hooks on all repositories.

To do so, call this URL:

http://jenkins.plone.org/roboto/run/githubcommithooks?token=XXXXX

### New commits on a core repository

The hook installed on all Plone GitHub repositories notify this end-point whenever a change happens in them.

This way mr.roboto can make all the needed actions to ensure our CI setup is notified and runs the necessary jobs.

The URL that's being called is:

http://jenkins.plone.org/roboto/run/corecommit?token=XXXXX

### Get sources and checkouts

For debugging purposes,
knowing what exactly mr.roboto has in its sources and checkouts can be really useful.

http://jenkins.plone.org/roboto/sources.json

http://jenkins.plone.org/roboto/checkouts.json

### Branches overview

Get an overview of which branch of each package is being used on any plone release.

http://jenkins.plone.org/roboto/branches

### Update sources and checkouts

If there is something wrong with sources or checkouts,
or they are empty (new deployment),
you can force them to be created:

http://jenkins.plone.org/roboto/update-sources-and-checkouts?token=XXX

## Development

To run mr.roboto locally,
do the following:

```shell
python3.11 -m venv .
. bin/activate
pip install pip-tools
pip-sync requirements-dev.txt
pip install -e src/mr.roboto
cp development.ini.sample development.ini
./bin/pserve development.ini --reload
```

_Happy hacking!_

### Test and QA

To run tests:

```shell
tox -e test
```

To format code and run QA tools:

```shell
tox -e format
tox -e lint
```

### Update dependencies

We use [`pip-tools`](https://pypi.org/project/pip-tools)
to pin all versions used by `mr.roboto`.

Now and then they need to be updated though,
to do so run the following commands:

```shell
python3.11 -m venv .
. bin/activate
pip install pip-tools
rm -f requirements*.txt
pip-compile requirements-app.in
pip-compile requirements-dev.in
```

After these steps,
look with `git diff` the changes on `requirements-dev.txt` and `requirements-app.txt`
and create a pull request to get the changes checked by GHA.


```mermaid
graph TD;
  "plone.app.relationfield" --> "plone.app.dexterity";
```
