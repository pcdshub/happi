362 bug_dict_invalid
####################

API Breaks
----------
- Client search methods will now return an `InvalidResult` if a container (e.g.
  `HappiItem`) cannot be created. Previously, client search methods would raise a
  KeyError from the inciting exception. This KeyError will no longer be raised,
  and the inciting exception will be included as a data member in the
  InvalidResult object. This means downstream code that iterates over many happi
  entries doesn't need special error handling on big searches unless specifically
  the specific search item it needs is invalid.

  - Similarities (between SearchResult and InvalidResult):

    - You can still check metadata with key-based access (if it is present)
    - Basic operations such as iteration, length checks still work (and will skip any of the missing data members)

  - Differences:

    - There is no expectation that an InvalidResult will have well-formed data, some of it may be well-formed but data types are not guaranteed and some required data may be missing.
    - You can't meaningfully compare two InvalidResult objects with equality checks.
    - `InvalidResult` objects can't find the item that generated them via an item property (`SearchResult` supports this)
    - `InvalidResult` objects don't have a get function and cannot be used to instantiate real devices

Features
--------
- N/A

Bugfixes
--------
- N/A

Maintenance
-----------
- N/A

Contributors
------------
- tangkong
