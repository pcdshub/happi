=================
 Release History
=================

v1.10.1 (2021-11-15)
====================

Bugfixes
--------
- Fix a logging format error in ``Client.from_config``

Contributors
------------
- klauer


v1.10.0 (2021-09-27)
====================

Features
--------
- Add ``happi container-registry`` command-line utility. This shows the user
  which ``happi`` containers are registered and available in their session.
  This is very useful for debugging purposes and more generally to
  understand which containers are available.

Maintenance
-----------
- Fix error in the docs build.
- Misc updates to the CI.

Contributors
------------
- unztag
- zrylettc


v1.9.0 (2021-02-10)
===================

Features
--------
- Add ``happi update <json>`` command-line utility. This allows the user to
  pipe in a json blob to the happi CLI to update their database. This enables
  bulk updates in a convenient way.
- Allow short (under 3) and long (over 80) character names. Users who want
  further restrictions on names for their projects are encouraged to create
  a custom container.
- Allow arbitrary user functions to be passed in to the EntryInfo ``enforce``
  field, for custom validation of data. These functions should mimic the
  signature and behavior of the built-in types: take one argument, return the
  value back as-is or cast to the type, raise ValueError if there is an issue.

Bugfixes
--------
- Properly expand home directory (~) in the JSON backend database path.
- Require that the name field does not conflict with reserved Python keywords.
- Fix an issue where boolean fields edited from the command-line were always
  interpreted as True.

Maintenance
-----------
- Update CI to PCDS standards.

Contributors
------------
- klauer
- unztag
- zllentz


v1.8.4 (2021-01-08)
===================

Bugfixes
--------
- Fix an issue where a package implementing a happi containers entrypoint
  could fail to be picked up by the happi registry based on the import order.

Maintenance
-----------
- Revisions, clarifications, and additions to the documentation.
- Docstring style fixes.

Contributors
------------
- klauer
- untzag
- zrylettc


v1.8.3 (2020-11-17)
===================

Bugfixes
--------
- Fix loading of acromag io channels from the lcls questionnaire.
  Previously, these were loading full acromag devices instead of
  individual channels and were using the incorrect PVs.
- Fix loading of Beckhoff axis motors from the lcls questionnaire.
  Previously, these were misidentified as IMS motors.

Maintenance
-----------
- Refactor questionnaire entry creation to accomplish the above.

Contributors
------------
- cristinasewell


v1.8.2 (2020-10-20)
===================

Bugfixes
--------
- Removed hanging raise command from qs loader (hotfix)


v1.8.1 (2020-10-21)
===================

Bugfixes
--------
- Fix various issues causing questionnaire loads to fail.
- Fix clarity issues for failed questionnaire loads.

Maintenance
-----------
- Break up the questionnaire loading routines into more maintainable
  chunks, reorganizing and cleaning up the code.
- Allow introspection of questionnaire state for debugging.


v1.8.0 (2020-10-07)
===================

Features
--------
- Adds bash/fzf-based fuzzy finding of happi items with corresponding
  activate/deactivate scripts.
- Adds ``happi search --json`` option to output JSON instead of a table.

Maintenance
-----------
- Move IPython import to where it's needed in ``happi load``, saving
  approximately half a second on any other ``happi`` CLI invocation.


v1.7.2 (2020-09-17)
===================

Bugfixes
--------
- Fix issue with edge cases in lcls questionnaire loader
- Fix issue with unclear warnings on creating malformed entries

Maintenance
-----------
- Improve testing coverage for CLI functions


v1.7.1 (2020-08-20)
===================

Bugfixes
--------
- Fix cli issue where the ``--clone`` argument would fail.
- Make sure the happi cli returns usage information
  if the user passes no arguments.


v1.7.0 (2020-08-18)
===================

Features
--------
- Add cli search globbing, e.g. now the following will work:
  ``happi search xpp*`` (show all devices whose names start with xpp)

Bugfixes
--------
- Fix issue with silent failure when editing a non-existent field.
- Fix issues related to changing an entry's name field.

Maintenance
-----------
- Add documentation for the happi cli
- Update the db.json examples to use OphydItem


v1.6.1 (2020-07-01)
===================

Bugfixes
--------
-   Do not raise an exception on single malformed entries uncovered during
    a search. Treat these as missing entries. This was causing an issue
    where queries like ``all_devices`` would fail outright.
-   Fix issue where ``device_cls`` string would leak through and raise a
    bad/confusing exception during ``create_device``

Maintenance
-----------
-   Reduce missing backends log messages from ``warning`` to ``debug``.
-   Fix docs failing to build and related issues.
-   Add ``requirements.txt`` file to ``MANIFEST.in``.


v1.6.0 (2020-04-30)
===================

-  LCLS-specific containers are moved out of happi, and into
   `pcdsdevices <https://github.com/pcdshub/pcdsdevices/tree/master/pcdsdevices/happi>`__
-  ``OphydItem`` is now the preferred “basic” ``ophyd.Device``
   container, with the intention of fully deprecating ``Device`` to
   avoid naming confusion
-  Minor internal fixes


v1.5.0 (2020-04-06)
===================

-  Refactor search methods, supporting mongo and JSON backends

   -  ``search`` - search by key/value pairs as kwargs
   -  ``search_range`` - search for a range of values in a specific key
   -  ``search_regex`` - search for key/value pairs as kwargs, with
      values being regular expressions
   -  Adds ``SearchResult`` container, allowing for access of metadata
      or device instantiation

-  ``Client['item']`` supported
-  ``happi.Device`` is now marked as deprecated

   -  Migrate to ``happi.OphydItem``

-  Documentation building fixed and made more accurate
-  Internal refactoring

   -  Reduce usage of metaclasses
   -  pymongo/mongomock are truly optional test dependencies now
   -  Added pre-commit configuration for developer quality-of-life
   -  ``HappiItem``\ s are now ``copy.copy()``-able
   -  Backends supply generators and not lists

-  Fixed many oustanding issues with the JSON backend


v1.4.0 (2020-03-13)
===================

Enhancements
------------

-  Add an add command for cli, e.g. happi add to start an interactive
   device adder
-  Add an edit command for cli, e.g. happi edit im3l0 location=750
   prefix=IM3L0:PPM
-  Change search command syntax to be simpler (more like edit)
-  Add a load command for cli, e.g. happi load im3l0 im1l1 -> IPython
   session plus other changes made in dev to “get it working”
-  Add two new Happi-aware Qt widgets: HappiDeviceListView &
   HappiDeviceTreeView

Bug Fixes
---------

-  Initialize database if it does not yet exists
-  Fix broken tests


v1.3.0 (2019-12-10)
===================

Enhancements
------------

-  Command line script allow users to search and add devices
   `#84 <https://github.com/pcdshub/happi/issues/84>`__
-  Base ``Container`` object now available with minimum amount of
   ``EntryInfo`` `#92 <https://github.com/pcdshub/happi/issues/92>`__
-  Allow Happi to load more devices from LCLS questionnaire
   `#94 <https://github.com/pcdshub/happi/issues/94>`__
-  New function ``list_choices`` added to ``happi.Client`` to allow user
   to know what beamlines, prefixes, names, etc. will return results.
-  Threaded ``load_devices`` with option to specify a callback when
   devices are ready
   `#67 <https://github.com/pcdshub/happi/issues/67>`__


v1.2.1 (2019-03-07)
===================

Bug Fixes
---------

-  The test suite now passes without the ``mongomock`` backend
   (`#89 <https://github.com/pcdshub/happi/issues/89>`__)
-  Ensure our file handles are properly closed in the JSON backend by
   using context managers
   (`#87 <https://github.com/pcdshub/happi/issues/87>`__)


v1.2.0 (2018-12-19)
===================

Enhancements
------------

-  ``Client`` now has a method ``load_device`` for searching the
   database for a ``Container`` and then loading the corresponding
   object based on ``device_class``, ``args`` and ``kwargs``. This is a
   shortcut to combine two previously existing features
   ``Client.find_device`` and ``happi.loader.from_container``

-  ``Client.from_config`` will create a ``Client`` object from a
   provided configuration file. You can either pass this file in
   explicitly, specify it via the the environment variable
   ``$HAPPI_CFG``, or it will be searched for in ``~config`` or wherever
   you specify your \`$XDG_CONFIG_HOME environment variable

-  Additional keywords were added to the base ``Device`` container;
   ``lightpath``, ``documentation`` and ``embedded_screen``,
   ``detailed_screen`` and ``engineering_screen``

-  There is now a base container for a ``Motor`` object.

Deprecations
------------

-  ``screen`` is longer a supported key. This was too generic and the
   three keys detailed above allow the user more specificity.

Fixes
-----

-  The ``JSONBackend`` no longer relies on ``fcntl`` a Linux only module
   of the Python standard library.


v1.1.2 (2018-08-30)
===================

Maintenance
-----------

-  In ``from_container``, the provided container is compared against the
   cached version of the device to find discrepancies. This means that
   modified container objects will always load a new Device.
   (`#62 <https://github.com/pcdshub/happi/issues/62>`__)
-  The QSBackend uses newer methods available in the psdm_qs_cli to
   determine the proposal from the experiment name. This is more robust
   against exotic experiment naming schemas than prior implementations
   (`#68 <https://github.com/pcdshub/happi/issues/68>`__)


v1.1.1 (2018-03-08)
===================

Enhancements
------------

-  The ``QSBackend`` guesses which a type of motor based on the
   ``prefix``. Currently this supports ``Newport``, ``IMS``, and
   ``PMC100`` motors. While there is not an explicit dependency, this
   will require ``pcdsdevices >= 0.5.0`` to load properly
   (`#51 <https://github.com/pcdshub/happi/issues/51>`__)

Bug Fixes
---------

-  Templating is more robust when dealing with types. This includes a
   fatal case where the default for an ``EntryInfo`` is ``None``
   (`#50 <https://github.com/pcdshub/happi/issues/50>`__)
-  A proper error message is returned if an entry in the table does not
   have the requisite information to load
   (`#53 <https://github.com/pcdshub/happi/issues/53>`__ )


v1.1.0 (2018-02-13)
===================

Ownership of this repository has been transferred to
https://github.com/pcdshub

Enhancements
------------

Happi now has a cache so the repeated requests to load the same device
do not spawn multiple objects.

Maintenance
-----------

-  Cleaner logging messages
-  ``QSBackend`` was expanded to accommodate different keyword arguments
   associated with different authentication methods.


v1.0.0 (2018-01-31)
===================

Enhancements
------------

-  ``happi`` now handles loading devices with the built-in ``EntryInfo``
   -> args, kwargs and device_class. Simply enter the proper information
   in these fields, either directly inputting information or using
   ``jinja2`` templating. The functions ``from_container`` and
   ``load_devices`` will then handle the necessary imports and
   initialize devices for you
-  Select which backend you want to use with the environment variable
   ``$HAPPI_BACKEND``
-  Backend to read from the PCDS Questionnaire
-  All containers work out of the box with ``pcdsdevices >= 0.3.0`` ##
   API
-  All backends are stored in the ``backends`` directory.
-  The default plugin is now considered to be ``JSONBackend``
-  The function formerly called ``load_device`` is now ``find_device``.

Build
-----

-  ``jinja2`` is now a dependency
-  ``psdm_qs_cli`` is now an optional dependency if you want to use the
   Questionnaire backend
-  ``pymongo`` is now an optional dependency if you do not want to use
   the MongoDB backend
-  Only tested against Python ``3.5.x`` and ``3.6.x``
-  Sent to the ``pcds-tag`` and ``pcds-dev`` Anaconda channels instead
   of the ``skywalker`` channels


v0.5.0 (2017-11-11)
===================

Enhancements
------------

-  ``happi`` now supports multiple backends. The required database
   operations are templated in the ``happi.backends.Backend`` The
   existing mongoDB support was kept as the default, but the an
   additional JSON backend was added. The choice of database type can be
   entered as an argument to the ``happi.Client``
-  Conda builds of ``happi`` are now available at ``skywalker-tag`` and
   ``skywalker-dev``

Bug Fixes
---------

-  Devices comparison now works properly. The listed prefix and names
   are compared.

API Changes
-----------

-  ``Mirror`` container has been changed to the more specific name
   ``OffsetMirror``

Deprecations
------------

-  ``happi`` will no longer support Python 2.7


v0.4.0 (2017-04-04)
===================

Bug Fixes
---------

-  Removed dependency on mongomock in conda-recipe
-  ``MockClient`` creates entire ``device_types`` container mapping

API Changes
-----------

-  Renamed alias -> name, and base -> prefix for Ophyd compatibility


v0.3.0 (2017-03-22)
===================

Enhancements
------------

-  Added Python 2.7 support
-  Added macros keyword for EDM support
-  Added CI tools for Travis, Codecov
-  Changed tests to use a ``mongomock.MockClient`` instead of an actual
   mongoDB instance
-  Device can now ``show_info`` and print a table output of all entered
   information

Bug Fixes
---------

-  ``active`` EntryInfo should default to True

API Changes
-----------

-  Moved the tests directory into the package to make it easily
   importable by other modules hoping to use a MockClient
-  Introduced explicit dependencies on ``six``, ``mongomock``, and
   ``prettytable``
