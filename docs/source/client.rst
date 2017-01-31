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
has a conveinent hook to create new devices. Here are two example workflows
that have identical outcomes


.. code::

    import happi
    
    client = happi.Client()
    
    #First Method
    #############
    device = client.create_device("Device", alias='my_device',...)
    device.save()

    #Second Method
    ##############
    device = happi.Device(alias='my_device',...)
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
keyword-value pairs to find the device or device/s you desire.

Editing Device Information
^^^^^^^^^^^^^^^^^^^^^^^^^^
The workflow for editing a device looks very similar to the code within
:ref:`entry_code`, but instead of instantiating the device you use either
:meth:`.Client.load_device` or :meth:`.Client.search` to grab an existing device from
the database. When the device is retreived this way the class method
:meth:`.Device.save` is overwritten, simply call this when you are done editing
the Device information.

Client API
^^^^^^^^^^
.. autoclass:: happi.Client
   :members:

