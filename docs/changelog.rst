Changelog
=========


0.5.2 (unreleased)
------------------

- Nothing changed yet.


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

* include all avialable formats in Admin integration

* bugfixes

0.1.0
-----

* Refactor api
