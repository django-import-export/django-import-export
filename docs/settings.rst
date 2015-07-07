========
Settings
========

``IMPORT_EXPORT_USE_TRANSACTIONS``
    Global setting controls if resource importing should use database
    transactions. Default is ``False``.

``IMPORT_EXPORT_SKIP_ADMIN_LOG``
    Global setting controls if creating log entries for
    the admin changelist should be skipped when importing resource.
    The `skip_admin_log` attribute of `ImportMixin` is checked first,
    which defaults to ``None``. If not found, this global option is used.
    This will speed up importing large datasets, but will lose
    changing logs in the admin changelist view.  Default is ``False``.

``IMPORT_EXPORT_TMP_STORAGE_CLASS``
    Global setting for the class to use to handle temporary storage
    of the uploaded file when importing from the admin using an
    `ImportMixin`.  The `tmp_storage_class` attribute of `ImportMixin`
    is checked first, which defaults to ``None``. If not found, this
    global option is used. Default is ``TempFolderStorage``.
