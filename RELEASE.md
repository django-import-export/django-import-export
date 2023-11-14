## Release process

The existing manual release process has been replaced with Github Actions as part of the CI / CD workflow.
This has been implemented using [this guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)

#### Perform the release

To create a new published release, follow the instructions [here](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).
Ensure you create the new tag to correspond with the release as required.

1. Go to the [Releases](https://github.com/django-import-export/django-import-export/releases) page
2. Click 'Draft a new release'
3. Choose or create a new tag
4. Check 'Set as a pre-release' or 'Set as the latest release' as appropriate
5. Generate release notes if desired.
6. Click 'publish'

### Check readthedocs

Login to [readthedocs.org](https://readthedocs.org) to check that the build ran OK (click on 'Builds' tab).
