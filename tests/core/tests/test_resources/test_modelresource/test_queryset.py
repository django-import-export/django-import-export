from unittest import mock

import tablib
from core.models import Book
from core.tests.resources import BookResource
from django.core.paginator import Paginator
from django.test import TestCase


class QuerysetHandlingTest(TestCase):
    def setUp(self):
        self.resource = BookResource()
        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "author_email", "price"])
        row = [self.book.pk, "Some book", "test@example.com", "10.25"]
        self.dataset.append(row)

    def test_iter_queryset(self):
        qs = Book.objects.all()
        with mock.patch.object(qs, "iterator") as mocked_method:
            list(self.resource.iter_queryset(qs))
            mocked_method.assert_called_once_with(chunk_size=100)

    def test_iter_queryset_prefetch_unordered(self):
        qsu = Book.objects.prefetch_related("categories").all()
        qso = qsu.order_by("pk").all()
        with mock.patch.object(qsu, "order_by") as mocked_method:
            mocked_method.return_value = qso
            list(self.resource.iter_queryset(qsu))
            mocked_method.assert_called_once_with("pk")

    def test_iter_queryset_prefetch_ordered(self):
        qs = Book.objects.prefetch_related("categories").order_by("pk").all()
        with mock.patch("import_export.resources.Paginator", autospec=True) as p:
            p.return_value = Paginator(qs, 100)
            list(self.resource.iter_queryset(qs))
            p.assert_called_once_with(qs, 100)

    def test_iter_queryset_prefetch_chunk_size(self):
        class B(BookResource):
            class Meta:
                chunk_size = 1000

        paginator = "import_export.resources.Paginator"
        qs = Book.objects.prefetch_related("categories").order_by("pk").all()
        with mock.patch(paginator, autospec=True) as mocked_obj:
            mocked_obj.return_value = Paginator(qs, 1000)
            list(B().iter_queryset(qs))
            mocked_obj.assert_called_once_with(qs, 1000)
