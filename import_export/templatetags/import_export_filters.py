from django import template
from django.contrib import admin

register = template.Library()


@register.filter
def is_exportable(obj, request):
    model_class = obj["model"]
    admin_class = admin.site._registry[model_class]
    return hasattr(
        admin_class, "has_export_permission"
    ) and admin_class.has_export_permission(request)


@register.filter
def is_importable(obj, request):
    model_class = obj["model"]
    admin_class = admin.site._registry[model_class]
    return hasattr(
        admin_class, "has_import_permission"
    ) and admin_class.has_import_permission(request)


@register.filter
def get_opts(obj):
    model_class = obj["model"]
    return model_class._meta
