## Release process

The existing manual release process has been replaced with Github Actions as part of the CI / CD workflow.
This has been implemented using [this guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)

#### Perform the release

The release workflow will only run when a tagged commit is pushed.

```bash
# create an annotated tag
git tag  -a <tag_name> -m "v<tag>"

# push this tag only to upstream
git push upstream <tag_name>
```

#### Workflow

- When any commit is pushed this will cause the 'release' workflow to be run.
  - This will upload the release files to TestPyPI.
  - The release version will be determined from the git commit log.
  - When a published release is identified (i.e. by the presence of a git tag):
    - Then the distribution files will be uploaded to PyPI as a release.
    - A github release will be created

### Check readthedocs

Login to [readthedocs.org](https://readthedocs.org) to check that the build ran OK (click on 'Builds' tab).
