## Bulk import testing

- Thinkpad T470 i5 processor (Ubuntu 18.04)
- python 3.8.1
- Postgres 10 (docker container)

### Install dependencies

```bash
# create venv and install django-import-export dependencies
pip install memory-profiler
```

### Create Postgres DB

```bash
export IMPORT_EXPORT_TEST_TYPE=postgres
export IMPORT_EXPORT_POSTGRESQL_USER=pguser
export IMPORT_EXPORT_POSTGRESQL_PASSWORD=pguserpass
export DJANGO_SETTINGS_MODULE=settings

cd ~/Projects/django-import-export/tests/bulk

# start a local postgres instance
docker-compose up -d db 

cd ..
./manage.py migrate
./manage.py test

# only required if you want to login to the Admin site
./manage.py createsuperuser --username admin  --email=email@example.com
```

### bulk_create

```bash
python3 import_book.py
```

### Results

- 20k book entries
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


#### bulk delete

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

### Clearing DB

(set environment variables before running)

```bash
./manage.py shell

from core.models import Book
Book.objects.all().delete()
```

### References

- https://hakibenita.com/fast-load-data-python-postgresql
