295 enh_audit_fns
#################

API Changes
-----------
- N/A

Features
--------
- adds audit functions that check the connection status of all signals in an
  ophyd device (``check_wait_connection``) and verify any fields requested by
  args/kwargs exist in the database (``check_args_kwargs_match``).
- adds ``happi audit -d/--details`` option to print the source of a requested
  audit function

Bugfixes
--------
- N/A

Maintenance
-----------
- N/A

Contributors
------------
- tangkong
