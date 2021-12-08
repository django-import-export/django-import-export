## Bulk import testing

This scripts outlines the steps used to profile bulk loading.
The `bulk_import.py` script is used to profile run duration and memory during bulk load testing.

### Pre-requisites

- [Docker](https://docker.com)
- [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/command_ref.html)

### Test environment

The following tests were run on the following platform:

- Thinkpad T470 i5 processor (Ubuntu 18.04)
- python 3.8.1
- Postgres 10 (docker container)

### Install dependencies

```bash
# create venv and install django-import-export dependencies
cd <PROJECT_HOME>
mkvirtualenv -p python3 djangoimportexport
pip install -r requirements/base.txt -r requirements/test.txt
```

### Create Postgres DB

```bash
export IMPORT_EXPORT_TEST_TYPE=postgres
export IMPORT_EXPORT_POSTGRESQL_USER=pguser
export IMPORT_EXPORT_POSTGRESQL_PASSWORD=pguserpass
export DJANGO_SETTINGS_MODULE=settings

cd <PROJECT_HOME>/tests

# start a local postgres instance
docker-compose -f bulk/docker-compose.yml up -d 

./manage.py migrate
./manage.py test

# only required if you want to login to the Admin site
./manage.py createsuperuser --username admin  --email=email@example.com
```

### Update settings

In order to use the `runscript` command, add `django_extensions` to `settings.py` (`INSTALLED_APPS`).

### Running script

```bash
# run creates, updates, and deletes
./manage.py runscript bulk_import

# pass 'create', 'update' or 'delete' to run the single test
./manage.py runscript bulk_import --script-args create
```

### Results

- Used 20k book entries
- Memory is reported as the peak memory value whilst running the test script

#### bulk_create

##### Default settings

- default settings
- uses `ModelInstanceLoader` by default

| Condition                          | Time (secs) |  Memory (MB)  |
| ---------------------------------- | ----------- | ------------- |
| `use_bulk=False`                   | 42.67       | 16.22         |
| `use_bulk=True, batch_size=None`   | 33.72       | 50.02         |
| `use_bulk=True, batch_size=1000`   | 33.21       | 11.43         |

##### Performance tweaks

| use_bulk | batch_size | skip_diff | instance_loader      | time (secs) | peak mem (MB) |
| -------- | ---------- | --------- | -------------------- | ----------- | ------------- |
| True     | 1000       | True      | force_init_instance  |  9.60       |  9.4          |
| True     | 1000       | False     | CachedInstanceLoader | 13.72       |  9.9          |
| True     | 1000       | True      | CachedInstanceLoader | 16.12       |  9.5          |
| True     | 1000       | False     | force_init_instance  | 19.93       | 10.5          |
| False    | n/a        | False     | force_init_instance  | 26.59       | 14.1          |
| True     | 1000       | False     | ModelInstanceLoader  | 28.60       |  9.7          |
| True     | 1000       | False     | ModelInstanceLoader  | 33.19       | 10.6          |
| False    | n/a        | False     | ModelInstanceLoader  | 45.32       | 16.3          |

(`force_init_instance`) means overriding `get_or_init_instance()` - this can be done when you know for certain that you are importing new rows:

```python
def get_or_init_instance(self, instance_loader, row):
    return self._meta.model(), True
```

#### bulk_update

```bash
./manage.py runscript bulk_import --script-args update
```

##### Default settings

- `skip_diff = False`
- `instance_loader_class = ModelInstanceLoader` 

| Condition                          | Time (secs) | Memory (MB)   |
| ---------------------------------- | ----------- | ------------- |
| `use_bulk=False`                   | 82.28       |   9.33        |
| `use_bulk=True, batch_size=None`   | 92.41       | 202.26        |
| `use_bulk=True, batch_size=1000`   | 52.63       |  11.25        |

##### Performance tweaks

- `skip_diff = True`
- `instance_loader_class = CachedInstanceLoader`

| Condition                          | Time (secs) |  Memory (MB)  |
| ---------------------------------- | ----------- | ------------- |
| `use_bulk=False`                   | 28.85       |  20.71        |
| `use_bulk=True, batch_size=None`   | 65.11       | 201.01        |
| `use_bulk=True, batch_size=1000`   | 21.56       |  21.25        |


- `skip_diff = False`

| Condition                                | Time (secs) |  Memory (MB)  |
| ---------------------------------------- | ----------- | ------------- |
| `use_bulk=True, batch_size=1000`         | 9.26        |  8.51         |
| `skip_html_diff=True, batch_size=1000`   | 8.69        |  7.50         |
| `skip_unchanged=True, batch_size=1000`   | 5.42        |  7.34         |


#### bulk delete

```bash
./manage.py runscript bulk_import --script-args delete
```

##### Default settings

- `skip_diff = False`
- `instance_loader_class = ModelInstanceLoader` 

| Condition                          | Time (secs) | Memory (MB)   |
| ---------------------------------- | ----------- | ------------- |
| `use_bulk=False`                   | 95.56       |  31.36        |
| `use_bulk=True, batch_size=None`   | 50.20       |  64.66        |
| `use_bulk=True, batch_size=1000`   | 43.77       |  33.123       |

##### Performance tweaks

- `skip_diff = True`
- `instance_loader_class = CachedInstanceLoader`

| Condition                          | Time (secs) |  Memory (MB)  |
| ---------------------------------- | ----------- | ------------- |
| `use_bulk=False`                   | 61.66       | 31.94         |
| `use_bulk=True, batch_size=None`   | 14.08       | 39.40         |
| `use_bulk=True, batch_size=1000`   | 15.37       | 32.70         |

### Checking DB

Note that the db is cleared down after each test run.
You need to uncomment the `delete()` calls to be able to view data.

```bash
./manage.py shell_plus

Book.objects.all().count()
```

### Clear down

Optional clear down of resources:

```bash
# remove the test db container
docker-compose -f bulk/docker-compose.yml down -v

# remove venv
deactivate
rmvirtualenv djangoimportexport
```

### References

- https://hakibenita.com/fast-load-data-python-postgresql
