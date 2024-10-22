import tablib
from core.models import Author, Book, Category
from core.tests.resources import BookResource
from django.test import TestCase

from import_export import fields, resources, widgets


class ForeignKeyM2MTest(TestCase):
    def setUp(self):
        self.resource = BookResource()
        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "author_email", "price"])
        row = [self.book.pk, "Some book", "test@example.com", "10.25"]
        self.dataset.append(row)

    def test_foreign_keys_export(self):
        author1 = Author.objects.create(name="Foo")
        self.book.author = author1
        self.book.save()

        dataset = self.resource.export(Book.objects.all())
        self.assertEqual(dataset.dict[0]["author"], author1.pk)

    def test_foreign_keys_import(self):
        author2 = Author.objects.create(name="Bar")
        headers = ["id", "name", "author"]
        row = [None, "FooBook", author2.pk]
        dataset = tablib.Dataset(row, headers=headers)
        self.resource.import_data(dataset, raise_errors=True)

        book = Book.objects.get(name="FooBook")
        self.assertEqual(book.author, author2)

    def test_m2m_export(self):
        cat1 = Category.objects.create(name="Cat 1")
        cat2 = Category.objects.create(name="Cat 2")
        self.book.categories.add(cat1)
        self.book.categories.add(cat2)

        dataset = self.resource.export(Book.objects.all())
        self.assertEqual(dataset.dict[0]["categories"], "%d,%d" % (cat1.pk, cat2.pk))

    def test_m2m_import(self):
        cat1 = Category.objects.create(name="Cat 1")
        headers = ["id", "name", "categories"]
        row = [None, "FooBook", str(cat1.pk)]
        dataset = tablib.Dataset(row, headers=headers)
        self.resource.import_data(dataset, raise_errors=True)

        book = Book.objects.get(name="FooBook")
        self.assertIn(cat1, book.categories.all())

    def test_m2m_import_clear(self):
        cat1 = Category.objects.create(name="Cat 1")
        self.book.categories.add(cat1)
        self.assertEqual(1, self.book.categories.count())
        headers = ["id", "name", "categories"]
        row = [self.book.pk, "FooBook", ""]
        dataset = tablib.Dataset(row, headers=headers)
        self.resource.import_data(dataset, raise_errors=True)

        book = Book.objects.get(name="FooBook")
        self.assertEqual(0, book.categories.count())

    def test_m2m_options_import(self):
        cat1 = Category.objects.create(name="Cat 1")
        cat2 = Category.objects.create(name="Cat 2")
        headers = ["id", "name", "categories"]
        row = [None, "FooBook", "Cat 1|Cat 2"]
        dataset = tablib.Dataset(row, headers=headers)

        class BookM2MResource(resources.ModelResource):
            categories = fields.Field(
                attribute="categories",
                widget=widgets.ManyToManyWidget(Category, field="name", separator="|"),
            )

            class Meta:
                model = Book

        resource = BookM2MResource()
        resource.import_data(dataset, raise_errors=True)
        book = Book.objects.get(name="FooBook")
        self.assertIn(cat1, book.categories.all())
        self.assertIn(cat2, book.categories.all())

    def test_m2m_add(self):
        cat1 = Category.objects.create(name="Cat 1")
        cat2 = Category.objects.create(name="Cat 2")
        cat3 = Category.objects.create(name="Cat 3")
        cat4 = Category.objects.create(name="Cat 4")
        headers = ["id", "name", "categories"]
        row = [None, "FooBook", "Cat 1|Cat 2"]
        dataset = tablib.Dataset(row, headers=headers)

        class BookM2MResource(resources.ModelResource):
            categories = fields.Field(
                attribute="categories",
                m2m_add=True,
                widget=widgets.ManyToManyWidget(Category, field="name", separator="|"),
            )

            class Meta:
                model = Book

        resource = BookM2MResource()
        resource.import_data(dataset, raise_errors=True)
        book = Book.objects.get(name="FooBook")
        self.assertIn(cat1, book.categories.all())
        self.assertIn(cat2, book.categories.all())
        self.assertNotIn(cat3, book.categories.all())
        self.assertNotIn(cat4, book.categories.all())

        row1 = [
            book.id,
            "FooBook",
            "Cat 1|Cat 2",
        ]  # This should have no effect, since Cat 1 and Cat 2 already exist
        row2 = [book.id, "FooBook", "Cat 3|Cat 4"]
        dataset = tablib.Dataset(row1, row2, headers=headers)
        resource.import_data(dataset, raise_errors=True)
        book2 = Book.objects.get(name="FooBook")
        self.assertEqual(book.id, book2.id)
        self.assertEqual(book.categories.count(), 4)
        self.assertIn(cat1, book2.categories.all())
        self.assertIn(cat2, book2.categories.all())
        self.assertIn(cat3, book2.categories.all())
        self.assertIn(cat4, book2.categories.all())
