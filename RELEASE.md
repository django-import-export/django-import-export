## Release process

The existing manual release process has been replaced with Github Actions as part of the CI / CD workflow.
This has been implemented using [this guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)

#### Perform the release

To create a new published release, follow the instructions [here](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).
Ensure you create the new tag to correspond with the release as required.

#### Workflow

- When any commit is pushed to the 'main' branch this will cause the 'release' workflow to be run.
  - This will upload the release files to TestPyPI.
  - The release version will be determined from the git commit log.
  - When a published release is identified (i.e. by the presence of a git tag), then the distribution files will
    be uploaded to PyPI as a release.
