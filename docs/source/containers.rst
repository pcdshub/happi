.. _device_label:

Device Containers
=================
Device
------
A generic device container is available for use that holds a few basic traits
pertinent to all LCLS devices. Largely this is available to provide a common
base that more specific devices will inherit from.

.. autoclass:: happi.Device
   :members:

Containers
----------
Each of the containers below share the attributes and entries of the generic
Device container. This section documents the entries when they either do not
exist in the generic device or require further clarification on a case-by-case
basis.

.. autosummary::
   :toctree: generated

   happi.containers.GateValve
   happi.containers.Slits
   happi.containers.PIM
   happi.containers.PIM
   happi.containers.IPM
   happi.containers.Attenuator
   happi.containers.Stopper
   happi.containers.OffsetMirror
   happi.containers.PulsePicker
   happi.containers.LODCM
   happi.containers.MovableStand
