from import_export import widgets


class HarshRussianWidget(widgets.CharWidget):
    def clean(self, value, row=None, *args, **kwargs):
        raise ValueError("Ова вриједност је страшна!")
