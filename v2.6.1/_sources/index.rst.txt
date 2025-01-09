HAPPI - Heuristic Access to Positions of Photon Instruments
===========================================================

Background
^^^^^^^^^^

Happi is a database-backed library that was originally created to hold
information about devices along SLAC's Linac Coherent Light Source beamline.
Though initially purpose-built, happi provides a framework for general indexing
of devices or *things* that correspond to Python objects.

Happi will help you create and index your objects, search through them, and
provide relevant metadata based on the object type.

Terminology Summary
^^^^^^^^^^^^^^^^^^^

* The happi client communicates with pre-configured database using an internal
  "backend".  Supported backends include JSON (with a file on disk) and MongoDB
  currently.
* A ``HappiItem`` container class describes metadata about a Python object and
  information on how to instantiate it.
* ``HappiItem`` may be customized for your own purposes through subclassing.
* Container classes have entries - marked by ``EntryInfo`` instances - that
  define the top-level keys and values of the item.
* The basic ``HappiItem`` has entries that tell happi how to import and
  instantiate a specific Python object.  The fields required for this are
  ``device_class``, ``args``, and ``kwargs``.  In short, the effect of loading
  this device would be to ``import device_class`` and instantiate it by way of
  ``device_class(*args, **kwargs)``.
* This resulting object is also referred to as a ``Device``, borrowing the name
  from the library ophyd.


 .. toctree::
   :maxdepth: 3
   :caption: Usage

   containers.rst
   client.rst
   cli.rst

.. toctree::
   :maxdepth: 3
   :caption: API Documentation

   api.rst

.. toctree::
   :maxdepth: 2
   :caption: Information

   releases.rst
   upcoming_changes.rst
