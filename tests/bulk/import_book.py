"""
Helper module for testing bulk imports.

Test one of create / update or delete by uncommenting the relevant method calls in main().
Parameters can be modified to test the effect on imports.
The DB is cleared down after each test run.

Each run is profiled for duration and peak memory usage.

When testing deletes, duration and memory usage has to be tested separately.
This can be done by simply commenting out the relevant call in profile()
"""
import time
from functools import wraps

import django
import tablib
from memory_profiler import memory_usage

from import_export import resources
from import_export.instance_loaders import CachedInstanceLoader

django.setup()
from core.models import Book    # isort:skip

NUM_ROWS = 250


class _BookResource(resources.ModelResource):

    class Meta:
        model = Book
        fields = ('id', 'name', 'author_email', 'price')
        use_bulk = True
        batch_size = 1000
        skip_diff = True
        force_init_instance = True
        instance_loader_class = CachedInstanceLoader


def profile(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        fn_kwargs_str = ', '.join(f'{k}={v}' for k, v in kwargs.items())
        print(f'\n{fn.__name__}({fn_kwargs_str})')

        # Measure time
        t = time.perf_counter()
        retval = fn(*args, **kwargs)
        elapsed = time.perf_counter() - t
        print(f'Time   {elapsed:0.4}')

        # Measure memory
        mem, retval = memory_usage((fn, args, kwargs), retval=True, timeout=200, interval=1e-7)
        print(f'Memory {max(mem) - min(mem)}')
        return retval

    return inner


@profile
def do_import(resource, dataset):
    resource.import_data(dataset)


def do_create():
    rows = [('', 'Some new book', 'email@example.com', '10.25')] * NUM_ROWS
    dataset = tablib.Dataset(*rows, headers=['id', 'name', 'author_email', 'price'])

    book_resource = _BookResource()
    do_import(book_resource, dataset)

    assert Book.objects.count() == NUM_ROWS * 2
    Book.objects.all().delete()


def do_update():
    rows = [('', 'Some new book', 'email@example.com', '10.25')] * NUM_ROWS
    books = [Book(name=r[1], author_email=r[2], price=r[3]) for r in rows]
    Book.objects.bulk_create(books)
    assert NUM_ROWS == Book.objects.count()

    # deletes - there must be existing rows in the DB...
    # i.e. so they can be deleted
    all_books = Book.objects.all()
    rows = [(b.id, b.name, b.author_email, b.price) for b in all_books]
    # Add this line in order to perform bulk delete
    dataset = tablib.Dataset(*rows, headers=['id', 'name', 'author_email', 'price'])

    book_resource = _BookResource()
    do_import(book_resource, dataset)

    assert Book.objects.count() == NUM_ROWS
    Book.objects.all().delete()


def do_delete():
    # Run this twice - once for duration and once for memory counts
    # comment out the lines in profile() as appropriate
    class _BookResource(resources.ModelResource):

        def for_delete(self, row, instance):
            return True

        class Meta:
            model = Book
            fields = ('id', 'name', 'author_email', 'price')
            use_bulk = True
            batch_size = 1000
            skip_diff = True
            instance_loader_class = CachedInstanceLoader

    rows = [('', 'Some new book', 'email@example.com', '10.25')] * NUM_ROWS
    books = [Book(name=r[1], author_email=r[2], price=r[3]) for r in rows]
    Book.objects.bulk_create(books)
    assert NUM_ROWS == Book.objects.count()

    # deletes - there must be existing rows in the DB...
    # i.e. so they can be deleted
    all_books = Book.objects.all()
    rows = [(b.id, b.name, b.author_email, b.price) for b in all_books]
    dataset = tablib.Dataset(*rows, headers=['id', 'name', 'author_email', 'price'])

    book_resource = _BookResource()
    do_import(book_resource, dataset)


def main():
    do_create()
    #do_update()
    #do_delete()


if __name__ == "__main__":
    main()
