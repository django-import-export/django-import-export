from core.models import Author, Book, Category, Profile, WithDefault
from core.tests.widget import HarshRussianWidget

from import_export import fields, resources, widgets


class MyResource(resources.Resource):
    name = fields.Field()
    email = fields.Field()
    extra = fields.Field()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kwargs = kwargs

    class Meta:
        export_order = ("email", "name")


class AuthorResource(resources.ModelResource):
    books = fields.Field(
        column_name="books",
        attribute="book_set",
        readonly=True,
    )

    class Meta:
        model = Author
        export_order = ("name", "books")


class BookResource(resources.ModelResource):
    published = fields.Field(column_name="published_date")

    class Meta:
        model = Book
        exclude = ("imported",)


class BookResourceWithStoreInstance(resources.ModelResource):
    class Meta:
        model = Book
        store_instance = True


class BookResourceWithLineNumberLogger(BookResource):
    def __init__(self, **kwargs):
        self.before_lines = []
        self.after_lines = []
        return super().__init__(**kwargs)

    def before_import_row(self, row, **kwargs):
        row_number = kwargs.pop("row_number")
        self.before_lines.append(row_number)

    def after_import_row(self, row, row_result, **kwargs):
        row_number = kwargs.pop("row_number")
        self.after_lines.append(row_number)


class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category


class ProfileResource(resources.ModelResource):
    class Meta:
        model = Profile
        exclude = ("user",)


class WithDefaultResource(resources.ModelResource):
    class Meta:
        model = WithDefault
        fields = ("name",)


class AuthorResourceWithCustomWidget(resources.ModelResource):
    class Meta:
        model = Author

    @classmethod
    def widget_from_django_field(cls, f, default=widgets.Widget):
        if f.name == "name":
            return HarshRussianWidget
        result = default
        internal_type = (
            f.get_internal_type()
            if callable(getattr(f, "get_internal_type", None))
            else ""
        )
        if internal_type in cls.WIDGETS_MAP:
            result = cls.WIDGETS_MAP[internal_type]
            if isinstance(result, str):
                result = getattr(cls, result)(f)
        return result
