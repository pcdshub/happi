335 bug_xfer_default
####################

API Changes
-----------
- N/A

Features
--------
- N/A

Bugfixes
--------
- Fixes bug where `happi transfer` was not filling default values properly
- Fixes conftest.trim_split_output, which was effectively a no-op.  Touches up affected tests

Maintenance
-----------
- Tests modified to no longer assert stdout matches expected strings.  Rather the effect of the
  command being tested is verified independently.  The `assert_match_expected` helper is still
  used, but will now print mismatches instead of asserting them.

Contributors
------------
- tangkong
