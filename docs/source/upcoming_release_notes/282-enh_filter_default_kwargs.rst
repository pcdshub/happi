282 enh_filter_default_kwargs
#############################

API Changes
-----------
- N/A

Features
--------
- adds flag ``include_default_as_kwarg``.  If False on a kwargs EntryInfo,
  any values that match the default on the corresponding EntryInfo will be
  omitted from the kwarg dictionary.
  The default value is True, retaining the original behavior.

Bugfixes
--------
- N/A

Maintenance
-----------
- N/A

Contributors
------------
- tangkong
