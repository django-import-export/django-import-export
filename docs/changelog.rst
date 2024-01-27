Changelog
=========

.. warning::

    Version 4 introduces breaking changes.  Please refer to :doc:`release notes<release_notes>`.

4.0.0-beta.3 (unreleased)
-------------------------

- Added feature: selectable fields for admin export view (#1734)
- Fix issue where declared Resource fields not defined in ``fields`` are still imported (#1702)
- Added customizable ``MediaStorage`` (#1708)
- Relocated admin integration section from advanced_usage.rst into new file (#1713)
- Fix slow export with ForeignKey id (#1717)
- Added customization of Admin UI import error messages (#1727)
- Improve output of error messages (#1729)
- Refactor `test_resources.py` into smaller modules (#1733)
- Added specific check for declared :attr:`~import_export.options.ResourceOptions.import_id_fields` not in dataset
  (#1735)
- Updated Admin integration documentation to clarify how to save custom form values (#1746)

4.0.0-beta.2 (2023-12-09)
-------------------------

- Fix declaring existing model field(s) in ModelResource altering export order (#1663)
- Updated `docker-compose` command with latest version syntax in `runtests.sh` (#1686)
- Support export from model change form (#1687)
- Updated Admin UI to track deleted and skipped Imports (#1691)
- Import form defaults to read-only field if only one format defined (#1690)
- Refactored :mod:`~import_export.resources` into separate modules for ``declarative`` and ``options`` (#1695)
- fix multiple inheritance not setting options (#1696)
- Refactored tests to remove dependencies between tests (#1703)
- Handle python3.12 datetime deprecations (#1705)
- Added FAQ entry for exporting large datasets (#1706)

4.0.0-beta.1 (2023-11-16)
--------------------------

Deprecations
############

- Removed v3 deprecations (#1629)
- Deprecation of ``ExportViewFormMixin`` (#1666)

Enhancements
############

- Refactor ordering logic (#1626)

  - Refactor 'diff' logic to avoid calling dehydrate methods

  - Refactor declarations of ``fields``, ``import_order`` and ``export_order`` to fix ordering issues

- refactor to export HTML / formulae escaping updates (#1638)
- removed unused variable ``Result.new_record`` (#1640)
- Refactor ``resources.py`` to standardise method args (#1641)
- added specific check for missing ``import_id_fields`` (#1645)
- Enable optional tablib dependencies (#1647)
- added :meth:`~import_export.widgets.ForeignKeyWidget.get_lookup_kwargs` to make it easier to override object
  lookup (#1651)
- Standardised interface of :meth:`~import_export.widgets.Widget.render` (#1657)
- Added :meth:`~import_export.resources.Resource.do_instance_save` helper method (#1668)
- Enable defining Resource model as a string (#1669)
- Support multiple Resources for export (#1671)

Fixes
#####

- dynamic widget parameters for CharField fixes 'NOT NULL constraint' error in xlsx (#1485)
- fix cooperation with adminsortable2 (#1633)
- Removed unused method ``utils.original()``
- Fix deprecated ``log_action`` method (#1673)

Development
###########

- Refactor build process (#1630)
- Refactored ``test_admin_integration()``: split into smaller test modules (#1662)
- Refactored ``test_resources()``: split into smaller test modules (#1672)

Documentation
#############

- Clarified ``skip_diff`` documentation (#1655)
- Improved documentation relating to validation on import (#1665)

3.3.7 (unreleased)
------------------

- Pass :meth:`~import_export.mixins.BaseExportMixin.get_export_resource_kwargs` to Resource constructor
  :meth:`~import_export.admin.ExportMixin.export_action` (#1739)
- Fix issue with model class passed to Resource constructor crashing on export (#1745)

3.3.6 (2024-01-10)
------------------

- Fix issue with highlight when using 'light' color scheme (#1728)

3.3.5 (2023-12-19)
------------------

- Remove unnecessary ChangeList queries to speed up export via Admin UI (#1715)
- Respect color scheme override (#1720)
- Update FAQ to cover skipping rows with validation errors (#1721)

3.3.4 (2023-12-09)
------------------

- Added support for django5 (#1634)
- Show list of exported fields in Admin UI (#1685)
- Added `CONTRIBUTING.md`
- Added support for python 3.12 (#1698)
- Update Finnish translations (#1701)

3.3.3 (2023-11-11)
------------------

- :meth:`~import_export.admin.ExportActionMixin.export_admin_action` can be overridden by subclassing it in the
  ``ModelAdmin`` (#1681)

3.3.2 (2023-11-09)
------------------

- Updated Spanish translations (#1639)
- Added documentation and tests for retrieving instance information after import (#1643)
- :meth:`~import_export.widgets.NumberWidget.render` returns ``None`` as empty string
  if ``coerce_to_string`` is True (#1650)
- Updated documentation to describe how to select for export in Admin UI (#1670)
- Added catch for django5 deprecation warning (#1676)
- Updated and compiled message files (#1678)

3.3.1 (2023-09-14)
------------------

- Added `.readthedocs.yaml` (#1625)

3.3.0 (2023-09-14)
------------------

Deprecations
############

- Remove 'escape output' deprecation (#1618)

  - Removal of deprecated :ref:`IMPORT_EXPORT_ESCAPE_OUTPUT_ON_EXPORT`.

  - Deprecation of :ref:`IMPORT_EXPORT_ESCAPE_HTML_ON_EXPORT`.  Refer to :ref:`installation` docs.

Enhancements
############

- Refactoring and fix to support filtering exports (#1579)
- Store ``instance`` and ``original`` object in :class:`~import_export.results.RowResult` (#1584)
- Add customizable blocks in import.html (#1598)
- Include 'allowed formats' settings (#1606)
- Add kwargs to enable CharWidget to return values as strings (#1623)

Internationalization
####################

- Add Finnish translation (#1588)
- Updated ru translation (#1604)
- Fixed badly formatted translation string (#1622)
- Remove 'escape output' deprecation (#1618)

Fixes
#####

- Do not decode bytes when writing to MediaStorage (#1615)
- Fix for cache entries not removed (#1621)

Development
###########

- Added support for Django 4.2 (#1570)
- Add automatic formatting and linting (#1571)
- removed duplicate admin integration tests (#1616)
- Removed support for python3.7 and django4.0 (past EOL) (#1618)

Documentation
#############

- Updated documentation for interoperability with third party libraries (#1614)

3.2.0 (2023-04-12)
------------------

- Escape formulae on export to XLSX (#1568)

  - This includes deprecation of :ref:`IMPORT_EXPORT_ESCAPE_OUTPUT_ON_EXPORT`.

    Refer to :ref:`installation` for alternatives.

  - :meth:`import_export.formats.TablibFormat.export()`: ``escape_output`` flag now deprecated in favour of
    ``escape_html`` and ``escape_formulae``.

- Refactor methods so that ``args`` are declared correctly (#1566)

  - This includes deprecations to be aware of if you have overridden :meth:`~import_export.resources.Resource.export`
    or :class:`~import_export.forms.ImportExportFormBase`.

    - ``export()``: If passing ``queryset`` as the first arg, ensure this is passed as a named parameter.

    - ``ImportExportFormBase``: If passing ``resources`` to ``__init__`` as the first arg, ensure this is
      passed as a named parameter.

- Updated ``setup.py`` (#1564)
- Added ``SECURITY.md`` (#1563)
- Updated FAQ to include workaround for `RelatedObjectDoesNotExist` exception (#1562)
- Prevent error comparing m2m field of the new objects (#1560)
- Add documentation for passing data from admin form to Resource  (#1555)
- Added new translations to Spanish and Spanish (Argentina) (#1552)
- Pass kwargs to import_set function (#1448)

3.1.0 (2023-02-21)
------------------

- Float and Decimal widgets use LANGUAGE_CODE on export (#1501)
- Add optional dehydrate method param (#1536)

  - ``exceptions`` module has been undeprecated

- Updated DE translation (#1537)
- Add option for single step import via Admin Site (#1540)
- Add support for m2m add (#1545)
- collect errors on bulk operations (#1541)

  - this change causes bulk import errors to be logged at DEBUG level not EXCEPTION.

- Improve bulk import performance (#1539)

  - ``raise_errors`` has been deprecated as a kwarg in ``import_row()``

- Reduce memory footprint during import (#1542)
- documentation updates (#1533)
- add detailed format parameter docstrings to ``DateWidget`` and ``TimeWidget`` (#1532)
- tox updates (#1534)
- fix xss vulnerability in html export (#1546)

3.0.2 (2022-12-13)
------------------

- Support Python 3.11 (#1508)
- use ``get_list_select_related`` in ``ExportMixin`` (#1511)
- bugfix: handle crash on start-up when ``change_list_template`` is a property (#1523)
- bugfix: include instance info in row result when row is skipped (#1526)
- bugfix: add ``**kwargs`` param to ``Resource`` constructor (#1527)

3.0.1 (2022-10-18)
------------------

- Updated ``django-import-export-ci.yml`` to fix node.js deprecation
- bugfix: ``DateTimeWidget.clean()`` handles tz aware datetime (#1499)
- Updated translations for v3.0.0 release (#1500)

3.0.0 (2022-10-18)
------------------

Breaking changes
################

This release makes some minor changes to the public API.  If you have overridden any methods from the ``resources`` or ``widgets`` modules, you may need to update your implementation to accommodate these changes.

- Check value of ``ManyToManyField`` in ``skip_row()`` (#1271)
    - This fixes an issue where ManyToMany fields are not checked correctly in ``skip_row()``.  This means that ``skip_row()`` now takes ``row`` as a mandatory arg.  If you have overridden ``skip_row()`` in your own implementation, you will need to add ``row`` as an arg.

- Bug fix: validation errors were being ignored when ``skip_unchanged`` is set (#1378)
    - If you have overridden ``skip_row()`` you can choose whether or not to skip rows if validation errors are present.  The default behavior is to not to skip rows if there are validation errors during import.

- Use 'create' flag instead of instance.pk (#1362)
    - ``import_export.resources.save_instance()`` now takes an additional mandatory argument: ``is_create``.  If you have overridden ``save_instance()`` in your own code, you will need to add this new argument.

- ``widgets``: Unused ``*args`` params have been removed from method definitions. (#1413)
    - If you have overridden ``clean()`` then you should update your method definition to reflect this change.
    - ``widgets.ForeignKeyWidget`` / ``widgets.ManyToManyWidget``: The unused ``*args`` param has been removed from ``__init__()``.  If you have overridden ``ForeignKeyWidget`` or ``ManyToManyWidget`` you may need to update your implementation to reflect this change.

- Admin interface: Modified handling of import errors (#1306)
    - Exceptions raised during the import process are now presented as form errors, instead of being wrapped in a \<H1\> tag in the response.  If you have any custom logic which uses the error written directly into the response, then this may need to be changed.

- ImportForm: improve compatibility with previous signature (#1434)
    - Previous ``ImportForm`` implementation was based on Django's ``forms.Form``, if you have any custom ImportForm you now need to inherit from ``import_export.forms.ImportExportFormBase``.

- Allow custom ``change_list_template`` in admin views using mixins (#1483)
    - If you are using admin mixins from this library in conjunction with code that overrides ``change_list_template`` (typically admin mixins from other libraries such as django-admin-sortable2 or reversion), object tools in the admin change list views may render differently now.
    - If you have created a custom template which extends any import_export template, then this may now cause a recursion error (see #1514)

- ``import.html``: Added blocks to import template (#1488)
    - If you have made customizations to the import template then you may need to refactor these after the addition of block declarations.

Deprecations
############

This release adds some deprecations which will be removed in a future release.

- Add support for multiple resources in ModelAdmin. (#1223)

    - The ``*Mixin.resource_class`` accepting single resource has been deprecated and the new ``*Mixin.resource_classes`` accepting subscriptable type (list, tuple, ...) has been added.

    - Same applies to all of the ``get_resource_class``, ``get_import_resource_class`` and ``get_export_resource_class`` methods.

- Deprecated ``exceptions.py`` (#1372)

- Refactored form-related methods on ``ImportMixin`` / ``ExportMixin`` (#1147)

    - The following are deprecated:

      - ``get_import_form()``

      - ``get_confirm_import_form()``

      - ``get_form_kwargs()``

      - ``get_export_form()``

Enhancements
############

- Default format selections set correctly for export action (#1389)
- Added option to store raw row values in each row's ``RowResult`` (#1393)
- Add natural key support to ``ForeignKeyWidget`` (#1371)
- Optimised default instantiation of ``CharWidget`` (#1414)
- Allow custom ``change_list_template`` in admin views using mixins (#1483)
- Added blocks to import template (#1488)
- improve compatibility with previous ImportForm signature (#1434)
- Refactored form-related methods on ``ImportMixin`` / ``ExportMixin`` (#1147)
- Include custom form media in templates (#1038)
- Remove unnecessary files generated when running tox locally (#1426)

Fixes
#####

- Fixed Makefile coverage: added ``coverage combine``
- Fixed handling of LF character when using ``CacheStorage`` (#1417)
- bugfix: ``skip_row()`` handles M2M field when UUID pk used
- Fix broken link to tablib formats page (#1418)
- Fix broken image ref in ``README.rst``
- bugfix: ``skip_row()`` fix crash when model has m2m field and none is provided in upload (#1439)
- Fix deprecation in example application: Added support for transitional form renderer (#1451)

Development
###########

- Increased test coverage, refactored CI build to use tox (#1372)

Documentation
#############

- Clarified issues around the usage of temporary storage (#1306)

2.9.0 (2022-09-14)
------------------

- Fix deprecation in example application: Added support for transitional form renderer (#1451)
- Escape HTML output when rendering decoding errors (#1469)
- Apply make_aware when the original file contains actual datetimes (#1478)
- Automatically guess the format of the file when importing (#1460)

2.8.0 (2022-03-31)
------------------

- Updated import.css to support dark mode (#1318)
- Fix crash when import_data() called with empty Dataset and ``collect_failed_rows=True`` (#1381)
- Improve Korean translation (#1402)
- Update example subclass widget code (#1407)
- Drop support for python3.6, django 2.2, 3.0, 3.1 (#1408)
- Add get_export_form() to ExportMixin (#1409)

2.7.1 (2021-12-23)
------------------

- Removed ``django_extensions`` from example app settings (#1356)
- Added support for Django 4.0 (#1357)

2.7.0 (2021-12-07)
------------------

- Big integer support for Integer widget (#788)
- Run compilemessages command to keep .mo files in sync (#1299)
- Added ``skip_html_diff`` meta attribute (#1329)
- Added python3.10 to tox and CI environment list (#1336)
- Add ability to rollback the import on validation error (#1339)
- Fix missing migration on example app (#1346)
- Fix crash when deleting via admin site (#1347)
- Use Github secret in CI script instead of hard-coded password (#1348)
- Documentation: correct error in example application which leads to crash (#1353)

2.6.1 (2021-09-30)
------------------

- Revert 'dark mode' css: causes issues in django2.2 (#1330)

2.6.0 (2021-09-15)
------------------

- Added guard for null 'options' to fix crash (#1325)
- Updated import.css to support dark mode (#1323)
- Fixed regression where overridden mixin methods are not called (#1315)
- Fix xls/xlsx import of Time fields (#1314)
- Added support for 'to_encoding' attribute (#1311)
- Removed travis and replaced with github actions for CI (#1307)
- Increased test coverage (#1286)
- Fix minor date formatting issue for date with years < 1000 (#1285)
- Translate the zh_Hans missing part (#1279)
- Remove code duplication from mixins.py and admin.py (#1277)
- Fix example in BooleanWidget docs (#1276)
- Better support for Django main (#1272)
- don't test Django main branch with python36,37 (#1269)
- Support Django 3.2 (#1265)
- Correct typo in Readme (#1258)
- Rephrase logical clauses in docstrings (#1255)
- Support multiple databases (#1254)
- Update django master to django main (#1251)
- Add Farsi translated messages in the locale (#1249)
- Update Russian translations (#1244)
- Append export admin action using ModelAdmin.get_actions (#1241)
- Fix minor mistake in makemigrations command (#1233)
- Remove EOL Python 3.5 from CI (#1228)
- CachedInstanceLoader defaults to empty when import_id is missing (#1225)
- Add kwargs to import_row, import_object and import_field (#1190)
- Call load_workbook() with data_only flag (#1095)


2.5.0 (2020-12-30)
------------------

- Changed the default value for ``IMPORT_EXPORT_CHUNK_SIZE`` to 100. (#1196)
- Add translation for Korean (#1218)
- Update linting, CI, and docs.


2.4.0 (2020-10-05)
------------------

- Fix deprecated Django 3.1 ``Signal(providing_args=...)`` usage.
- Fix deprecated Django 3.1 ``django.conf.urls.url()`` usage.


2.3.0 (2020-07-12)
------------------

- Add missing translation keys for all languages (#1144)
- Added missing Portuguese translations (#1145)
- Add kazakh translations (#1161)
- Add bulk operations (#1149)

2.2.0 (2020-06-01)
------------------

- Deal with importing a BooleanField that actually has ``True``, ``False``, and
  ``None`` values. (#1071)
- Add row_number parameter to before_import_row, after_import_row and after_import_instance (#1040)
- Paginate queryset if Queryset.prefetch_related is used (#1050)

2.1.0 (2020-05-02)
------------------

- Fix DurationWidget handling of zero value (#1117)

- Make import diff view only show headers for user visible fields (#1109)

- Make confirm_form accessible in get_import_resource_kwargs and get_import_data_kwargs (#994, #1108)

- Initialize Decimal with text value, fix #1035 (#1039)

- Adds meta flag 'skip_diff' to enable skipping of diff operations (#1045)

- Update docs (#1097, #1114, #1122, #969, #1083, #1093)


2.0.2 (2020-02-16)
------------------

- Add support for tablib >= 1.0 (#1061)

- Add ability to install a subset of tablib supported formats and save some
  automatic dependency installations (needs tablib >= 1.0)

- Use column_name when checking row for fields (#1056)

2.0.1 (2020-01-15)
------------------

- Fix deprecated Django 3.0 function usage (#1054)

- Pin tablib version to not use new major version (#1063)

- Format field is always shown on Django 2.2 (#1007)

2.0 (2019-12-03)
----------------

- Removed support for Django < 2.0
- Removed support for Python < 3.5
- feat: Support for Postgres JSONb Field (#904)

1.2.0 (2019-01-10)
------------------

- feat: Better surfacing of validation errors in UI / optional model instance validation (#852)

- chore: Use modern setuptools in setup.py (#862)

- chore: Update URLs to use https:// (#863)

- chore: remove outdated workarounds

- chore: Run SQLite tests with in-memory database

- fix: Change logging level (#832)

- fix: Changed ``get_instance()`` return val (#842)

1.1.0 (2018-10-02)
------------------

- fix: Django2.1 ImportExportModelAdmin export (#797) (#819)

- setup: add django2.1 to test matrix

- JSONWidget for jsonb fields (#803)

- Add ExportActionMixin (#809)

- Add Import Export Permissioning #608 (#804)

- write_to_tmp_storage() for import_action() (#781)

- follow relationships on ForeignKeyWidget #798

- Update all pypi.python.org URLs to pypi.org

- added test for tsv import

- added unicode support for TSV for python 2

- Added ExportViewMixin (#692)

1.0.1 (2018-05-17)
------------------

- Make deep copy of fileds from class attr to instance attr (#550)

- Fix #612: NumberWidget.is_empty() should strip the value if string type (#613)

- Fix #713: last day isn't included in results qs (#779)

- use Python3 compatible MySql driver in development (#706)

- fix: warning U mode is deprecated in python 3 (#776)

- refactor: easier overridding widgets and default field (#769)

- Updated documentation regardign declaring fields (#735)

- custom js for action form also handles grappelli (#719)

- Use 'verbose_name' in breadcrumbs to match Django default (#732)

- Add Resource.get_diff_class() (#745)

- Fix and add polish translation (#747)

- Restore raise_errors to before_import (#749)


1.0.0 (2018-02-13)
------------------

- Switch to semver versioning (#687)

- Require Django>=1.8 (#685)

- upgrade tox configuration (#737)


0.7.0 (2018-01-17)
------------------

- skip_row override example (#702)

- Testing against Django 2.0 should not fail (#709)

- Refactor transaction handling (#690)

- Resolves #703 fields shadowed (#703)

- discourage installation as a zipped egg (#548)

- Fixed middleware settings in test app for Django 2.x (#696)


0.6.1 (2017-12-04)
------------------

- Refactors and optimizations (#686, #632, #684, #636, #631, #629, #635, #683)

- Travis tests for Django 2.0.x (#691)


0.6.0 (2017-11-23)
------------------

- Refactor import_row call by using keyword arguments (#585)

- Added {{ block.super }} call in block bodyclass in admin/base_site.html (#582)

- Add support for the Django DurationField with DurationWidget (#575)

- GitHub bmihelac -> django-import-export Account Update (#574)

- Add intersphinx links to documentation (#572)

- Add Resource.get_import_fields() (#569)

- Fixed readme mistake (#568)

- Bugfix/fix m2m widget clean (#515)

- Allow injection of context data for template rendered by import_action() and export_action() (#544)

- Bugfix/fix exception in generate_log_entries() (#543)

- Process import dataset and result in separate methods (#542)

- Bugfix/fix error in converting exceptions to strings (#526)

- Fix admin integration tests for the new "Import finished..." message, update Czech translations to 100% coverage. (#596)

- Make import form type easier to override (#604)

- Add saves_null_values attribute to Field to control whether null values are saved on the object (#611)

- Add Bulgarian translations (#656)

- Add django 1.11 to TravisCI (#621)

- Make Signals code example format correctly in documentation (#553)

- Add Django as requirement to setup.py (#634)

- Update import of reverse for django 2.x (#620)

- Add Django-version classifiers to setup.py’s CLASSIFIERS (#616)

- Some fixes for Django 2.0 (#672)

- Strip whitespace when looking up ManyToMany fields (#668)

- Fix all ResourceWarnings during tests in Python 3.x (#637)

- Remove downloads count badge from README since shields.io no longer supports it for PyPi (#677)

- Add coveralls support and README badge (#678)


0.5.1 (2016-09-29)
------------------

- French locale not in pypi (#524)

- Bugfix/fix undefined template variables (#519)


0.5.0 (2016-09-01)
------------------

- Hide default value in diff when importing a new instance (#458)

- Append rows to Result object via function call to allow overriding (#462)

- Add get_resource_kwargs to allow passing request to resource (#457)

- Expose Django user to get_export_data() and export() (#447)

- Add before_export and after_export hooks (#449)

- fire events post_import, post_export events (#440)

- add **kwargs to export_data / create_dataset

- Add before_import_row() and after_import_row() (#452)

- Add get_export_fields() to Resource to control what fields are exported (#461)

- Control user-visible fields (#466)

- Fix diff for models using ManyRelatedManager

- Handle already cleaned objects (#484)

- Add after_import_instance hook (#489)

- Use optimized xlsx reader (#482)

- Adds resource_class of BookResource (re-adds) in admin docs (#481)

- Require POST method for process_import() (#478)

- Add SimpleArrayWidget to support use of django.contrib.postgres.fields.ArrayField (#472)

- Add new Diff class (#477)

- Fix #375: add row to widget.clean(), obj to widget.render() (#479)

- Restore transactions for data import (#480)

- Refactor the import-export templates (#496)

- Update doc links to the stable version, update rtfd to .io (#507)

- Fixed typo in the Czech translation (#495)


0.4.5 (2016-04-06)
------------------

- Add FloatWidget, use with model fields models.FloatField (#433)

- Fix default values in fields (#431, #364)

  Field constructor ``default`` argument is NOT_PROVIDED instead of None
  Field clean method checks value against ``Field.empty_values`` [None, '']

0.4.4 (2016-03-22)
------------------

- FIX: No static/ when installed via pip #427

- Add total # of imports and total # of updates to import success msg


0.4.3 (2016-03-08)
------------------

- fix MediaStorage does not respect the read_mode parameter (#416)

- Reset SQL sequences when new objects are imported (#59)

- Let Resource rollback if import throws exception (#377)

- Fixes error when a single value is stored in m2m relation field (#177)

- Add support for django.db.models.TimeField (#381)


0.4.2 (2015-12-18)
------------------

- add xlsx import support


0.4.1 (2015-12-11)
------------------

- fix for fields with a dyanmic default callable (#360)


0.4.0 (2015-12-02)
------------------

- Add Django 1.9 support

- Django 1.4 is not supported (#348)


0.3.1 (2015-11-20)
------------------

- FIX: importing csv in python 3


0.3 (2015-11-20)
----------------

- FIX: importing csv UnicodeEncodeError introduced in 0.2.9 (#347)


0.2.9 (2015-11-12)
------------------

- Allow Field.save() relation following (#344)

- Support default values on fields (and models) (#345)

- m2m widget: allow trailing comma (#343)

- Open csv files as text and not binary (#127)


0.2.8 (2015-07-29)
------------------

- use the IntegerWidget for database-fields of type BigIntegerField (#302)

- make datetime timezone aware if USE_TZ is True (#283).

- Fix 0 is interpreted as None in number widgets (#274)

- add possibility to override tmp storage class (#133, #251)

- better error reporting (#259)


0.2.7 (2015-05-04)
------------------

- Django 1.8 compatibility

- add attribute inheritance to Resource (#140)

- make the filename and user available to import_data (#237)

- Add to_encoding functionality (#244)

- Call before_import before creating the instance_loader - fixes #193


0.2.6 (2014-10-09)
------------------

- added use of get_diff_headers method into import.html template (#158)

- Try to use OrderedDict instead of SortedDict, which is deprecated in
  Django 1.7 (#157)

- fixed #105 unicode import

- remove invalid form action "form_url" #154


0.2.5 (2014-10-04)
------------------

- Do not convert numeric types to string (#149)

- implement export as an admin action (#124)


0.2.4 (2014-09-18)
------------------

- fix: get_value raised attribute error on model method call

- Fixed XLS import on python 3. Optimized loop

- Fixed properly skipping row marked as skipped when importing data from
  the admin interface.

- Allow Resource.export to accept iterables as well as querysets

- Improve error messages

- FIX: Properly handle NullBoleanField (#115) - Backward Incompatible Change
  previously None values were handled as false


0.2.3 (2014-07-01)
------------------

- Add separator and field keyword arguments to ManyToManyWidget

- FIX: No support for dates before 1900 (#93)


0.2.2 (2014-04-18)
------------------

- RowResult now stores exception object rather than it's repr

- Admin integration - add EntryLog object for each added/updated/deleted instance


0.2.1 (2014-02-20)
------------------

- FIX import_file_name form field can be use to access the filesystem (#65)


0.2.0 (2014-01-30)
------------------

- Python 3 support


0.1.6 (2014-01-21)
------------------

* Additional hooks for customizing the workflow (#61)

0.1.5 (2013-11-29)
------------------

* Prevent queryset caching when exporting (#44)

* Allow unchanged rows to be skipped when importing (#30)

* Update tests for Django 1.6 (#57)

* Allow different ``ResourceClass`` to be used in ``ImportExportModelAdmin``
  (#49)

0.1.4
-----

* Use ``field_name`` instead of ``column_name`` for field dehydration, FIX #36

* Handle OneToOneField,  FIX #17 - Exception when attempting access something
  on the related_name.

* FIX #23 - export filter not working

0.1.3
-----

* Fix packaging

* DB transactions support for importing data

0.1.2
-----

* support for deleting objects during import

* bug fixes

* Allowing a field to be 'dehydrated' with a custom method

* added documentation

0.1.1
-----

* added ExportForm to admin integration for choosing export file format

* refactor admin integration to allow better handling of specific formats
  supported features and better handling of reading text files

* include all available formats in Admin integration

* bugfixes

0.1.0
-----

* Refactor api
