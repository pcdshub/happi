.. _client_label:

Client 
******
Users will interact with the database by using the :class:`happi.Client`, this
will handle the authentication, and methods for adding, editing and removing
devices.

By default the MongoDB underneath happi is incredibly flexible, allowing us to
put arbitrary key-value pair information into the databse. While this will make
adding functionality easy in the future, it also means that any rules on the
structure of the data we allow will need to be performed by the
:class:`.happi.Client` itself. To make this intuitive, the client deals
primarily with objects we will call Device Containers, see :ref:`device_label`
in order to see more about how the devices are created. However the basic use
cases for the client can be demonstrated without much knowledge of how the
:class:`.Device` container works.

Authentication
^^^^^^^^^^^^^^
There are two accounts available for accessing the Happi database, one of which
is embedded in the source code itself that provides basic reading privilege,
the other which allows you to add and edit.

The :class:`.Client` also assumes a host and port name of the MongoDB instance.
All of this information can be entered upon intialization of the client using
keyword arguments. 

.. _entry_code:

Creating a New Entry
^^^^^^^^^^^^^^^^^^^^
A new device must be a subclass of the basic container :class:`.Device`.
While you are free to initialized the object whereever you see fit, the client
has a conveinent hook to create new devices.

.. code::

    import happi
    
    client = happi.Client(user='test',pw='test',db='test')

    device = client.create_device("Device", alias='my_device',base='PV:BASE', beamline='XRT', z=345.5)
    device.save()

Alternatively, you can create the device separately and add the device
explicitly using :meth:`.Client.save`

.. code::

    device = happi.Device(alias='my_device2',base='PV:BASE2', beamline='MFX', z=355.5)
    client.add_device(device)

The main advantage of the first method is that all of the container classes are
already stored in the :attr:`.Client.device_types` dictionary so they can be
easily accessed with a string. Keep in mind, that either way, all of the
mandatory information needs to be given to the device before it can be loaded
into the database. For more information on device creation see
:ref:`device_label`.
    
Searching the Database
^^^^^^^^^^^^^^^^^^^^^^
There are two ways to load information from the database
:meth:`.Client.load_device` and :meth:`.Client.search`. The former should only
be used to load one device at at a time. Both accept criteria in the from of
keyword-value pairs to find the device or device/s you desire. Here are some
example searches to demonstrate the power of the Happi Client

First, lets look for all the devices of type generic ``Device``, as first their
corresponding objects or as a dictionary

.. code::
    
    import happi
    
    client = happi.Client(user='test',pw='test',db='test')

    client.search(type='Device')

    client.search(type='Device', as_dict=True)

    client.search(type='Device', beamline='MFX')

There are also some more advance methods to search specific areas of the
beamline


.. code::
    
   client.search(type='Device', start=314.4, end=348.6)

You can also explicitly load a single device

.. code::

   device =  client.load_device(base='PV:BASE2')



Editing Device Information
^^^^^^^^^^^^^^^^^^^^^^^^^^
The workflow for editing a device looks very similar to the code within
:ref:`entry_code`, but instead of instantiating the device you use either
:meth:`.Client.load_device` or :meth:`.Client.search` to grab an existing device from
the database. When the device is retreived this way the class method
:meth:`.Device.save` is overwritten, simply call this when you are done editing
the Device information.

.. code::

    my_motor = client.load_device(base='PV:BASE')
    
    my_motor.z = 425.4
    
    my_motor.save()

.. note::

    Because the database uses the ``base`` key as a device's identification you
    can not edit this information in the same way. Instead you have to use
    :meth:`.Client.add_device` to create a new entry. 
    

Client API
^^^^^^^^^^
.. autoclass:: happi.Client
   :members:

