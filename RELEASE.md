## Release process

The existing manual release process has been replaced with Github Actions as part of the CI / CD workflow.
This has been implemented using [this guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)

#### Perform the release

Now the release will be triggered on any commit to main and uploaded to TestPypi.
If the release is tagged, then a release to Pypi will occur.

To create a new published release, follow the instructions [here](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).
Ensure you create the new tag to correspond with the release as required.
