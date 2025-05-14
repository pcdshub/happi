Release History
###############


v2.6.2 (2025-05-13)
===================

Maintenance
-----------
- Fixes a variety of typing mistakes
- Fixes `happi transfer` to use the public `happi.containers.registry` API rather than internals
- Use `line_profiler` in pip dev_requirements instead of `line-profiler` to avoid confusion
- Splits happi pip package into subpackages (`gui`, `mongo`) for more precise dependency specification.
  The default dependency set has can be installed via `pip install happi[all]`, and includes
  the `gui` and `mongo` optional dependencies.
- Update test suite to handle no-arg case in cli for click>=8.2.0

Contributors
------------
- tangkong
- jwlodek


v2.6.0 (2024-12-19)
===================

Features
--------
- Updated `happi load` to support searching and loading in one user-friendly expression. The load function now gathers the results of each search term individually and loads the union of the results.

Maintenance
-----------
- Make running happi repair only saves an item if it actually got changed during the repair process
- Fixes issue in test suite, making tst_base_pim2 a loadable SimpleNamespacce
- Add example .cfg and some more instructions on using happi cli
- Make pre-release notes script default to just using vi if EDITOR env var is not set.
- Fix a few dead links in the docs, add to contributing doc to make 1st time dev instructions bit more clear

Contributors
------------
- janeliu-slac
- nstelter-slac
- tangkong



v2.5.0 (2023-12-19)
===================

Features
--------
- Adds more user-friendly qt search widget

Bugfixes
--------
- Fixes audit output table, preventing names from being dropped

Maintenance
-----------
- Adjusts cli audit output to work better for file redirects
- Fix conda recipe to use "run_constrained" not "run-constrained"

Contributors
------------
- tangkong
- klauer



v2.4.0 (2023-09-27)
===================

Features
--------
- Added ``happi.audit.audit()`` which can be used to programmatically audit
  happi items.

Bugfixes
--------
- Fixes bug where `happi transfer` was not filling default values properly
- Fixes conftest.trim_split_output, which was effectively a no-op.  Touches up affected tests
- Issue 302: Add functionality to happi 'repair' that ensures that the name and id fields of a device are the same.
- Removes an extra pcdsutils import from test_cli.py that is not properly caught by error handling

Maintenance
-----------
- Adds error handling for the temporary file created when initializing a json backend object.
- Changes format of temporary file name generation to contain only a unique hash.
- Tests modified to no longer assert stdout matches expected strings.  Rather the effect of the
  command being tested is verified independently.  The `assert_match_expected` helper is still
  used, but will now print mismatches instead of asserting them.
- Allows `happi update` to handle json-backend-type payloads
- Adds pcdsutils and pcdsdevices to environment requirements in conda recipe and dev requirements
- Removes pcdsutils and pcdsdevices from extra testing requirements in github workflow
- The ``happi audit`` CLI entrypoint has been modified to use
  ``happi.audit.audit()``.
- Updates mongo backend to handle authSource, require connection information (host, user, etc)
- Documents bson dependency.  Bson is vendored by pymongo, which instructs
  users to not install bson from pypi (`pymongo readme <https://github.com/mongodb/mongo-python-driver/tree/master#installation>`)

Contributors
------------
- klauer
- laura-king
- tangkong



v2.3.0 (2023-06-30)
===================

Features
--------
- CLI command ``happi config edit`` - open config file in ``$EDITOR``
- CLI command ``happi config init`` - create new config file with default options
- CLI command ``happi config show`` - show location & contents of config file
- Extend the config searching mechanism to check the platformdirs config directory.
  The happi config file path is taken from the ``HAPPI_CFG`` environment variable,
  but if the variable is not set then the following locations are searched in order
  for files named ``.happi.cfg`` or ``happi.cfg``:

  - The location specified by the ``XDG_CONFIG_HOME`` environment variable
  - ``~/.config``
  - (**new**) The location specified by ``platformdirs.user_config_dir("happi")``

Maintenance
-----------
- Add dependency on `platformdirs <https://pypi.org/project/platformdirs/>`_.
- Update build requirements to use pip-provided extras for documentation and test builds

Contributors
------------
- tangkong
- untzag



v2.2.0 (2023-05-08)
===================

Features
--------
- Adds a hook in ``happi.loader.from_container`` that runs the method
  ``post_happi_md`` on an instantiated object after the metadata
  container has been attached.
  This allows a clear method for objects to interact with
  happi metadata if desired.

Maintenance
-----------
- Makes ``HappiDeviceTreeView`` more tolerant of items with missing metadata keys.
  Items missing the key used to group the tree view will be organized
  into a catch-all "[KEY NOT FOUND]" group.

Contributors
------------
- tangkong



v2.1.0 (2023-04-03)
===================

Features
--------
- Adds ``happi repair`` command, for synchronizing backend database with fields expected by container.
  Adds a corresponding audit function.
- Adds audit functions that check the connection status of all signals in an
  ophyd device (``check_wait_connection``) and verify any fields requested by
  args/kwargs exist in the database (``check_args_kwargs_match``).
- Adds ``happi audit -d/--details`` option to print the source of a requested
  audit function.
- Adds the ``happi delete`` CLI tool for deleting entries from the happi database.

Bugfixes
--------
- Fix an issue where an ill-timed interrupt of the json backend's
  ``store`` operation could truncate the data file. This also removes
  the implicit/optional dependency on ``fcntl``.

Maintenance
-----------
- Migrates from Travis CI to GitHub Actions for continuous integration testing, and documentation deployment.
- Updates happi to use setuptools-scm, replacing versioneer, as its version-string management tool of choice.
- Syntax has been updated to Python 3.9+ via ``pyupgrade``.
- happi has migrated to modern ``pyproject.toml``, replacing ``setup.py``.
- Sphinx 6.0 now supported for documentation building.

Contributors
------------
- tangkong
- zllentz



v2.0.0 (2022-10-20)
===================

API Changes
-----------
- Removed deprecated ``happi.containers.Device`` container.
- Removed deprecated methods:
    * ``happi.Client.create_device``
    * ``happi.Client.add_device``
    * ``happi.Client.find_device``
    * ``happi.Client.all_devices``
    * ``happi.Client.remove_device``
    * ``happi.SearchResult.device``

Features
--------
- Added ``EntryInfo`` keyword argument ``include_default_as_kwarg``.  If set to ``False``,
  any keys that are included in an item's ``kwargs`` that match the default of their
  corresponding ``EntryInfo`` will be omitted from the keyword arguments passed to
  ``device_class`` when instantiating (loading) the item as in ``happi.loader.load_device`` or
  ``SearchResult.get()``.
  If the ``kwargs`` EntryInfo sets ``include_default_as_kwarg = True``,
  the setting on the corresponding ``EntryInfo`` will be used to decide
  whether or not to omit a keyword argument.
  If the ``kwargs`` EntryInfo sets ``include_default_as_kwarg = False``,
  the setting on corresponding ``EntryInfo`` will be ignored.
  The default value is True on all EntryInfo instances, retaining the original behavior.
- For happi load, fall back to Python REPL if IPython is not available.
- Added MultiBackend, which allows a happi Client to serve information
  from multiple databases simultaneously.  Updates config parsing logic
  to match.
- Added ``happi audit`` function for running checks on happi database items.
- Restored --json option for ``happi search``.

Bugfixes
--------
- Removed extraneous extraneous print in ``happi load``.
- Calculate a max width for shown tables based on the current terminal size
  to prevent bad line wrapping.

Maintenance
-----------
- Prevent ophyd / pyepics teardown during test suite.
- Improved error logging in happi CLI to be more consistent.

Contributors
------------
- JJL772
- klauer
- tangkong



v1.14.0 (2022-07-06)
====================

API Changes
-----------
- Added ``happi.Client.create_item`` and deprecated
  ``happi.Client.create_device``.
- Added ``happi.Client.add_item`` and deprecated ``happi.Client.add_device``.
- Added ``happi.Client.find_item`` and deprecated ``happi.Client.find_device``.
- Added ``happi.Client.all_items`` and deprecated ``happi.Client.all_devices``.
- Added ``happi.Client.remove_item`` and deprecated
  ``happi.Client.remove_device``.
- Deprecated ``happi.SearchResult.device`` and above deprecated items are now
  scheduled for removal in the next major happi release.
- Internal backend API ``all_devices`` has been changed to ``all_items``.
- Added ``happi.Client.retain_cache_context`` for clients that desire to
  control when reloading the database from a happi backend happens.
- Backend implementations may now optionally support a caching mechanism with
  ``clear_cache`` being called externally by the client when desirable.
- The happi container registry now supports adding new container classes
  manually by way of
  ``happi.containers.registry["ContainerName"] = ContainerClass``.

Features
--------
- Significant performance increase for JSON-backed happi clients.
- Makes ``SearchResult`` hashable
- Uses hashable ``SearchResult`` in happi search cli command
- JSON database paths may now be relative to the configuration file.
- Added ``happi benchmark`` for identifying which items are slow to load.
- Added ``happi profile`` for identifying why particular items are slow to load.

Bugfixes
--------
- Fix a rare race condition related to reading a json device database
  twice in a command line search command between database updates.
- Issue where happi Client would repeatedly (and unnecessarily) make database
  backend calls has been fixed.
- Allow int search values to match their float counterparts
- The happi container registry is loaded at first use and not on import.  This
  can result in increased performance where the happi database is not used.
  It also fixes a scenario in which a module that defines a happi container
  attempts to import certain classes from happi.

Maintenance
-----------
- Old terminology for ``HappiItem`` instances has been scrubbed and clarified
  in documentation.
- Test suite and documentation has been updated to reflect trajectory of
  deprecated methods and naming.
- Added relaxed flake8 configuration.
- Remove happi.device.Device from tests to avoid deprecation warnings
- Add type annotations to test suite
- Clean up fixture usage and separate ``three_valves`` fixture into ``three_valves`` and ``client_with_three_valves``
- add pre-release notes scripts
- More documentation about the happi container registry was added.
- Refactored CLI slightly to re-use searching logic.

Contributors
------------
- JJL772
- klauer
- tangkong
- zllentz


v1.13.0 (2022-06-03)
====================

Features
--------
- Added the ``enforce_doc`` argument to ``EntryInfo``. This lets us explain
  what the entry info represents and how it is meant to be filled out
  in more explicit words when it would be helpful to do.
- Added methods to client and cli entry points for changing the container
  of a happi item. This will walk the user through the process of
  switching to or between custom containers while making sure we adhere
  to the defined ``EntryInfo``. Check out ``happi transfer --help`` for
  command-line usage or ``Client.change_container`` for library usage.
- Added the option to pick between glob and regex searching from the CLI,
  rather than only allowing glob as in the past.
  Give ``happi search --regex`` a try and check out ``happi search --help``
  for more information.

Fixes
-----
- Fixed an issue where it was previously impossible to input dictionary
  and list fields using the CLI.
- Fixed handling of numeric values in ``happi search``.
- Fixed range searching logic for multiple range searches in one query.
- Fixed the ambiguity between a search returning no results (exit code 0)
  and a search being malformed (exit code 1).

Maintenance
-----------
- Refactored the CLI to use ``click`` instead of bare ``argparse``.
  This implementation is much cleaner and will lead to more advanced
  CLI features in the future.
- ``psdm_qs_cli`` and ``pymongo`` are no longer required dependencies of
  ``happi``. These have been reclassified into the ``run_constrained``
  portion of the conda recipe bundled in this repository and will also
  be adjusted on conda-forge.
- Improved usage and cleanup of temporary files when running the happi
  test suite.
- Restored the automatic documention uploads.
- Added/modified test cases to better cover search behavior.

Contributors
------------
- tangkong


v1.12.0 (2022-03-31)
====================

Features
--------
- Add optional per-device load timers to help identify slow-loading devices.

Fixes
-----
- Fixed an issue where missing keys could cause a find match to fail.
- Switch on-import fcntl warning to debug to reduce spam.

Contributors
------------
- klauer


v1.11.0 (2022-02-07)
====================

Features
--------
- Add ``--names`` flag to the ``happi search`` command. This causes the
  search to output only the names of the matching devices. This is useful
  for using the output of ``happi search`` inside another ``happi`` command,
  for example: ``happi load $(happi search "*" --names)``.

Contributors
------------
- unztag


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
-  ``OphydItem`` is now the preferred basic ``ophyd.Device``
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

-  Add an add command for cli, e.g. ``happi add`` to start an interactive
   device adder
-  Add an edit command for cli, e.g. ``happi edit im3l0 location=750``
   prefix=IM3L0:PPM
-  Change search command syntax to be simpler (more like edit)
-  Add a load command for cli, e.g. ``happi load im3l0 im1l1`` -> IPython
   session plus other changes made in dev to get it working
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
