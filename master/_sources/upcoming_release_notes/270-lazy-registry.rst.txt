270 lazy registry
#################

API Changes
-----------
- The happi container registry now supports adding new container classes
  manually by way of
  ``happi.containers.registry["ContainerName"] = ContainerClass``.

Features
--------
- N/A

Bugfixes
--------
- The happi container registry is loaded at first use and not on import.  This
  can result in increased performance where the happi database is not used.
  It also fixes a scenario in which a module that defines a happi container
  attempts to import certain classes from happi.

Maintenance
-----------
- More documentation about the happi container registry was added.

Contributors
------------
- klauer
