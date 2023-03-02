301 fix_save_corrupt
####################

API Changes
-----------
- N/A

Features
--------
- N/A

Bugfixes
--------
- Fix an issue where an ill-timed interrupt of the json backend's
  ``store`` operation could truncate the data file. This also removes
  the implicit/optional dependency on ``fcntl``.

Maintenance
-----------
- Remove some lingering references to Travis CI

Contributors
------------
- zllentz
