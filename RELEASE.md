## Release process

#### Pre release

- Set up `.pypirc` file to reference both pypi and testpypi.

#### Release

- Ensure that all code has been committed and integration tests have run on Github.
  - If pushing directly to `main` branch, ensure this is done on the correct remote repo. 
- `make messages` is intended to be run now to keep the translation files up-to-date.  
  - Run this if there have been any translations updates for the release.  It is recommended to run this prior to any minor release.
  - This creates updates to all translation files so there is no need to commit these unless there have been any translation changes.

```bash
# check out clean version 
# all git operations will be run against this source repo
git clone git@github.com:django-import-export/django-import-export.git django-import-export-rel

cd django-import-export-rel

# checkout any feature branch at this point
# git checkout develop

python3 -m venv venv
source venv/bin/activate
pip install -U pip setuptools wheel

pip install -r requirements/deploy.txt

# zest.releaser pre-release
# (you can set the correct version in this step)
prerelease
```

#### Perform the release

For the first pass you may choose not to upload only to testpypi (not pypi) so that you can check the release. You can check the release by manually downloading the files from testPyPI and checking the contents. 

Once the test file have been checked, run again to upload to PyPI.

```bash
release

# resets the version and pushes changes to origin
postrelease

# remove the rel copy - no longer required
deactivate
cd ..
rm -rf django-import-export-rel
```