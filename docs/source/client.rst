.. _client_label:

Using the Client
****************
Users will interact with the database by using the :class:`happi.Client`, this
will handle the authentication, and methods for adding, editing and removing
devices.

Happi is incredibly flexible, allowing us to put arbitrary key-value pair
information into the database. While this will make adding functionality easy in
the future, it also means that any rules on the structure of the data we allow
will need to be performed by the :class:`.Client` itself. To make this
intuitive, the Client deals primarily with :ref:`containers`, which are objects
that hold and specify these rules.

.. _entry_code:

Creating a New Entry
^^^^^^^^^^^^^^^^^^^^
A new device must be a subclass of the basic container :class:`.Device`.
While you are free to use the initialized object wherever you see fit, the client
has a hook to create new devices.

Before we can create our first client, we need to create a backend for our device
information to be stored.

.. ipython:: python

    from happi.backends.json_db import JSONBackend

    db = JSONBackend(path='doc_test.json', initialize=True)

If you are connecting to an existing database you can pass the information
directly into the ``Client`` itself at `__init__``. See :ref:`db_choice`
about how to configure your default backend choice

.. ipython:: python

    from happi import Client, Device

    client = Client(path='doc_test.json')

    device = client.create_device("Device", name='my_device',prefix='PV:BASE', beamline='XRT', z=345.5, location_group="Loc1", functional_group="Func1", device_class='types.SimpleNamespace', args=[])

    device.save()

Alternatively, you can create the device separately and add the device
explicitly using :meth:`.Device.save`

.. ipython:: python

    device = Device(name='my_device2',prefix='PV:BASE2', beamline='MFX', z=355.5, location_group="Loc2", functional_group="Func2")

    client.add_device(device)

The main advantage of the first method is that all of the container classes are
already stored in the :attr:`.Client.device_types` dictionary so they can be
easily accessed with a string. Keep in mind, that either way, all of the
mandatory information needs to be given to the device before it can be loaded
into the database.

Searching the Database
^^^^^^^^^^^^^^^^^^^^^^
There are two ways to load information from the database
:meth:`.Client.find_device` and :meth:`.Client.search`. The former should only
be used to load one device at at a time. Both accept criteria in the from of
keyword-value pairs to find the device or device/s you desire. Here are some
example searches to demonstrate the power of the Happi Client.

First, lets look for all the devices of type generic ``Device``:

.. ipython:: python

    results = client.search(type='Device')


This returns a list of zero or more :class:`SearchResult` instances, which can
be used to introspect metadata or even instantiate the corresponding device
instance.


Working with the SearchResult
"""""""""""""""""""""""""""""

Representing a single search result from ``Client.search`` and its variants, a
:class:`SearchResult` can be used in multiple ways.

This result can be keyed for metadata as in:

.. ipython:: python

    result = results[0]
    result['name']


The :class:`HappiItem` can be readily retrieved:


.. ipython:: python

    result.item
    type(result.item)


Or the object may be instantiated:

.. ipython:: python

    result.get()


See that :meth:`.SearchResult.get` returns the class we expect, based on the
`device_class`.

.. ipython:: python

    result['device_class']
    type(result.get())

There are also some more advance methods to search specific areas of the
beamline or use programmer-friendly regular expressions, described in the
upcoming sections.


Searching for items on a beamline
"""""""""""""""""""""""""""""""""

To search for items on a beamline such as `MFX`, one would use the following:


.. ipython:: python

    client.search(type='Device', beamline='MFX')


Searching a range
"""""""""""""""""

Searching a Z-range on the beamline, or a range with any arbitrary key is also
easy by way of :meth:`.Client.search_range`. For example:

.. ipython:: python

    client.search_range('z', start=314.4, end=348.6, type='Device')

This would return all devices between Z=314.4 and Z=348.6.

Any numeric key can be filtered in the same way, replacing `'z'` with the key
name.

Searching with regular expressions
""""""""""""""""""""""""""""""""""

Any key can use a regular expression for searching by using :meth:`.Client.search_regex`

.. ipython:: python

    client.search_regex(name='my_device[2345]')


Editing Device Information
^^^^^^^^^^^^^^^^^^^^^^^^^^
The workflow for editing a device looks very similar to the code within
:ref:`entry_code`, but instead of instantiating the device you use either
:meth:`.Client.find_device` or :meth:`.Client.search` to grab an existing device from
the data prefix. When the device is retrieved this way the class method
:meth:`.Device.save` is overwritten, simply call this when you are done editing
the Device information.

.. ipython:: python

    my_motor = client.find_device(prefix='PV:BASE')

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

    device_1 = client.find_device(name='my_device')

    device_2 = client.find_device(name='my_device2')

    for device in (device_1, device_2):
        client.remove_device(device)

.. _db_choice:

Selecting a Backend
^^^^^^^^^^^^^^^^^^^
Happi supports both JSON and MongoDB backends. You can always import your
chosen backend directly, but in order to save time you can create an
environment variable ``HAPPI_BACKEND`` and set this to ``"mongodb"``. This well
tell the library to assume you want to use the :class:`.MongoBackend`.
Otherwise, the library uses the :class:`.JSONBackend`.

..
   Remove test file created by initializing a JSONBackend above

.. ipython:: python
   :suppress:

   rm doc_test.json
