Changelog
=========

.. warning::

    If upgrading from v3, v4 introduces breaking changes.  Please refer to :doc:`release notes<release_notes>`.

4.3.6 (2025-02-21)
------------------

- Add flag to ignore empty rows in XLSX import (`2028 <https://github.com/django-import-export/django-import-export/issues/2028>`_)
- Add support for Django 5.2 (`2037 <https://github.com/django-import-export/django-import-export/pull/2037>`_)
- Fix Chinese translation (`2040 <https://github.com/django-import-export/django-import-export/issues/2040>`_)

4.3.5 (2025-02-01)
------------------

- Clarify documentation on creating non-existent relations (`2029 <https://github.com/django-import-export/django-import-export/issues/2029>`_)
- Update Turkish translations (`2031 <https://github.com/django-import-export/django-import-export/issues/2031>`_)

4.3.4 (2025-01-15)
------------------

- Handle QuerySets called with ``values()`` on export (`2011 <https://github.com/django-import-export/django-import-export/issues/2011>`_)

4.3.3 (2024-12-02)
------------------

- Update all translations (`2014 <https://github.com/django-import-export/django-import-export/issues/2014>`_)

4.3.2 (2024-12-01)
------------------

- Updated Farsi translation (`2008 <https://github.com/django-import-export/django-import-export/issues/2008>`_)
- Updated German translation (`2012 <https://github.com/django-import-export/django-import-export/issues/2012>`_)

4.3.1 (2024-11-19)
------------------

- Fix imports for openpyxl (`2005 <https://github.com/django-import-export/django-import-export/issues/2005>`_)

4.3.0 (2024-11-19)
------------------

- Addition of import & export management commands (`1992 <https://github.com/django-import-export/django-import-export/issues/1992>`_)
- Handle ``IllegalCharacterError`` in xlsx exports (`2001 <https://github.com/django-import-export/django-import-export/issues/2001>`_)
- Add ``__repr__`` method to InvalidRow for improved debugging (`2003 <https://github.com/django-import-export/django-import-export/issues/2003>`_)

4.2.1 (2024-11-11)
------------------

- Removed dependency files in favour of ``pyproject.toml`` (`1982 <https://github.com/django-import-export/django-import-export/issues/1982>`_)
- Documentation updates (`1989 <https://github.com/django-import-export/django-import-export/issues/1989>`_)
- Fix crash on export of tz-aware datetime to binary formats (`1995 <https://github.com/django-import-export/django-import-export/issues/1995>`_)

4.2.0 (2024-10-23)
------------------

This release contains breaking changes.  Please refer to :doc:`release notes<release_notes>`.

- Upgraded tablib version (`1627 <https://github.com/django-import-export/django-import-export/issues/1627>`_)
- Document overriding formats (`1868 <https://github.com/django-import-export/django-import-export/issues/1868>`_)
- Consistent queryset creation in ModelAdmin export mixin (`1890 <https://github.com/django-import-export/django-import-export/pull/1890>`_)
- Deprecated :meth:`~import_export.admin.ExportMixin.get_valid_export_item_pks` in favour of :meth:`~import_export.admin.ExportMixin.get_queryset` (`1890 <https://github.com/django-import-export/django-import-export/pull/1890>`_)
- Improve deprecation warning for ``ExportViewFormMixin`` to report at point of class definition (`1900 <https://github.com/django-import-export/django-import-export/pull/1900>`_)
- Fix export for fields with custom declared name (`1903 <https://github.com/django-import-export/django-import-export/pull/1903>`_)
- Hide the "Resource" form when it only has one option (`1908 <https://github.com/django-import-export/django-import-export/issues/1908>`_)
- Update date, time and datetime widget render method to handle derived instance (`1918 <https://github.com/django-import-export/django-import-export/issues/1918>`_)
- Add support for Django 5.1 (`1926 <https://github.com/django-import-export/django-import-export/issues/1926>`_)
- Accept numbers using the numeric separators of the current language in number widgets (:meth:`~import_export.widgets.FloatWidget`, :meth:`~import_export.widgets.IntegerWidget`, :meth:`~import_export.widgets.DecimalWidget`) (`1927 <https://github.com/django-import-export/django-import-export/issues/1927>`_)
- Added warning for declared fields excluded from fields whitelist (`1930 <https://github.com/django-import-export/django-import-export/issues/1930>`_)
- Fix v3 regression: handle native types on export to spreadsheet (`1939 <https://github.com/django-import-export/django-import-export/issues/1939>`_)
- Fix export button displayed on change screen when export permission not assigned (`1942 <https://github.com/django-import-export/django-import-export/issues/1942>`_)
- Fix crash for Django 5.1 when rows are skipped (`1944 <https://github.com/django-import-export/django-import-export/issues/1944>`_)
- Allow callable in dehydrate method (`1950 <https://github.com/django-import-export/django-import-export/issues/1950>`_)
- Fix crash when Resource fields declared incorrectly (`1963 <https://github.com/django-import-export/django-import-export/issues/1963>`_)
- Updated dependencies (`1979 <https://github.com/django-import-export/django-import-export/issues/1979>`_)

4.1.1 (2024-07-08)
------------------

- Restore return value for deprecated method :meth:`~import_export.resources.Resource.get_fields` (`1897 <https://github.com/django-import-export/django-import-export/pull/1897>`_)

4.1.0 (2024-06-25)
------------------

- Improve Error class (`1882 <https://github.com/django-import-export/django-import-export/pull/1882>`_)
- Fix response content assertions (`1883 <https://github.com/django-import-export/django-import-export/pull/1883>`_)
- Admin UI: display checkboxes before labels in export form (`1884 <https://github.com/django-import-export/django-import-export/pull/1884>`_)
- deprecated unused method: :meth:`~import_export.resources.Resource.get_fields` (`1885 <https://github.com/django-import-export/django-import-export/pull/1885>`_)

4.0.10 (2024-06-25)
------------------

- remove django version check for custom storages (`1889 <https://github.com/django-import-export/django-import-export/pull/1889>`_)

4.0.9 (2024-06-18)
------------------

- docs: clarify :meth:`~import_export.resources.Resource.for_delete` documentation (`1877 <https://github.com/django-import-export/django-import-export/pull/1877>`_)
- fix default ``Field`` returns empty string instead of *'None'*  (`1872 <https://github.com/django-import-export/django-import-export/pull/1872>`_)
- revert setting default value for ``attribute`` (`1875 <https://github.com/django-import-export/django-import-export/pull/1875>`_)

4.0.8 (2024-06-13)
------------------

- docs: clarify widget configuration (`1865 <https://github.com/django-import-export/django-import-export/pull/1865>`_)
- Enable skip export confirm page (`1867 <https://github.com/django-import-export/django-import-export/pull/1867>`_)

4.0.7 (2024-05-30)
------------------

- fix documentation to show correct method for reading form data on export (`1859 <https://github.com/django-import-export/django-import-export/pull/1859>`_)
- Admin UI: display both field name and column name on export (`1857 <https://github.com/django-import-export/django-import-export/pull/1857>`_)
- fix export declared field with custom column name (`1861 <https://github.com/django-import-export/django-import-export/pull/1861>`_)
- fix declared fields do not have correct Widget class set (`1861 <https://github.com/django-import-export/django-import-export/pull/1861>`_)
- docs: clarify changes to ``CharWidget`` in v4 (`1862 <https://github.com/django-import-export/django-import-export/pull/1862>`_)
- refactor :class:`~import_export.resources.Resource` to remove code duplication in export (`1863 <https://github.com/django-import-export/django-import-export/pull/1863>`_)

4.0.6 (2024-05-27)
------------------

- Added additional test for export field order (`1848 <https://github.com/django-import-export/django-import-export/pull/1848>`_)
- fix crash on import when relation has custom PK (`1853 <https://github.com/django-import-export/django-import-export/pull/1853>`_)
- fix crash on export from action when instance has custom PK (`1854 <https://github.com/django-import-export/django-import-export/pull/1854>`_)

4.0.5 (2024-05-23)
------------------

- Fix for invalid build due to malformed README.rst (`1851 <https://github.com/django-import-export/django-import-export/pull/1851>`_)

4.0.4 (2024-05-23)
------------------

- Refactored ``DateWidget`` & ``DateTimeWidget`` to remove code duplication (`1839 <https://github.com/django-import-export/django-import-export/pull/1839>`_)
- Release note documentation updated (`1840 <https://github.com/django-import-export/django-import-export/pull/1840>`_)
- Added missing migration to example app (`1843 <https://github.com/django-import-export/django-import-export/pull/1843>`_)
- Fix admin UI display of field import order (`1849 <https://github.com/django-import-export/django-import-export/pull/1849>`_)

4.0.3 (2024-05-16)
------------------

- Support widgets with CSS and JS media in ImportForm (`1807 <https://github.com/django-import-export/django-import-export/pull/1807>`_)
- Documentation updates (`1833 <https://github.com/django-import-export/django-import-export/pull/1833>`_)
- Clarified documentation when importing with ``import_id_fields``  (`1836 <https://github.com/django-import-export/django-import-export/pull/1836>`_)
- re-add ``resource_class`` deprecation warning (`1837 <https://github.com/django-import-export/django-import-export/pull/1837>`_)
- fixed Arabic translation for 'import' word (`1838 <https://github.com/django-import-export/django-import-export/pull/1838>`_)

4.0.2 (2024-05-13)
------------------

- fix export with custom column name (`1821 <https://github.com/django-import-export/django-import-export/pull/1821>`_)
- fix allow ``column_name`` to be declared in ``fields`` list (`1822 <https://github.com/django-import-export/django-import-export/pull/1822>`_)
- fix clash between ``key_is_id`` and ``use_natural_foreign_keys`` (`1824 <https://github.com/django-import-export/django-import-export/pull/1824>`_)
- remove unreachable code (`1825 <https://github.com/django-import-export/django-import-export/pull/1825>`_)
- fix issue with widget assignment for custom ``ForeignKey`` subclasses (`1826 <https://github.com/django-import-export/django-import-export/pull/1826>`_)
- performance: select of valid pks for export restricted to action exports (`1827 <https://github.com/django-import-export/django-import-export/pull/1827>`_)
- fix crash on export with custom column name (`1828 <https://github.com/django-import-export/django-import-export/pull/1828>`_)
- remove outdated datetime formatting logic (`1830 <https://github.com/django-import-export/django-import-export/pull/1830>`_)

4.0.1 (2024-05-08)
------------------

- fix crash on export when model has no ``id`` (`1802 <https://github.com/django-import-export/django-import-export/pull/1802>`_)
- fix Widget crash when django Field subclass is used (`1805 <https://github.com/django-import-export/django-import-export/pull/1805>`_)
- fix regression: allow imports when default ``import_id_field`` is not present (`1813 <https://github.com/django-import-export/django-import-export/pull/1813>`_)

4.0.0 (2024-04-27)
------------------

Deprecations
############

- Removed v3 deprecations (`1629 <https://github.com/django-import-export/django-import-export/pull/1629>`_)
- Deprecation of ``ExportViewFormMixin`` (`1666 <https://github.com/django-import-export/django-import-export/pull/1666>`_)

Enhancements
############

- Refactor ordering logic (`1626 <https://github.com/django-import-export/django-import-export/pull/1626>`_)

  - Refactor 'diff' logic to avoid calling dehydrate methods

  - Refactor declarations of ``fields``, ``import_order`` and ``export_order`` to fix ordering issues

- refactor to export HTML / formulae escaping updates (`1638 <https://github.com/django-import-export/django-import-export/pull/1638>`_)
- removed unused variable ``Result.new_record`` (`1640 <https://github.com/django-import-export/django-import-export/pull/1640>`_)
- Refactor ``resources.py`` to standardise method args (`1641 <https://github.com/django-import-export/django-import-export/pull/1641>`_)
- added specific check for missing ``import_id_fields`` (`1645 <https://github.com/django-import-export/django-import-export/pull/1645>`_)
- Enable optional tablib dependencies (`1647 <https://github.com/django-import-export/django-import-export/pull/1647>`_)
- added :meth:`~import_export.widgets.ForeignKeyWidget.get_lookup_kwargs` to make it easier to override object lookup (`1651 <https://github.com/django-import-export/django-import-export/pull/1651>`_)
- Standardised interface of :meth:`~import_export.widgets.Widget.render` (`1657 <https://github.com/django-import-export/django-import-export/pull/1657>`_)
- Fix declaring existing model field(s) in ModelResource altering export order (`1663 <https://github.com/django-import-export/django-import-export/pull/1663>`_)
- Added :meth:`~import_export.resources.Resource.do_instance_save` helper method (`1668 <https://github.com/django-import-export/django-import-export/pull/1668>`_)
- Enable defining Resource model as a string (`1669 <https://github.com/django-import-export/django-import-export/pull/1669>`_)
- Support multiple Resources for export (`1671 <https://github.com/django-import-export/django-import-export/pull/1671>`_)
- Support export from model change form (`1687 <https://github.com/django-import-export/django-import-export/pull/1687>`_)
- Import form defaults to read-only field if only one format defined (`1690 <https://github.com/django-import-export/django-import-export/pull/1690>`_)
- Updated Admin UI to track deleted and skipped Imports (`1691 <https://github.com/django-import-export/django-import-export/pull/1691>`_)
- Added customizable ``MediaStorage`` (`1708 <https://github.com/django-import-export/django-import-export/pull/1708>`_)
- Added customization of Admin UI import error messages (`1727 <https://github.com/django-import-export/django-import-export/pull/1727>`_)
- Improve output of error messages (`1729 <https://github.com/django-import-export/django-import-export/pull/1729>`_)
- Added feature: selectable fields for admin export view (`1734 <https://github.com/django-import-export/django-import-export/pull/1734>`_)
- Added specific check for declared :attr:`~import_export.options.ResourceOptions.import_id_fields` not in dataset (`1735 <https://github.com/django-import-export/django-import-export/pull/1735>`_)
- added try / catch to :meth:`~import_export.results.RowResult.add_instance_info` to handle unserializable instances (`1767 <https://github.com/django-import-export/django-import-export/pull/1767>`_)
- Add form error if source file contains invalid header (`1780 <https://github.com/django-import-export/django-import-export/pull/1780>`_)
- Remove unneeded format method overrides (`1785 <https://github.com/django-import-export/django-import-export/pull/1785>`_)
- Support dynamic selection of Resource class based on request property (`1787 <https://github.com/django-import-export/django-import-export/pull/1787>`_)

Fixes
#####

- dynamic widget parameters for CharField fixes 'NOT NULL constraint' error in xlsx (`1485 <https://github.com/django-import-export/django-import-export/pull/1485>`_)
- fix cooperation with adminsortable2 (`1633 <https://github.com/django-import-export/django-import-export/pull/1633>`_)
- Removed unused method ``utils.original()``
- Fix deprecated ``log_action`` method (`1673 <https://github.com/django-import-export/django-import-export/pull/1673>`_)
- fix multiple inheritance not setting options (`1696 <https://github.com/django-import-export/django-import-export/pull/1696>`_)
- Fix issue where declared Resource fields not defined in ``fields`` are still imported (`1702 <https://github.com/django-import-export/django-import-export/pull/1702>`_)
- Fixed handling of :attr:`~import_export.exceptions.FieldError` during Admin import (`1755 <https://github.com/django-import-export/django-import-export/pull/1755>`_)
- Fixed handling of django ``FieldError`` during Admin export (`1756 <https://github.com/django-import-export/django-import-export/pull/1756>`_)
- Add check for type to :meth:`~import_export.widgets.Widget.render` (`1757 <https://github.com/django-import-export/django-import-export/pull/1757>`_)
- fix: YAML export does not work with SafeString (`1762 <https://github.com/django-import-export/django-import-export/pull/1762>`_)
- fix: :meth:`~import_export.widgets.SimpleArrayWidget.render` crashes if value is ``None`` (`1771 <https://github.com/django-import-export/django-import-export/pull/1771>`_)
- fix form not being passed to ``get_import_resource_kwargs()`` (`1789 <https://github.com/django-import-export/django-import-export/pull/1789>`_)
- Fix: Missing default widget for ``PositiveBigIntegerField`` (`1795 <https://github.com/django-import-export/django-import-export/pull/1795>`_)

Development
###########

- Refactor build process (`1630 <https://github.com/django-import-export/django-import-export/pull/1630>`_)
- Refactored ``test_admin_integration()``: split into smaller test modules (`1662 <https://github.com/django-import-export/django-import-export/pull/1662>`_)
- Refactored ``test_resources()``: split into smaller test modules (`1672 <https://github.com/django-import-export/django-import-export/pull/1672>`_)
- Updated ``docker-compose`` command with latest version syntax in ``runtests.sh`` (`1686 <https://github.com/django-import-export/django-import-export/pull/1686>`_)
- Refactored :mod:`~import_export.resources` into separate modules for ``declarative`` and ``options`` (`1695 <https://github.com/django-import-export/django-import-export/pull/1695>`_)
- Refactored tests to remove dependencies between tests (`1703 <https://github.com/django-import-export/django-import-export/pull/1703>`_)
- Handle python3.12 datetime deprecations (`1705 <https://github.com/django-import-export/django-import-export/pull/1705>`_)
- Refactor ``test_resources.py`` into smaller modules (`1733 <https://github.com/django-import-export/django-import-export/pull/1733>`_)
- Updated test coverage to include error row when ``collect_failed_rows`` is ``True`` (`1753 <https://github.com/django-import-export/django-import-export/pull/1753>`_)
- Removed support for django 3.2 (`1790 <https://github.com/django-import-export/django-import-export/pull/1790>`_)
- Added test for widgets generating by model fields `1795 <https://github.com/django-import-export/django-import-export/pull/1795>`_)

Documentation
#############

- Clarified ``skip_diff`` documentation (`1655 <https://github.com/django-import-export/django-import-export/pull/1655>`_)
- Improved documentation relating to validation on import (`1665 <https://github.com/django-import-export/django-import-export/pull/1665>`_)
- Added FAQ entry for exporting large datasets (`1706 <https://github.com/django-import-export/django-import-export/pull/1706>`_)
- Relocated admin integration section from advanced_usage.rst into new file (`1713 <https://github.com/django-import-export/django-import-export/pull/1713>`_)
- Updated Admin integration documentation to clarify how to save custom form values (`1746 <https://github.com/django-import-export/django-import-export/pull/1746>`_)

Performance
###########

- Fix slow export with ForeignKey id (`1717 <https://github.com/django-import-export/django-import-export/pull/1717>`_)

i18n
####

- updated translations for release-4 (`1775 <https://github.com/django-import-export/django-import-export/pull/1775>`_)

3.3.9 (2024-04-28)
------------------

- Update translations for Russian language (`1797 <https://github.com/django-import-export/django-import-export/pull/1797>`_)

3.3.8 (2024-04-08)
------------------

- Add additional django template block for extending import page (`1776 <https://github.com/django-import-export/django-import-export/pull/1776>`_)

3.3.7 (2024-02-03)
------------------

- Pass :meth:`~import_export.mixins.BaseExportMixin.get_export_resource_kwargs` to Resource constructor
  :meth:`~import_export.admin.ExportMixin.export_action` (`1739 <https://github.com/django-import-export/django-import-export/pull/1739>`_)
- Fix issue with model class passed to Resource constructor crashing on export (`1745 <https://github.com/django-import-export/django-import-export/pull/1745>`_)
- Fix indentation for skip_row docstring (`1743 <https://github.com/django-import-export/django-import-export/pull/1743>`_)
- Return ``kwargs`` by default from :meth:`~import_export.mixins.BaseImportExportMixin.get_resource_kwargs` (`1748 <https://github.com/django-import-export/django-import-export/pull/1748>`_)

3.3.6 (2024-01-10)
------------------

- Fix issue with highlight when using 'light' color scheme (`1728 <https://github.com/django-import-export/django-import-export/pull/1728>`_)

3.3.5 (2023-12-19)
------------------

- Remove unnecessary ChangeList queries to speed up export via Admin UI (`1715 <https://github.com/django-import-export/django-import-export/pull/1715>`_)
- Respect color scheme override (`1720 <https://github.com/django-import-export/django-import-export/pull/1720>`_)
- Update FAQ to cover skipping rows with validation errors (`1721 <https://github.com/django-import-export/django-import-export/pull/1721>`_)

3.3.4 (2023-12-09)
------------------

- Added support for django5 (`1634 <https://github.com/django-import-export/django-import-export/pull/1634>`_)
- Show list of exported fields in Admin UI (`1685 <https://github.com/django-import-export/django-import-export/pull/1685>`_)
- Added `CONTRIBUTING.md`
- Added support for python 3.12 (`1698 <https://github.com/django-import-export/django-import-export/pull/1698>`_)
- Update Finnish translations (`1701 <https://github.com/django-import-export/django-import-export/pull/1701>`_)

3.3.3 (2023-11-11)
------------------

- :meth:`~import_export.admin.ExportActionMixin.export_admin_action` can be overridden by subclassing it in the
  ``ModelAdmin`` (`1681 <https://github.com/django-import-export/django-import-export/pull/1681>`_)

3.3.2 (2023-11-09)
------------------

- Updated Spanish translations (`1639 <https://github.com/django-import-export/django-import-export/pull/1639>`_)
- Added documentation and tests for retrieving instance information after import (`1643 <https://github.com/django-import-export/django-import-export/pull/1643>`_)
- :meth:`~import_export.widgets.NumberWidget.render` returns ``None`` as empty string
  if ``coerce_to_string`` is True (`1650 <https://github.com/django-import-export/django-import-export/pull/1650>`_)
- Updated documentation to describe how to select for export in Admin UI (`1670 <https://github.com/django-import-export/django-import-export/pull/1670>`_)
- Added catch for django5 deprecation warning (`1676 <https://github.com/django-import-export/django-import-export/pull/1676>`_)
- Updated and compiled message files (`1678 <https://github.com/django-import-export/django-import-export/pull/1678>`_)

3.3.1 (2023-09-14)
------------------

- Added `.readthedocs.yaml` (`1625 <https://github.com/django-import-export/django-import-export/pull/1625>`_)

3.3.0 (2023-09-14)
------------------

Deprecations
############

- Remove 'escape output' deprecation (`1618 <https://github.com/django-import-export/django-import-export/pull/1618>`_)

  - Removal of deprecated :ref:`IMPORT_EXPORT_ESCAPE_OUTPUT_ON_EXPORT`.

  - Deprecation of :ref:`IMPORT_EXPORT_ESCAPE_HTML_ON_EXPORT`.  Refer to :ref:`installation` docs.

Enhancements
############

- Refactoring and fix to support filtering exports (`1579 <https://github.com/django-import-export/django-import-export/pull/1579>`_)
- Store ``instance`` and ``original`` object in :class:`~import_export.results.RowResult` (`1584 <https://github.com/django-import-export/django-import-export/pull/1584>`_)
- Add customizable blocks in import.html (`1598 <https://github.com/django-import-export/django-import-export/pull/1598>`_)
- Include 'allowed formats' settings (`1606 <https://github.com/django-import-export/django-import-export/pull/1606>`_)
- Add kwargs to enable CharWidget to return values as strings (`1623 <https://github.com/django-import-export/django-import-export/pull/1623>`_)

Internationalization
####################

- Add Finnish translation (`1588 <https://github.com/django-import-export/django-import-export/pull/1588>`_)
- Updated ru translation (`1604 <https://github.com/django-import-export/django-import-export/pull/1604>`_)
- Fixed badly formatted translation string (`1622 <https://github.com/django-import-export/django-import-export/pull/1622>`_)
- Remove 'escape output' deprecation (`1618 <https://github.com/django-import-export/django-import-export/pull/1618>`_)

Fixes
#####

- Do not decode bytes when writing to MediaStorage (`1615 <https://github.com/django-import-export/django-import-export/pull/1615>`_)
- Fix for cache entries not removed (`1621 <https://github.com/django-import-export/django-import-export/pull/1621>`_)

Development
###########

- Added support for Django 4.2 (`1570 <https://github.com/django-import-export/django-import-export/pull/1570>`_)
- Add automatic formatting and linting (`1571 <https://github.com/django-import-export/django-import-export/pull/1571>`_)
- removed duplicate admin integration tests (`1616 <https://github.com/django-import-export/django-import-export/pull/1616>`_)
- Removed support for python3.7 and django4.0 (past EOL) (`1618 <https://github.com/django-import-export/django-import-export/pull/1618>`_)

Documentation
#############

- Updated documentation for interoperability with third party libraries (`1614 <https://github.com/django-import-export/django-import-export/pull/1614>`_)

3.2.0 (2023-04-12)
------------------

- Escape formulae on export to XLSX (`1568 <https://github.com/django-import-export/django-import-export/pull/1568>`_)

  - This includes deprecation of :ref:`IMPORT_EXPORT_ESCAPE_OUTPUT_ON_EXPORT`.

    Refer to :ref:`installation` for alternatives.

  - :meth:`import_export.formats.TablibFormat.export()`: ``escape_output`` flag now deprecated in favour of
    ``escape_html`` and ``escape_formulae``.

- Refactor methods so that ``args`` are declared correctly (`1566 <https://github.com/django-import-export/django-import-export/pull/1566>`_)

  - This includes deprecations to be aware of if you have overridden :meth:`~import_export.resources.Resource.export`
    or :class:`~import_export.forms.ImportExportFormBase`.

    - ``export()``: If passing ``queryset`` as the first arg, ensure this is passed as a named parameter.

    - ``ImportExportFormBase``: If passing ``resources`` to ``__init__`` as the first arg, ensure this is
      passed as a named parameter.

- Updated ``setup.py`` (`1564 <https://github.com/django-import-export/django-import-export/pull/1564>`_)
- Added ``SECURITY.md`` (`1563 <https://github.com/django-import-export/django-import-export/pull/1563>`_)
- Updated FAQ to include workaround for `RelatedObjectDoesNotExist` exception (`1562 <https://github.com/django-import-export/django-import-export/pull/1562>`_)
- Prevent error comparing m2m field of the new objects (`1560 <https://github.com/django-import-export/django-import-export/pull/1560>`_)
- Add documentation for passing data from admin form to Resource  (`1555 <https://github.com/django-import-export/django-import-export/pull/1555>`_)
- Added new translations to Spanish and Spanish (Argentina) (`1552 <https://github.com/django-import-export/django-import-export/pull/1552>`_)
- Pass kwargs to import_set function (`1448 <https://github.com/django-import-export/django-import-export/pull/1448>`_)

3.1.0 (2023-02-21)
------------------

- Float and Decimal widgets use LANGUAGE_CODE on export (`1501 <https://github.com/django-import-export/django-import-export/pull/1501>`_)
- Add optional dehydrate method param (`1536 <https://github.com/django-import-export/django-import-export/pull/1536>`_)

  - ``exceptions`` module has been undeprecated

- Updated DE translation (`1537 <https://github.com/django-import-export/django-import-export/pull/1537>`_)
- Add option for single step import via Admin Site (`1540 <https://github.com/django-import-export/django-import-export/pull/1540>`_)
- Add support for m2m add (`1545 <https://github.com/django-import-export/django-import-export/pull/1545>`_)
- collect errors on bulk operations (`1541 <https://github.com/django-import-export/django-import-export/pull/1541>`_)

  - this change causes bulk import errors to be logged at DEBUG level not EXCEPTION.

- Improve bulk import performance (`1539 <https://github.com/django-import-export/django-import-export/pull/1539>`_)

  - ``raise_errors`` has been deprecated as a kwarg in ``import_row()``

- Reduce memory footprint during import (`1542 <https://github.com/django-import-export/django-import-export/pull/1542>`_)
- documentation updates (`1533 <https://github.com/django-import-export/django-import-export/pull/1533>`_)
- add detailed format parameter docstrings to ``DateWidget`` and ``TimeWidget`` (`1532 <https://github.com/django-import-export/django-import-export/pull/1532>`_)
- tox updates (`1534 <https://github.com/django-import-export/django-import-export/pull/1534>`_)
- fix xss vulnerability in html export (`1546 <https://github.com/django-import-export/django-import-export/pull/1546>`_)

3.0.2 (2022-12-13)
------------------

- Support Python 3.11 (`1508 <https://github.com/django-import-export/django-import-export/pull/1508>`_)
- use ``get_list_select_related`` in ``ExportMixin`` (`1511 <https://github.com/django-import-export/django-import-export/pull/1511>`_)
- bugfix: handle crash on start-up when ``change_list_template`` is a property (`1523 <https://github.com/django-import-export/django-import-export/pull/1523>`_)
- bugfix: include instance info in row result when row is skipped (`1526 <https://github.com/django-import-export/django-import-export/pull/1526>`_)
- bugfix: add ``**kwargs`` param to ``Resource`` constructor (`1527 <https://github.com/django-import-export/django-import-export/pull/1527>`_)

3.0.1 (2022-10-18)
------------------

- Updated ``django-import-export-ci.yml`` to fix node.js deprecation
- bugfix: ``DateTimeWidget.clean()`` handles tz aware datetime (`1499 <https://github.com/django-import-export/django-import-export/pull/1499>`_)
- Updated translations for v3.0.0 release (`1500 <https://github.com/django-import-export/django-import-export/pull/1500>`_)

3.0.0 (2022-10-18)
------------------

Breaking changes
################

This release makes some minor changes to the public API.  If you have overridden any methods from the ``resources`` or ``widgets`` modules, you may need to update your implementation to accommodate these changes.

- Check value of ``ManyToManyField`` in ``skip_row()`` (`1271 <https://github.com/django-import-export/django-import-export/pull/1271>`_)
    - This fixes an issue where ManyToMany fields are not checked correctly in ``skip_row()``.  This means that ``skip_row()`` now takes ``row`` as a mandatory arg.  If you have overridden ``skip_row()`` in your own implementation, you will need to add ``row`` as an arg.

- Bug fix: validation errors were being ignored when ``skip_unchanged`` is set (`1378 <https://github.com/django-import-export/django-import-export/pull/1378>`_)
    - If you have overridden ``skip_row()`` you can choose whether or not to skip rows if validation errors are present.  The default behavior is to not to skip rows if there are validation errors during import.

- Use 'create' flag instead of instance.pk (`1362 <https://github.com/django-import-export/django-import-export/pull/1362>`_)
    - ``import_export.resources.save_instance()`` now takes an additional mandatory argument: ``is_create``.  If you have overridden ``save_instance()`` in your own code, you will need to add this new argument.

- ``widgets``: Unused ``*args`` params have been removed from method definitions. (`1413 <https://github.com/django-import-export/django-import-export/pull/1413>`_)
    - If you have overridden ``clean()`` then you should update your method definition to reflect this change.
    - ``widgets.ForeignKeyWidget`` / ``widgets.ManyToManyWidget``: The unused ``*args`` param has been removed from ``__init__()``.  If you have overridden ``ForeignKeyWidget`` or ``ManyToManyWidget`` you may need to update your implementation to reflect this change.

- Admin interface: Modified handling of import errors (`1306 <https://github.com/django-import-export/django-import-export/pull/1306>`_)
    - Exceptions raised during the import process are now presented as form errors, instead of being wrapped in a \<H1\> tag in the response.  If you have any custom logic which uses the error written directly into the response, then this may need to be changed.

- ImportForm: improve compatibility with previous signature (`1434 <https://github.com/django-import-export/django-import-export/pull/1434>`_)
    - Previous ``ImportForm`` implementation was based on Django's ``forms.Form``, if you have any custom ImportForm you now need to inherit from ``import_export.forms.ImportExportFormBase``.

- Allow custom ``change_list_template`` in admin views using mixins (`1483 <https://github.com/django-import-export/django-import-export/pull/1483>`_)
    - If you are using admin mixins from this library in conjunction with code that overrides ``change_list_template`` (typically admin mixins from other libraries such as django-admin-sortable2 or reversion), object tools in the admin change list views may render differently now.
    - If you have created a custom template which extends any import_export template, then this may now cause a recursion error (see `1415  <https://github.com/django-import-export/django-import-export/pull/1415 >`_)

- ``import.html``: Added blocks to import template (`1488 <https://github.com/django-import-export/django-import-export/pull/1488>`_)
    - If you have made customizations to the import template then you may need to refactor these after the addition of block declarations.

Deprecations
############

This release adds some deprecations which will be removed in a future release.

- Add support for multiple resources in ModelAdmin. (`1223 <https://github.com/django-import-export/django-import-export/pull/1223>`_)

    - The ``*Mixin.resource_class`` accepting single resource has been deprecated and the new ``*Mixin.resource_classes`` accepting subscriptable type (list, tuple, ...) has been added.

    - Same applies to all of the ``get_resource_class``, ``get_import_resource_class`` and ``get_export_resource_class`` methods.

- Deprecated ``exceptions.py`` (`1372 <https://github.com/django-import-export/django-import-export/pull/1372>`_)

- Refactored form-related methods on ``ImportMixin`` / ``ExportMixin`` (`1147 <https://github.com/django-import-export/django-import-export/pull/1147>`_)

    - The following are deprecated:

      - ``get_import_form()``

      - ``get_confirm_import_form()``

      - ``get_form_kwargs()``

      - ``get_export_form()``

Enhancements
############

- Default format selections set correctly for export action (`1389 <https://github.com/django-import-export/django-import-export/pull/1389>`_)
- Added option to store raw row values in each row's ``RowResult`` (`1393 <https://github.com/django-import-export/django-import-export/pull/1393>`_)
- Add natural key support to ``ForeignKeyWidget`` (`1371 <https://github.com/django-import-export/django-import-export/pull/1371>`_)
- Optimised default instantiation of ``CharWidget`` (`1414 <https://github.com/django-import-export/django-import-export/pull/1414>`_)
- Allow custom ``change_list_template`` in admin views using mixins (`1483 <https://github.com/django-import-export/django-import-export/pull/1483>`_)
- Added blocks to import template (`1488 <https://github.com/django-import-export/django-import-export/pull/1488>`_)
- improve compatibility with previous ImportForm signature (`1434 <https://github.com/django-import-export/django-import-export/pull/1434>`_)
- Refactored form-related methods on ``ImportMixin`` / ``ExportMixin`` (`1147 <https://github.com/django-import-export/django-import-export/pull/1147>`_)
- Include custom form media in templates (`1038 <https://github.com/django-import-export/django-import-export/pull/1038>`_)
- Remove unnecessary files generated when running tox locally (`1426 <https://github.com/django-import-export/django-import-export/pull/1426>`_)

Fixes
#####

- Fixed Makefile coverage: added ``coverage combine``
- Fixed handling of LF character when using ``CacheStorage`` (`1417 <https://github.com/django-import-export/django-import-export/pull/1417>`_)
- bugfix: ``skip_row()`` handles M2M field when UUID pk used
- Fix broken link to tablib formats page (`1418 <https://github.com/django-import-export/django-import-export/pull/1418>`_)
- Fix broken image ref in ``README.rst``
- bugfix: ``skip_row()`` fix crash when model has m2m field and none is provided in upload (`1439 <https://github.com/django-import-export/django-import-export/pull/1439>`_)
- Fix deprecation in example application: Added support for transitional form renderer (`1451 <https://github.com/django-import-export/django-import-export/pull/1451>`_)

Development
###########

- Increased test coverage, refactored CI build to use tox (`1372 <https://github.com/django-import-export/django-import-export/pull/1372>`_)

Documentation
#############

- Clarified issues around the usage of temporary storage (`1306 <https://github.com/django-import-export/django-import-export/pull/1306>`_)

2.9.0 (2022-09-14)
------------------

- Fix deprecation in example application: Added support for transitional form renderer (`1451 <https://github.com/django-import-export/django-import-export/pull/1451>`_)
- Escape HTML output when rendering decoding errors (`1469 <https://github.com/django-import-export/django-import-export/pull/1469>`_)
- Apply make_aware when the original file contains actual datetimes (`1478 <https://github.com/django-import-export/django-import-export/pull/1478>`_)
- Automatically guess the format of the file when importing (`1460 <https://github.com/django-import-export/django-import-export/pull/1460>`_)

2.8.0 (2022-03-31)
------------------

- Updated import.css to support dark mode (`1318 <https://github.com/django-import-export/django-import-export/pull/1318>`_)
- Fix crash when import_data() called with empty Dataset and ``collect_failed_rows=True`` (`1381 <https://github.com/django-import-export/django-import-export/pull/1381>`_)
- Improve Korean translation (`1402 <https://github.com/django-import-export/django-import-export/pull/1402>`_)
- Update example subclass widget code (`1407 <https://github.com/django-import-export/django-import-export/pull/1407>`_)
- Drop support for python3.6, django 2.2, 3.0, 3.1 (`1408 <https://github.com/django-import-export/django-import-export/pull/1408>`_)
- Add get_export_form() to ExportMixin (`1409 <https://github.com/django-import-export/django-import-export/pull/1409>`_)

2.7.1 (2021-12-23)
------------------

- Removed ``django_extensions`` from example app settings (`1356 <https://github.com/django-import-export/django-import-export/pull/1356>`_)
- Added support for Django 4.0 (`1357 <https://github.com/django-import-export/django-import-export/pull/1357>`_)

2.7.0 (2021-12-07)
------------------

- Big integer support for Integer widget (`788 <https://github.com/django-import-export/django-import-export/pull/788>`_)
- Run compilemessages command to keep .mo files in sync (`1299 <https://github.com/django-import-export/django-import-export/pull/1299>`_)
- Added ``skip_html_diff`` meta attribute (`1329 <https://github.com/django-import-export/django-import-export/pull/1329>`_)
- Added python3.10 to tox and CI environment list (`1336 <https://github.com/django-import-export/django-import-export/pull/1336>`_)
- Add ability to rollback the import on validation error (`1339 <https://github.com/django-import-export/django-import-export/pull/1339>`_)
- Fix missing migration on example app (`1346 <https://github.com/django-import-export/django-import-export/pull/1346>`_)
- Fix crash when deleting via admin site (`1347 <https://github.com/django-import-export/django-import-export/pull/1347>`_)
- Use Github secret in CI script instead of hard-coded password (`1348 <https://github.com/django-import-export/django-import-export/pull/1348>`_)
- Documentation: correct error in example application which leads to crash (`1353 <https://github.com/django-import-export/django-import-export/pull/1353>`_)

2.6.1 (2021-09-30)
------------------

- Revert 'dark mode' css: causes issues in django2.2 (`1330 <https://github.com/django-import-export/django-import-export/pull/1330>`_)

2.6.0 (2021-09-15)
------------------

- Added guard for null 'options' to fix crash (`1325 <https://github.com/django-import-export/django-import-export/pull/1325>`_)
- Updated import.css to support dark mode (`1323 <https://github.com/django-import-export/django-import-export/pull/1323>`_)
- Fixed regression where overridden mixin methods are not called (`1315 <https://github.com/django-import-export/django-import-export/pull/1315>`_)
- Fix xls/xlsx import of Time fields (`1314 <https://github.com/django-import-export/django-import-export/pull/1314>`_)
- Added support for 'to_encoding' attribute (`1311 <https://github.com/django-import-export/django-import-export/pull/1311>`_)
- Removed travis and replaced with github actions for CI (`1307 <https://github.com/django-import-export/django-import-export/pull/1307>`_)
- Increased test coverage (`1286 <https://github.com/django-import-export/django-import-export/pull/1286>`_)
- Fix minor date formatting issue for date with years < 1000 (`1285 <https://github.com/django-import-export/django-import-export/pull/1285>`_)
- Translate the zh_Hans missing part (`1279 <https://github.com/django-import-export/django-import-export/pull/1279>`_)
- Remove code duplication from mixins.py and admin.py (`1277 <https://github.com/django-import-export/django-import-export/pull/1277>`_)
- Fix example in BooleanWidget docs (`1276 <https://github.com/django-import-export/django-import-export/pull/1276>`_)
- Better support for Django main (`1272 <https://github.com/django-import-export/django-import-export/pull/1272>`_)
- don't test Django main branch with python36,37 (`1269 <https://github.com/django-import-export/django-import-export/pull/1269>`_)
- Support Django 3.2 (`1265 <https://github.com/django-import-export/django-import-export/pull/1265>`_)
- Correct typo in Readme (`1258 <https://github.com/django-import-export/django-import-export/pull/1258>`_)
- Rephrase logical clauses in docstrings (`1255 <https://github.com/django-import-export/django-import-export/pull/1255>`_)
- Support multiple databases (`1254 <https://github.com/django-import-export/django-import-export/pull/1254>`_)
- Update django master to django main (`1251 <https://github.com/django-import-export/django-import-export/pull/1251>`_)
- Add Farsi translated messages in the locale (`1249 <https://github.com/django-import-export/django-import-export/pull/1249>`_)
- Update Russian translations (`1244 <https://github.com/django-import-export/django-import-export/pull/1244>`_)
- Append export admin action using ModelAdmin.get_actions (`1241 <https://github.com/django-import-export/django-import-export/pull/1241>`_)
- Fix minor mistake in makemigrations command (`1233 <https://github.com/django-import-export/django-import-export/pull/1233>`_)
- Remove EOL Python 3.5 from CI (`1228 <https://github.com/django-import-export/django-import-export/pull/1228>`_)
- CachedInstanceLoader defaults to empty when import_id is missing (`1225 <https://github.com/django-import-export/django-import-export/pull/1225>`_)
- Add kwargs to import_row, import_object and import_field (`1190 <https://github.com/django-import-export/django-import-export/pull/1190>`_)
- Call load_workbook() with data_only flag (`1095 <https://github.com/django-import-export/django-import-export/pull/1095>`_)


2.5.0 (2020-12-30)
------------------

- Changed the default value for ``IMPORT_EXPORT_CHUNK_SIZE`` to 100. (`1196 <https://github.com/django-import-export/django-import-export/pull/1196>`_)
- Add translation for Korean (`1218 <https://github.com/django-import-export/django-import-export/pull/1218>`_)
- Update linting, CI, and docs.


2.4.0 (2020-10-05)
------------------

- Fix deprecated Django 3.1 ``Signal(providing_args=...)`` usage.
- Fix deprecated Django 3.1 ``django.conf.urls.url()`` usage.


2.3.0 (2020-07-12)
------------------

- Add missing translation keys for all languages (`1144 <https://github.com/django-import-export/django-import-export/pull/1144>`_)
- Added missing Portuguese translations (`1145 <https://github.com/django-import-export/django-import-export/pull/1145>`_)
- Add kazakh translations (`1161 <https://github.com/django-import-export/django-import-export/pull/1161>`_)
- Add bulk operations (`1149 <https://github.com/django-import-export/django-import-export/pull/1149>`_)

2.2.0 (2020-06-01)
------------------

- Deal with importing a BooleanField that actually has ``True``, ``False``, and
  ``None`` values. (`1071 <https://github.com/django-import-export/django-import-export/pull/1071>`_)
- Add row_number parameter to before_import_row, after_import_row and after_import_instance (`1040 <https://github.com/django-import-export/django-import-export/pull/1040>`_)
- Paginate queryset if Queryset.prefetch_related is used (`1050 <https://github.com/django-import-export/django-import-export/pull/1050>`_)

2.1.0 (2020-05-02)
------------------

- Fix DurationWidget handling of zero value (`1117 <https://github.com/django-import-export/django-import-export/pull/1117>`_)

- Make import diff view only show headers for user visible fields (`1109 <https://github.com/django-import-export/django-import-export/pull/1109>`_)

- Make confirm_form accessible in get_import_resource_kwargs and get_import_data_kwargs (`994 <https://github.com/django-import-export/django-import-export/pull/994>`_, `1108 <https://github.com/django-import-export/django-import-export/pull/1108>`_)

- Initialize Decimal with text value, fix #1035 (`1039 <https://github.com/django-import-export/django-import-export/pull/1039>`_)

- Adds meta flag 'skip_diff' to enable skipping of diff operations (`1045 <https://github.com/django-import-export/django-import-export/pull/1045>`_)

- Update docs (`1097 <https://github.com/django-import-export/django-import-export/pull/1097>`_, `1114 <https://github.com/django-import-export/django-import-export/pull/1114>`_, `1122 <https://github.com/django-import-export/django-import-export/pull/1122>`_, `969 <https://github.com/django-import-export/django-import-export/pull/969>`_, `1083 <https://github.com/django-import-export/django-import-export/pull/1083>`_, `1093 <https://github.com/django-import-export/django-import-export/pull/1093>`_)

2.0.2 (2020-02-16)
------------------

- Add support for tablib >= 1.0 (`1061 <https://github.com/django-import-export/django-import-export/pull/1061>`_)

- Add ability to install a subset of tablib supported formats and save some
  automatic dependency installations (needs tablib >= 1.0)

- Use column_name when checking row for fields (`1056 <https://github.com/django-import-export/django-import-export/pull/1056>`_)

2.0.1 (2020-01-15)
------------------

- Fix deprecated Django 3.0 function usage (`1054 <https://github.com/django-import-export/django-import-export/pull/1054>`_)

- Pin tablib version to not use new major version (`1063 <https://github.com/django-import-export/django-import-export/pull/1063>`_)

- Format field is always shown on Django 2.2 (`1007 <https://github.com/django-import-export/django-import-export/pull/1007>`_)

2.0 (2019-12-03)
----------------

- Removed support for Django < 2.0
- Removed support for Python < 3.5
- feat: Support for Postgres JSONb Field (`904 <https://github.com/django-import-export/django-import-export/pull/904>`_)

1.2.0 (2019-01-10)
------------------

- feat: Better surfacing of validation errors in UI / optional model instance validation (`852 <https://github.com/django-import-export/django-import-export/pull/852>`_)

- chore: Use modern setuptools in setup.py (`862 <https://github.com/django-import-export/django-import-export/pull/862>`_)

- chore: Update URLs to use https:// (`863 <https://github.com/django-import-export/django-import-export/pull/863>`_)

- chore: remove outdated workarounds

- chore: Run SQLite tests with in-memory database

- fix: Change logging level (`832 <https://github.com/django-import-export/django-import-export/pull/832>`_)

- fix: Changed ``get_instance()`` return val (`842 <https://github.com/django-import-export/django-import-export/pull/842>`_)

1.1.0 (2018-10-02)
------------------

- fix: Django2.1 ImportExportModelAdmin export (`797 <https://github.com/django-import-export/django-import-export/pull/797>`_, `819 <https://github.com/django-import-export/django-import-export/pull/819>`_)

- setup: add django2.1 to test matrix

- JSONWidget for jsonb fields (`803 <https://github.com/django-import-export/django-import-export/pull/803>`_)

- Add ExportActionMixin (`809 <https://github.com/django-import-export/django-import-export/pull/809>`_)

- Add Import Export Permissioning #608 (`804 <https://github.com/django-import-export/django-import-export/pull/804>`_)

- write_to_tmp_storage() for import_action() (`781 <https://github.com/django-import-export/django-import-export/pull/781>`_)

- follow relationships on ForeignKeyWidget (`798 <https://github.com/django-import-export/django-import-export/pull/798>`_)

- Update all pypi.python.org URLs to pypi.org

- added test for tsv import

- added unicode support for TSV for python 2

- Added ExportViewMixin (`692 <https://github.com/django-import-export/django-import-export/pull/692>`_)

1.0.1 (2018-05-17)
------------------

- Make deep copy of fields from class attr to instance attr (`550 <https://github.com/django-import-export/django-import-export/pull/550>`_)

- Fix #612: NumberWidget.is_empty() should strip the value if string type (`613 <https://github.com/django-import-export/django-import-export/pull/613>`_)

- Fix #713: last day isn't included in results qs (`779 <https://github.com/django-import-export/django-import-export/pull/779>`_)

- use Python3 compatible MySql driver in development (`706 <https://github.com/django-import-export/django-import-export/pull/706>`_)

- fix: warning U mode is deprecated in python 3 (`776 <https://github.com/django-import-export/django-import-export/pull/776>`_)

- refactor: easier overriding widgets and default field (`769 <https://github.com/django-import-export/django-import-export/pull/769>`_)

- Updated documentation regarding declaring fields (`735 <https://github.com/django-import-export/django-import-export/pull/735>`_)

- custom js for action form also handles grappelli (`719 <https://github.com/django-import-export/django-import-export/pull/719>`_)

- Use 'verbose_name' in breadcrumbs to match Django default (`732 <https://github.com/django-import-export/django-import-export/pull/732>`_)

- Add Resource.get_diff_class() (`745 <https://github.com/django-import-export/django-import-export/pull/745>`_)

- Fix and add polish translation (`747 <https://github.com/django-import-export/django-import-export/pull/747>`_)

- Restore raise_errors to before_import (`749 <https://github.com/django-import-export/django-import-export/pull/749>`_)


1.0.0 (2018-02-13)
------------------

- Switch to semver versioning (`687 <https://github.com/django-import-export/django-import-export/pull/687>`_)

- Require Django>=1.8 (`685 <https://github.com/django-import-export/django-import-export/pull/685>`_)

- upgrade tox configuration (`737 <https://github.com/django-import-export/django-import-export/pull/737>`_)


0.7.0 (2018-01-17)
------------------

- skip_row override example (`702 <https://github.com/django-import-export/django-import-export/pull/702>`_)

- Testing against Django 2.0 should not fail (`709 <https://github.com/django-import-export/django-import-export/pull/709>`_)

- Refactor transaction handling (`690 <https://github.com/django-import-export/django-import-export/pull/690>`_)

- Resolves #703 fields shadowed (`703 <https://github.com/django-import-export/django-import-export/pull/703>`_)

- discourage installation as a zipped egg (`548 <https://github.com/django-import-export/django-import-export/pull/548>`_)

- Fixed middleware settings in test app for Django 2.x (`696 <https://github.com/django-import-export/django-import-export/pull/696>`_)


0.6.1 (2017-12-04)
------------------

- Refactors and optimizations (`686 <https://github.com/django-import-export/django-import-export/pull/686>`_, `632 <https://github.com/django-import-export/django-import-export/pull/632>`_, `684 <https://github.com/django-import-export/django-import-export/pull/684>`_, `636 <https://github.com/django-import-export/django-import-export/pull/636>`_, `631 <https://github.com/django-import-export/django-import-export/pull/631>`_, `629 <https://github.com/django-import-export/django-import-export/pull/629>`_, `635 <https://github.com/django-import-export/django-import-export/pull/635>`_, `683 <https://github.com/django-import-export/django-import-export/pull/683>`_)

- Travis tests for Django 2.0.x (`691 <https://github.com/django-import-export/django-import-export/pull/691>`_)


0.6.0 (2017-11-23)
------------------

- Refactor import_row call by using keyword arguments (`585 <https://github.com/django-import-export/django-import-export/pull/585>`_)

- Added {{ block.super }} call in block bodyclass in admin/base_site.html (`582 <https://github.com/django-import-export/django-import-export/pull/582>`_)

- Add support for the Django DurationField with DurationWidget (`575 <https://github.com/django-import-export/django-import-export/pull/575>`_)

- GitHub bmihelac -> django-import-export Account Update (`574 <https://github.com/django-import-export/django-import-export/pull/574>`_)

- Add intersphinx links to documentation (`572 <https://github.com/django-import-export/django-import-export/pull/572>`_)

- Add Resource.get_import_fields() (`569 <https://github.com/django-import-export/django-import-export/pull/569>`_)

- Fixed readme mistake (`568 <https://github.com/django-import-export/django-import-export/pull/568>`_)

- Bugfix/fix m2m widget clean (`515 <https://github.com/django-import-export/django-import-export/pull/515>`_)

- Allow injection of context data for template rendered by import_action() and export_action() (`544 <https://github.com/django-import-export/django-import-export/pull/544>`_)

- Bugfix/fix exception in generate_log_entries() (`543 <https://github.com/django-import-export/django-import-export/pull/543>`_)

- Process import dataset and result in separate methods (`542 <https://github.com/django-import-export/django-import-export/pull/542>`_)

- Bugfix/fix error in converting exceptions to strings (`526 <https://github.com/django-import-export/django-import-export/pull/526>`_)

- Fix admin integration tests for the new "Import finished..." message, update Czech translations to 100% coverage. (`596 <https://github.com/django-import-export/django-import-export/pull/596>`_)

- Make import form type easier to override (`604 <https://github.com/django-import-export/django-import-export/pull/604>`_)

- Add saves_null_values attribute to Field to control whether null values are saved on the object (`611 <https://github.com/django-import-export/django-import-export/pull/611>`_)

- Add Bulgarian translations (`656 <https://github.com/django-import-export/django-import-export/pull/656>`_)

- Add django 1.11 to TravisCI (`621 <https://github.com/django-import-export/django-import-export/pull/621>`_)

- Make Signals code example format correctly in documentation (`553 <https://github.com/django-import-export/django-import-export/pull/553>`_)

- Add Django as requirement to setup.py (`634 <https://github.com/django-import-export/django-import-export/pull/634>`_)

- Update import of reverse for django 2.x (`620 <https://github.com/django-import-export/django-import-export/pull/620>`_)

- Add Django-version classifiers to setup.py’s CLASSIFIERS (`616 <https://github.com/django-import-export/django-import-export/pull/616>`_)

- Some fixes for Django 2.0 (`672 <https://github.com/django-import-export/django-import-export/pull/672>`_)

- Strip whitespace when looking up ManyToMany fields (`668 <https://github.com/django-import-export/django-import-export/pull/668>`_)

- Fix all ResourceWarnings during tests in Python 3.x (`637 <https://github.com/django-import-export/django-import-export/pull/637>`_)

- Remove downloads count badge from README since shields.io no longer supports it for PyPi (`677 <https://github.com/django-import-export/django-import-export/pull/677>`_)

- Add coveralls support and README badge (`678 <https://github.com/django-import-export/django-import-export/pull/678>`_)


0.5.1 (2016-09-29)
------------------

- French locale not in pypi (`524 <https://github.com/django-import-export/django-import-export/pull/524>`_)

- Bugfix/fix undefined template variables (`519 <https://github.com/django-import-export/django-import-export/pull/519>`_)


0.5.0 (2016-09-01)
------------------

- Hide default value in diff when importing a new instance (`458 <https://github.com/django-import-export/django-import-export/pull/458>`_)

- Append rows to Result object via function call to allow overriding (`462 <https://github.com/django-import-export/django-import-export/pull/462>`_)

- Add get_resource_kwargs to allow passing request to resource (`457 <https://github.com/django-import-export/django-import-export/pull/457>`_)

- Expose Django user to get_export_data() and export() (`447 <https://github.com/django-import-export/django-import-export/pull/447>`_)

- Add before_export and after_export hooks (`449 <https://github.com/django-import-export/django-import-export/pull/449>`_)

- fire events post_import, post_export events (`440 <https://github.com/django-import-export/django-import-export/pull/440>`_)

- add **kwargs to export_data / create_dataset

- Add before_import_row() and after_import_row() (`452 <https://github.com/django-import-export/django-import-export/pull/452>`_)

- Add get_export_fields() to Resource to control what fields are exported (`461 <https://github.com/django-import-export/django-import-export/pull/461>`_)

- Control user-visible fields (`466 <https://github.com/django-import-export/django-import-export/pull/466>`_)

- Fix diff for models using ManyRelatedManager

- Handle already cleaned objects (`484 <https://github.com/django-import-export/django-import-export/pull/484>`_)

- Add after_import_instance hook (`489 <https://github.com/django-import-export/django-import-export/pull/489>`_)

- Use optimized xlsx reader (`482 <https://github.com/django-import-export/django-import-export/pull/482>`_)

- Adds resource_class of BookResource (re-adds) in admin docs (`481 <https://github.com/django-import-export/django-import-export/pull/481>`_)

- Require POST method for process_import() (`478 <https://github.com/django-import-export/django-import-export/pull/478>`_)

- Add SimpleArrayWidget to support use of django.contrib.postgres.fields.ArrayField (`472 <https://github.com/django-import-export/django-import-export/pull/472>`_)

- Add new Diff class (`477 <https://github.com/django-import-export/django-import-export/pull/477>`_)

- Fix #375: add row to widget.clean(), obj to widget.render() (`479 <https://github.com/django-import-export/django-import-export/pull/479>`_)

- Restore transactions for data import (`480 <https://github.com/django-import-export/django-import-export/pull/480>`_)

- Refactor the import-export templates (`496 <https://github.com/django-import-export/django-import-export/pull/496>`_)

- Update doc links to the stable version, update rtfd to .io (`507 <https://github.com/django-import-export/django-import-export/pull/507>`_)

- Fixed typo in the Czech translation (`495 <https://github.com/django-import-export/django-import-export/pull/495>`_)


0.4.5 (2016-04-06)
------------------

- Add FloatWidget, use with model fields models.FloatField (`433 <https://github.com/django-import-export/django-import-export/pull/433>`_)

- Fix default values in fields (`431 <https://github.com/django-import-export/django-import-export/pull/431>`_, `364 <https://github.com/django-import-export/django-import-export/pull/364>`_)

  Field constructor ``default`` argument is NOT_PROVIDED instead of None
  Field clean method checks value against ``Field.empty_values`` [None, '']

0.4.4 (2016-03-22)
------------------

- FIX: No static/ when installed via pip (`427 <https://github.com/django-import-export/django-import-export/pull/427>`_)

- Add total # of imports and total # of updates to import success msg


0.4.3 (2016-03-08)
------------------

- fix MediaStorage does not respect the read_mode parameter (`416 <https://github.com/django-import-export/django-import-export/pull/416>`_)

- Reset SQL sequences when new objects are imported (`59 <https://github.com/django-import-export/django-import-export/pull/59>`_)

- Let Resource rollback if import throws exception (`377 <https://github.com/django-import-export/django-import-export/pull/377>`_)

- Fixes error when a single value is stored in m2m relation field (`177 <https://github.com/django-import-export/django-import-export/pull/177>`_)

- Add support for django.db.models.TimeField (`381 <https://github.com/django-import-export/django-import-export/pull/381>`_)


0.4.2 (2015-12-18)
------------------

- add xlsx import support


0.4.1 (2015-12-11)
------------------

- fix for fields with a dyanmic default callable (`360 <https://github.com/django-import-export/django-import-export/pull/360>`_)


0.4.0 (2015-12-02)
------------------

- Add Django 1.9 support

- Django 1.4 is not supported (`348 <https://github.com/django-import-export/django-import-export/pull/348>`_)


0.3.1 (2015-11-20)
------------------

- FIX: importing csv in python 3


0.3 (2015-11-20)
----------------

- FIX: importing csv UnicodeEncodeError introduced in 0.2.9 (`347 <https://github.com/django-import-export/django-import-export/pull/347>`_)


0.2.9 (2015-11-12)
------------------

- Allow Field.save() relation following (`344 <https://github.com/django-import-export/django-import-export/pull/344>`_)

- Support default values on fields (and models) (`345 <https://github.com/django-import-export/django-import-export/pull/345>`_)

- m2m widget: allow trailing comma (`343 <https://github.com/django-import-export/django-import-export/pull/343>`_)

- Open csv files as text and not binary (`127 <https://github.com/django-import-export/django-import-export/pull/127>`_)


0.2.8 (2015-07-29)
------------------

- use the IntegerWidget for database-fields of type BigIntegerField (`302 <https://github.com/django-import-export/django-import-export/pull/302>`_)

- make datetime timezone aware if USE_TZ is True (`283 <https://github.com/django-import-export/django-import-export/pull/283>`_).

- Fix 0 is interpreted as None in number widgets (`274 <https://github.com/django-import-export/django-import-export/pull/274>`_)

- add possibility to override tmp storage class (`133 <https://github.com/django-import-export/django-import-export/pull/133>`_, `251 <https://github.com/django-import-export/django-import-export/pull/251>`_)

- better error reporting (`259 <https://github.com/django-import-export/django-import-export/pull/259>`_)


0.2.7 (2015-05-04)
------------------

- Django 1.8 compatibility

- add attribute inheritance to Resource (`140 <https://github.com/django-import-export/django-import-export/pull/140>`_)

- make the filename and user available to import_data (`237 <https://github.com/django-import-export/django-import-export/pull/237>`_)

- Add to_encoding functionality (`244 <https://github.com/django-import-export/django-import-export/pull/244>`_)

- Call before_import before creating the instance_loader - fixes (`193 <https://github.com/django-import-export/django-import-export/pull/193>`_)


0.2.6 (2014-10-09)
------------------

- added use of get_diff_headers method into import.html template (`158 <https://github.com/django-import-export/django-import-export/pull/158>`_)

- Try to use OrderedDict instead of SortedDict, which is deprecated in
  Django 1.7 (`157 <https://github.com/django-import-export/django-import-export/pull/157>`_)

- fixed #105 unicode import

- remove invalid form action "form_url" (`154 <https://github.com/django-import-export/django-import-export/pull/154>`_)


0.2.5 (2014-10-04)
------------------

- Do not convert numeric types to string (`149 <https://github.com/django-import-export/django-import-export/pull/149>`_)

- implement export as an admin action (`124 <https://github.com/django-import-export/django-import-export/pull/124>`_)


0.2.4 (2014-09-18)
------------------

- fix: get_value raised attribute error on model method call

- Fixed XLS import on python 3. Optimized loop

- Fixed properly skipping row marked as skipped when importing data from
  the admin interface.

- Allow Resource.export to accept iterables as well as querysets

- Improve error messages

- FIX: Properly handle NullBoleanField (`115 <https://github.com/django-import-export/django-import-export/pull/115>`_) - Backward Incompatible Change
  previously None values were handled as false


0.2.3 (2014-07-01)
------------------

- Add separator and field keyword arguments to ManyToManyWidget

- FIX: No support for dates before 1900 (`93 <https://github.com/django-import-export/django-import-export/pull/93>`_)


0.2.2 (2014-04-18)
------------------

- RowResult now stores exception object rather than it's repr

- Admin integration - add EntryLog object for each added/updated/deleted instance


0.2.1 (2014-02-20)
------------------

- FIX import_file_name form field can be use to access the filesystem (`65 <https://github.com/django-import-export/django-import-export/pull/65>`_)


0.2.0 (2014-01-30)
------------------

- Python 3 support


0.1.6 (2014-01-21)
------------------

* Additional hooks for customizing the workflow (`61 <https://github.com/django-import-export/django-import-export/pull/61>`_)

0.1.5 (2013-11-29)
------------------

* Prevent queryset caching when exporting (`44 <https://github.com/django-import-export/django-import-export/pull/44>`_)

* Allow unchanged rows to be skipped when importing (`30 <https://github.com/django-import-export/django-import-export/pull/30>`_)

* Update tests for Django 1.6 (`57 <https://github.com/django-import-export/django-import-export/pull/57>`_)

* Allow different ``ResourceClass`` to be used in ``ImportExportModelAdmin``
  (`49 <https://github.com/django-import-export/django-import-export/pull/49>`_)

0.1.4
-----

* Use ``field_name`` instead of ``column_name`` for field dehydration, FIX (`36 <https://github.com/django-import-export/django-import-export/pull/36>`_)

* Handle OneToOneField,  FIX (`17 <https://github.com/django-import-export/django-import-export/pull/17>`_) - Exception when attempting access something
  on the related_name.

* export filter not working (`23 <https://github.com/django-import-export/django-import-export/pull/23>`_)

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
