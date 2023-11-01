from import_export import resources, widgets
from tests.core.models import Author, Book
from tests.test_resources.basic_resources import BookResource
from tests.test_resources.widgets import HarshRussianWidget


class BookResourceWithStoreInstance(resources.ModelResource):
    class Meta:
        model = Book
        store_instance = True


class BookResourceWithLineNumberLogger(BookResource):
    def __init__(self, *args, **kwargs):
        self.before_lines = []
        self.after_lines = []
        return super().__init__(*args, **kwargs)

    def before_import_row(self, row, **kwargs):
        row_number = kwargs.pop("row_number")
        self.before_lines.append(row_number)

    def after_import_row(self, row, row_result, **kwargs):
        row_number = kwargs.pop("row_number")
        self.after_lines.append(row_number)


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
