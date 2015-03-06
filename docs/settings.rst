========
Settings
========

``IMPORT_EXPORT_USE_TRANSACTIONS``
    Global setting controls if resource importing should use database
    transactions. Default is ``False``.

``IMPORT_EXPORT_SKIP_ADMIN_LOG``
    Global setting controls if creating log entries for
    the admin changelist should be skipped when importing resource.
    The skip_admin_log attribute of `ImportMixin` is checked first,
    which defaults to None. If not found, this global option is used.
    This will speed up importing large datasets, but will lose
    changing logs in the admin changelist view.  Default is ``False``.
