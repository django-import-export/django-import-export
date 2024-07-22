"""
Helper module for testing bulk imports.

See testing.rst
"""

import time
from functools import wraps

import tablib
from memory_profiler import memory_usage

from import_export import resources
from import_export.instance_loaders import CachedInstanceLoader

from core.models import Book  # isort:skip

# The number of rows to be created on each profile run.
# Increase this value for greater load testing.
NUM_ROWS = 10000


class _BookResource(resources.ModelResource):
    class Meta:
        model = Book
        fields = ("id", "name", "author_email", "price")
        use_bulk = True
        batch_size = 1000
        skip_unchanged = True
        # skip_diff = True
        # This flag can speed up imports
        # Cannot be used when performing updates
        # force_init_instance = True
        instance_loader_class = CachedInstanceLoader


def profile_duration(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        # Measure duration
        t = time.perf_counter()
        fn(*args, **kwargs)
        elapsed = time.perf_counter() - t
        print(f"Time {elapsed: 0.4}")

    return inner


def profile_mem(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        # Measure memory
        mem, retval = memory_usage(
            (fn, args, kwargs), retval=True, timeout=200, interval=1e-7
        )
        print(f"Memory {max(mem) - min(mem)}")
        return retval

    return inner


@profile_duration
def do_import_duration(resource, dataset):
    resource.import_data(dataset)


@profile_mem
def do_import_mem(resource, dataset):
    resource.import_data(dataset)


def do_create():
    class _BookResource(resources.ModelResource):
        class Meta:
            model = Book
            fields = ("id", "name", "author_email", "price")
            use_bulk = True
            batch_size = 1000
            skip_unchanged = True
            skip_diff = True
            force_init_instance = True

    print("\ndo_create()")
    # clearing down existing objects
    books = Book.objects.all()
    books._raw_delete(books.db)

    rows = [("", "Some new book", "email@example.com", "10.25")] * NUM_ROWS
    dataset = tablib.Dataset(*rows, headers=["id", "name", "author_email", "price"])

    book_resource = _BookResource()
    do_import_duration(book_resource, dataset)
    do_import_mem(book_resource, dataset)

    # Book objects are created once for the 'duration' run,
    # and once for the 'memory' run
    assert Book.objects.count() == NUM_ROWS * 2
    books._raw_delete(books.db)


def do_update():
    print("\ndo_update()")

    # clearing down existing objects
    books = Book.objects.all()
    books._raw_delete(books.db)

    rows = [("", "Some new book", "email@example.com", "10.25")] * NUM_ROWS
    books = [Book(name=r[1], author_email=r[2], price=r[3]) for r in rows]

    # run 'update' - there must be existing rows in the DB...
    # i.e. so they can be updated
    Book.objects.bulk_create(books)
    assert NUM_ROWS == Book.objects.count()

    # find the ids, so that we can perform the update
    all_books = Book.objects.all()
    rows = [(b.id, b.name, b.author_email, b.price) for b in all_books]
    dataset = tablib.Dataset(*rows, headers=["id", "name", "author_email", "price"])

    book_resource = _BookResource()
    do_import_duration(book_resource, dataset)
    do_import_mem(book_resource, dataset)

    assert NUM_ROWS == Book.objects.count()
    books = Book.objects.all()
    books._raw_delete(books.db)


def do_delete():
    class _BookResource(resources.ModelResource):
        def for_delete(self, row, instance):
            return True

        class Meta:
            model = Book
            fields = ("id", "name", "author_email", "price")
            use_bulk = True
            batch_size = 1000
            skip_diff = True
            instance_loader_class = CachedInstanceLoader

    print("\ndo_delete()")

    # clearing down existing objects
    books = Book.objects.all()
    books._raw_delete(books.db)

    rows = [("", "Some new book", "email@example.com", "10.25")] * NUM_ROWS
    books = [Book(name=r[1], author_email=r[2], price=r[3]) for r in rows]

    # deletes - there must be existing rows in the DB...
    # i.e. so they can be deleted
    Book.objects.bulk_create(books)
    assert NUM_ROWS == Book.objects.count()

    all_books = Book.objects.all()
    rows = [(b.id, b.name, b.author_email, b.price) for b in all_books]
    dataset = tablib.Dataset(*rows, headers=["id", "name", "author_email", "price"])

    book_resource = _BookResource()
    do_import_duration(book_resource, dataset)

    assert 0 == Book.objects.count()

    # recreate rows which have just been deleted
    Book.objects.bulk_create(books)
    assert NUM_ROWS == Book.objects.count()

    all_books = Book.objects.all()
    rows = [(b.id, b.name, b.author_email, b.price) for b in all_books]
    dataset = tablib.Dataset(*rows, headers=["id", "name", "author_email", "price"])
    do_import_mem(book_resource, dataset)
    assert 0 == Book.objects.count()


def run(*args):
    if len(args) > 0:
        arg = args[0].lower()
        if arg == "create":
            do_create()
        if arg == "update":
            do_update()
        if arg == "delete":
            do_delete()
    else:
        do_create()
        do_update()
        do_delete()
