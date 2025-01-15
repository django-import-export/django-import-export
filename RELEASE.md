## Release process

Pull requests automatically have [pre-commit](https://pre-commit.com/) checks applied via
the [pre-commit.ci](https://pre-commit.ci/) Github application.
These checks will run automatically once the Github application is installed.
The checks run off the `.pre-commit-config.yaml` file, and that file can be used to apply
additional config to the CI process.

### Pre-release

Ensure that `changelog.rst` is up-to-date with the correct version number and release date.

It's sensible to perform a clean installation of the package and ensure the server runs ok.
This can avoid issues with broken imports which may not have been picked up by integration tests.

```
python -m venv venv
pip install django-import-export
tests/manage.py runserver
```

Now browse http://localhost:8000 and test that the site runs ok.

### Compile translations

- `make messages` is intended to be run now to keep the translation files up-to-date.
  - Run this if there have been any translations updates for the release.  It is recommended to run this prior to any minor release.
  - This creates updates to all translation files so there is no need to commit these unless there have been any translation changes.
  - If 'no module named settings' error is seen, try unsetting `DJANGO_SETTINGS_MODULE` environment variable.

### Perform the release

To create a new published release, follow the instructions [here](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).
Ensure you create the new tag to correspond with the release as required.

Always build the release from `main` because ReadTheDocs builds documentation from `main`,
so if another branch is used, then the documentation will be incomplete.

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

For pre-releases, the release version has to be activated via the readthedocs UI before it can be built.

### Troubleshooting

The build can fail on 'publish to PyPI' with errors such as:

```
`long_description` has syntax errors in markup and would not be rendered on PyPI.
```

This is because the README.rst contains syntax errors and cannot be rendered.  You can check this with:

```
pip install readme_renderer
python setup.py check -r -s
```
If there are duplicate target names, you can correct this with [underscores](https://github.com/sphinx-doc/sphinx/issues/3921#issuecomment-315581557).
