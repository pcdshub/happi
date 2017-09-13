.. _device_label:

Device Containers
=================
In order to ensure that information is entered into the database in an
organized fashion, the client will only accept classes that inherit from
:class:`.Device`. Each device will have the key information represented as
class attributes, available to be manipulated like any other regular property    

Editing the information for a container is a simple as:

.. ipython:: python

    from happi import Device

    device = Device(name='my_device')

    device.name = 'new_name'

The :class:`.Device` class also supports extraneous data that may not have been
captured when the original container was created. You can either enter this as
a keyword, or enter it into the :attr:`.Device.extraneous` dictionary.

While you are free to play around with the device attributes, when loading the
object into the database you will need to make sure that all of the
:attr:`.Device.mandatory_info` has been entered, otherwise the client
will reject the device. 

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

Gate Valve
++++++++++
.. autoclass:: happi.containers.GateValve

Slits
+++++
.. autoclass:: happi.containers.Slits

PIM
+++
.. autoclass:: happi.containers.PIM

IPM
+++++
.. autoclass:: happi.containers.IPM

Attenuator
++++++++++
.. autoclass:: happi.containers.Attenuator

Stopper
+++++++
.. autoclass:: happi.containers.Stopper

Mirror
++++++
.. autoclass:: happi.containers.OffsetMirror

PulsePicker
++++++++++++
.. autoclass:: happi.containers.PulsePicker

LODCM
+++++
.. autoclass:: happi.containers.LODCM

MovableStand
+++++++++++++
.. autoclass:: happi.containers.MovableStand
