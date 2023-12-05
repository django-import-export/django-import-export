import json

import tablib
from django.conf import settings
from django.test import TestCase

from import_export import resources

if "postgresql" in settings.DATABASES["default"]["ENGINE"]:
    from django.contrib.postgres.fields import ArrayField
    from django.db import models

    class BookWithChapters(models.Model):
        name = models.CharField("Book name", max_length=100)
        chapters = ArrayField(models.CharField(max_length=100), default=list)
        data = models.JSONField(null=True)

    class BookWithChaptersResource(resources.ModelResource):
        class Meta:
            model = BookWithChapters
            fields = (
                "id",
                "name",
                "chapters",
                "data",
            )

    class TestExportArrayField(TestCase):
        def test_exports_array_field(self):
            dataset_headers = ["id", "name", "chapters"]
            chapters = ["Introduction", "Middle Chapter", "Ending"]
            dataset_row = ["1", "Book With Chapters", ",".join(chapters)]
            dataset = tablib.Dataset(headers=dataset_headers)
            dataset.append(dataset_row)
            book_with_chapters_resource = resources.modelresource_factory(
                model=BookWithChapters
            )()
            result = book_with_chapters_resource.import_data(dataset, dry_run=False)

            self.assertFalse(result.has_errors())
            book_with_chapters = list(BookWithChapters.objects.all())[0]
            self.assertListEqual(book_with_chapters.chapters, chapters)

    class TestExportJsonField(TestCase):
        def setUp(self):
            self.json_data = {"some_key": "some_value"}
            self.book = BookWithChapters.objects.create(name="foo", data=self.json_data)

        def test_export_field_with_appropriate_format(self):
            resource = resources.modelresource_factory(model=BookWithChapters)()
            result = resource.export(BookWithChapters.objects.all())
            assert result[0][3] == json.dumps(self.json_data)

    class TestImportJsonField(TestCase):
        def setUp(self):
            self.resource = BookWithChaptersResource()
            self.data = {"some_key": "some_value"}
            self.json_data = json.dumps(self.data)
            self.book = BookWithChapters.objects.create(name="foo")
            self.dataset = tablib.Dataset(headers=["id", "name", "data"])
            row = [self.book.id, "Some book", self.json_data]
            self.dataset.append(row)

        def test_sets_json_data_when_model_field_is_empty(self):
            self.assertIsNone(self.book.data)
            result = self.resource.import_data(self.dataset, raise_errors=True)

            self.assertFalse(result.has_errors())
            self.assertEqual(len(result.rows), 1)

            self.book.refresh_from_db()
            self.assertEqual(self.book.data, self.data)

    class TestImportArrayField(TestCase):
        def setUp(self):
            self.resource = BookWithChaptersResource()
            self.chapters = ["Introduction", "Middle Chapter", "Ending"]
            self.book = BookWithChapters.objects.create(name="foo")
            self.dataset = tablib.Dataset(headers=["id", "name", "chapters"])
            row = [self.book.id, "Some book", ",".join(self.chapters)]
            self.dataset.append(row)

        def test_import_of_data_with_array(self):
            self.assertListEqual(self.book.chapters, [])
            result = self.resource.import_data(self.dataset, raise_errors=True)

            self.assertFalse(result.has_errors())
            self.assertEqual(len(result.rows), 1)

            self.book.refresh_from_db()
            self.assertEqual(self.book.chapters, self.chapters)
