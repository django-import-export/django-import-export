## Release process

#### Pre-release

Ensure that ``CHANGELOG.rst`` is up-to-date with the correct version number and release date.

#### Perform the release

To create a new published release, follow the instructions [here](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).
Ensure you create the new tag to correspond with the release as required.

1. Go to the [Releases](https://github.com/django-import-export/django-import-export/releases) page
2. Click 'Draft a new release'
3. Choose or create a new tag
4. Choose the desired branch (if not `main`)
5. Check 'Set as a pre-release' or 'Set as the latest release' as appropriate
6. Generate release notes if desired.
7. Click 'Publish release'

The `release` github workflow will run and publish the release binaries to both test.pypi.org and pypi.org.

### Check readthedocs

[readthedocs](https://readthedocs.org/projects/django-import-export/) integration is used to publish documentation.
The webhook endpoint on readthedocs is configured using
[these instructions](https://docs.readthedocs.io/en/latest/guides/setup/git-repo-manual.html).

This is implemented using a Webhook defined in the Github repo (Settings / Webhooks).

readthedocs should be checked after each release to ensure that the docs have built correctly.
Login to [readthedocs.org](https://readthedocs.org) to check that the build ran OK (click on 'Builds' tab).
