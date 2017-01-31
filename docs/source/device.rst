.. _device_label:

Device Containers
=================
In order to ensure that information is entered into the database in an
organized fashion, the client will only accept classes that inherit from
:class:`.Device`. Each device will have the key information represented as
class attributes, available to be manipulated like any other regular property    

Editing the information for a container is a simple as:

.. code::

    from happi import Device

    #Initialize
    device = Device(alias='my_device',...)

    #Set a new value for the alias
    device.alias = 'new_alias'

The :class:`.Device` class also supports extraneous data that may not have been
captured when the original container was created. You can either enter this as
a keyword, or enter it into the :attr:`.Device.extraneous` dictionary.

While you are free to play around with the device attributes, when loading the
object into the database you will need to make sure that all of the
:attr:`.Device.mandatory_information` has been entered, otherwise the client
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

Slits
+++++
.. autoclass:: happi.containers.Slits
   :members:

PIM
+++
.. autoclass:: happi.containers.PIM
   :members:

IPM
+++++
.. autoclass:: happi.containers.IPM
   :members:

Attenuator
++++++++++
.. autoclass:: happi.containers.Attenuator
   :members:

Gate Valve
++++++++++
.. autoclass:: happi.containers.GateValve
   :members:

Stopper
+++++++
.. autoclass:: happi.containers.Stopper
   :members:

Mirror
++++++
.. autoclass:: happi.containers.Mirror
   :members:

Pulse Picker
++++++++++++
.. autoclass:: happi.containers.PulsePicker
   :members:

LODCM
+++++
.. autoclass:: happi.containers.LODCM
   :members:
