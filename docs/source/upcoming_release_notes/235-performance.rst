235 client performance
######################

API Changes
-----------
- Added ``happi.Client.retain_cache_context`` for clients that desire to
  control when reloading the database from a happi backend happens.
- Backend implementations may now optionally support a caching mechanism with
  ``clear_cache`` being called externally by the client when desirable.

Features
--------
- Significant performance increase for JSON-backed happi clients.

Bugfixes
--------
- Issue where happi Client would repeatedly (and unnecessarily) make database
  backend calls has been fixed.

Maintenance
-----------
- Added relaxed flake8 configuration.

Contributors
------------
- klauer
