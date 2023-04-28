308 enh_post_md-hook
###################

API Changes
-----------
- N/A

Features
--------
- Adds a hook in happi.loader.from_container that runs the method ``post_happi_md`` on an instantiated object after the metadata container has been attached.  This allows a clear method for objects to interact with happi metadata if desired.

Bugfixes
--------
- N/A

Maintenance
-----------
- N/A

Contributors
------------
- tangkong
