## Release process

The existing manual release process has been replaced with Github Actions as part of the CI / CD workflow.
This has been implemented using [this guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)

#### Perform the release

The release workflow will only run when a tagged commit is pushed.

```bash
# create a commit for the release (e.g. update changelog)

# create an annotated tag
git tag  -a <tag_name> -m "v<tag>"

# push the tagged commit to branch (e.g. 'main')
git push --atomic upstream <branch> <tag>
```

#### Workflow

- When any commit is pushed to the 'main' branch this will cause the 'release' workflow to be run.
  - This will upload the release files to TestPyPI.
  - The release version will be determined from the git commit log.
  - When a published release is identified (i.e. by the presence of a git tag), then the distribution files will
    be uploaded to PyPI as a release.
