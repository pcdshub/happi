#############
Release Notes
#############

v1.1.2 (2018-08-30)
===================

**Maintenance**

- In :meth:`.from_container`, the provided container is compared against
  the cached version of the device to find discrepancies. This means that
  modified container objects will always load a new Device. (#62)

- The ``QSBackend`` uses newer methods available in the ``psdm_qs_cli`` to
  determine the proposal from the experiment name. This is more robust against
  exotic experiment naming schemas than prior implementations (#68)

v1.1.1 (2018-03-08)
===================

**Enhancements**

- The ``QSBackend`` guesses which a type of motor based on the ``prefix``.
  Currently this supports ``Newport``, ``IMS``, and ``PMC100`` motors. While there is
  not an explicit dependency, this will require ``pcdsdevices >= 0.5.0`` to load
  properly (#51)

**Bug Fixes**

- Templating is more robust when dealing with types. This includes a fatal case
  where the default for an ``EntryInfo`` is ``None`` (#50)

- A proper error message is returned if an entry in the table does not have the
  requisite information to load (#53 )

v1.1.0 (2018-02-13)
===================
Ownership of this repository has been transferred to
`<https://github.com/pcdshub>`_

**Enhancements**

- Happi now has a cache so the repeated requests to load the same device do
  not spawn multiple objects.

**Maintenance**

- Cleaner logging messages

  - ``QSBackend`` was expanded to accommodate different keyword arguments
     associated with different authentication methods.
