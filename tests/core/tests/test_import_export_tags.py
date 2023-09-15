from unittest import TestCase

from import_export.templatetags import import_export_tags


class TagsTest(TestCase):
    def test_compare_values(self):
        target = (
            '<del style="background:#ffe6e6;">a</del>'
            '<ins style="background:#e6ffe6;">b</ins>'
        )
        self.assertEqual(target, import_export_tags.compare_values("a", "b"))
