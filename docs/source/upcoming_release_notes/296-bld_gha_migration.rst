296 bld_gha_migration
#################

API Changes
-----------
- N/A

Features
--------
- N/A

Bugfixes
--------
- N/A

Maintenance
-----------
- Migrates from travis ci to github actions for continuous integration testing, and documentation deployment
- Updates happi to use setuptools-scm, replacing versioneer, as its version-string management tool of choice
- Syntax has been updated to Python 3.9+ via ``pyupgrade``
- happi has migrated to modern ``pyproject.toml``, replacing ``setup.py``
- Sphinx 6.0 now supported for documentation building

Contributors
------------
- tangkong
