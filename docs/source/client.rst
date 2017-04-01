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
While you are free to use the initialized object whereever you see fit, the client
has a hook to create new devices. The examples belows use a ``MockClient`` so
that the tutorial does not change actual database files.

.. ipython:: python

    import happi
    
    import happi.tests 
    client = happi.tests.MockClient(user='test',pw='test',db='test')

    device = client.create_device("Device", name='my_device',prefix='PV:BASE', beamline='XRT', z=345.5)
    
    device.save()

Alternatively, you can create the device separately and add the device
explicitly using :meth:`.Device.save`

.. ipython:: python

    device = happi.Device(name='my_device2',prefix='PV:BASE2', beamline='MFX', z=355.5)
   
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

.. ipython:: python
    
    client.search(type='Device')

    client.search(type='Device', as_dict=True)


There are also some more advance methods to search specific areas of the
beamline


.. ipython:: python
    
    client.search(type='Device', beamline='MFX')
   
    client.search(type='Device', start=314.4, end=348.6)

You can also explicitly load a single device. The advantage of this method is
you won't have to parse a list of returned devices. If nothing meets your given
criteria, an ``SearchError`` will be raised 

.. ipython:: python

   device =  client.load_device(prefix='PV:BASE2')

   print(device.prefix, device.name)

   try:
       client.load_device(name='non-existant')
   except happi.errors.SearchError as e:
       print(e)


Editing Device Information
^^^^^^^^^^^^^^^^^^^^^^^^^^
The workflow for editing a device looks very similar to the code within
:ref:`entry_code`, but instead of instantiating the device you use either
:meth:`.Client.load_device` or :meth:`.Client.search` to grab an existing device from
the dataprefix. When the device is retreived this way the class method
:meth:`.Device.save` is overwritten, simply call this when you are done editing
the Device information.

.. ipython:: python

    my_motor = client.load_device(prefix='PV:BASE')
    
    my_motor.z = 425.4
    
    my_motor.save()

.. note::

    Because the database uses the ``prefix`` key as a device's identification you
    can not edit this information in the same way. Instead you must explicitly
    remove the device and then use :meth:`.Client.add_device` to create a new
    entry. 
    
Finally, lets clean up our example objects by using
:meth:`.Client.remove_device` to clean them from the database

.. ipython:: python

    device_1 = client.load_device(name='my_device')
    
    device_2 = client.load_device(name='my_device2')

    for device in (device_1, device_2):
        client.remove_device(device)

Client API
^^^^^^^^^^
.. autoclass:: happi.Client
   :members:

