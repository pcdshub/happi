124 device_to_item
#################

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
- Removed previously-deprecated ``happi.Device`` container.

Features
--------
- N/A

Bugfixes
--------
- N/A

Maintenance
-----------
- Old terminology for ``HappiItem`` instances has been scrubbed and clarified
  in documentation.

Contributors
------------
- klauer
