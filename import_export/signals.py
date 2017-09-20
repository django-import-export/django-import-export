from django.dispatch import Signal

post_export = Signal(providing_args=["model"])
post_import = Signal(providing_args=["model"])
