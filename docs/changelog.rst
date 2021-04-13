Changelog
=========


2.5.1 (unreleased)
------------------

- Support Django 3.2.
- Correctly select widget for ``SmallAutoField`` and ``BigAutoField``.


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

- Deal with importing a BooleanField that actually has `True`, `False`, and
  `None` values. (#1071)
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

- fix: Changed `get_instance()` return val (#842)

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

  Field constructor `default` argument is NOT_PROVIDED instead of None
  Field clean method checks value against `Field.empty_values` [None, '']

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

* Use `field_name` instead of `column_name` for field dehydration, FIX #36

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
