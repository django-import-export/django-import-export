"""
Helper module for testing bulk imports.

See tests/bulk/README.md
"""
import time
from functools import wraps

import tablib
from memory_profiler import memory_usage

from import_export import resources
from import_export.instance_loaders import CachedInstanceLoader

from core.models import Book    # isort:skip

# The number of rows to be created on each profile run.
# Increase this value for greater load testing.
NUM_ROWS = 10000


class _BookResource(resources.ModelResource):

    class Meta:
        model = Book
        fields = ('id', 'name', 'author_email', 'price', 'imported', 'published', 'published_time', 'added')
        use_bulk = True
        batch_size = 1000
        skip_unchanged = True
        #skip_diff = True
        # This flag can speed up imports
        # Cannot be used when performing updates
        # force_init_instance = True
        instance_loader_class = CachedInstanceLoader


class _LimitedBookResource(resources.ModelResource):
    class Meta:
        model = Book
        fields = ('name',)
        use_bulk = True
        batch_size = 1000
        skip_unchanged = True
        instance_loader_class = CachedInstanceLoader


def profile_duration(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        # Measure duration
        t = time.perf_counter()
        retval = fn(*args, **kwargs)
        elapsed = time.perf_counter() - t
        print(f'Time   {elapsed:0.4}')

    return inner


def profile_mem(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        # Measure memory
        mem, retval = memory_usage((fn, args, kwargs), retval=True, timeout=200, interval=1e-7)
        print(f'Memory {max(mem) - min(mem)}')
        return retval

    return inner


def do_create():
    print("\ndo_create()")
    # clearing down existing objects
    Book.objects.all().delete()

    books = []
    for i in range(NUM_ROWS):
        books.append(
            Book(
                name="Some new book",
                author_email="email@author.be",
                imported=1,
                published="2022-01-01",
                published_time="00:00:00",
                price="13.37",
                added="2022-01-02T00:00:00Z"
            )
        )
    
    Book.objects.bulk_create(books)


def do_delete():
    print("\ndo_delete()")

    Book.objects.all().delete()

@profile_duration
def do_export_duration(resource):
    resource.export()


@profile_mem
def do_export_memory(resource):
    resource.export()


def _do_export(resource):
    do_export_duration(resource)
    do_export_memory(resource)
    

def do_limited_export():
    print("\ndo_limited_export()")

    _do_export(_LimitedBookResource())


def do_full_export():
    print("\ndo_full_export()")

    _do_export(_BookResource())


def run(*args):
    do_create()
    do_limited_export()
    do_full_export()
    do_delete()
