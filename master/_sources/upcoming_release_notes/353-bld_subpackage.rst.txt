353 bld_subpackage
##################

API Breaks
----------
- N/A

Features
--------
- N/A

Bugfixes
--------
- N/A

Maintenance
-----------
- Splits happi pip package into subpackages (`gui`, `mongo`) for more precise dependency specification.
  The default dependency set has can be installed via `pip install happi[all]`, and includes
  the `gui` and `mongo` optional dependencies.

Contributors
------------
- tangkong
