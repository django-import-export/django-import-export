from core.tests.resources import BookResource
from django.db.models import CharField, SlugField
from django.test import TestCase

from import_export import widgets


class WidgetFromDjangoFieldTest(TestCase):
    def test_widget_from_django_field_for_CharField_returns_CharWidget(self):
        f = CharField()
        resource = BookResource()
        w = resource.widget_from_django_field(f)
        self.assertEqual(widgets.CharWidget, w)

    def test_widget_from_django_field_for_CharField_subclass_returns_CharWidget(self):
        f = SlugField()
        resource = BookResource()
        w = resource.widget_from_django_field(f)
        self.assertEqual(widgets.CharWidget, w)
