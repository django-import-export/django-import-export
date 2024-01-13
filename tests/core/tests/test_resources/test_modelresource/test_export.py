import tablib
from core.models import Author, Book
from core.tests.utils import ignore_widget_deprecation_warning
from django.test import TestCase

from tests.core.tests.resources import BookResource


class ExportFunctionalityTest(TestCase):
    def setUp(self):
        self.resource = BookResource()
        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "author_email", "price"])
        row = [self.book.pk, "Some book", "test@example.com", "10.25"]
        self.dataset.append(row)

    def test_get_export_headers(self):
        headers = self.resource.get_export_headers()
        self.assertEqual(
            headers,
            [
                "id",
                "name",
                "author",
                "author_email",
                "published_date",
                "published_time",
                "price",
                "added",
                "categories",
            ],
        )

    @ignore_widget_deprecation_warning
    def test_export(self):
        with self.assertNumQueries(2):
            dataset = self.resource.export(queryset=Book.objects.all())
            self.assertEqual(len(dataset), 1)

    @ignore_widget_deprecation_warning
    def test_export_with_foreign_keys(self):
        """
        Test that export() containing foreign keys doesn't generate
        extra query for every row.
        Fixes #974
        """
        author = Author.objects.create()
        self.book.author = author
        self.book.save()
        Book.objects.create(name="Second book", author=Author.objects.create())
        Book.objects.create(name="Third book", author=Author.objects.create())

        with self.assertNumQueries(3):
            dataset = self.resource.export(Book.objects.prefetch_related("categories"))
            self.assertEqual(dataset.dict[0]["author"], author.pk)
            self.assertEqual(len(dataset), 3)

    @ignore_widget_deprecation_warning
    def test_export_iterable(self):
        with self.assertNumQueries(2):
            dataset = self.resource.export(queryset=list(Book.objects.all()))
            self.assertEqual(len(dataset), 1)

    @ignore_widget_deprecation_warning
    def test_export_prefetch_related(self):
        with self.assertNumQueries(3):
            dataset = self.resource.export(
                queryset=Book.objects.prefetch_related("categories").all()
            )
            self.assertEqual(len(dataset), 1)

    @ignore_widget_deprecation_warning
    def test_export_handles_named_queryset_parameter(self):
        class _BookResource(BookResource):
            def before_export(self, queryset, **kwargs):
                self.qs = queryset
                self.kwargs_ = kwargs

        self.resource = _BookResource()
        # when queryset is supplied, it should be passed to before_export()
        self.resource.export(queryset=Book.objects.all(), **{"a": 1})
        self.assertEqual(Book.objects.count(), len(self.resource.qs))
        self.assertEqual(dict(a=1), self.resource.kwargs_)
