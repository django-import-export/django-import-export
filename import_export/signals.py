from django.dispatch import Signal

post_export = Signal(providing_args=["model", "request"])
post_import = Signal(providing_args=["model", "request"])
