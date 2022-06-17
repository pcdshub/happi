.. _client_label:

Using the Client
****************
Users will interact with the database by using the :class:`happi.Client`, this
will handle the authentication, and methods for adding, editing and removing
items.

Happi is incredibly flexible, allowing us to put arbitrary key-value pair
information into the database. While this will make adding functionality easy in
the future, it also means that any rules on the structure of the data we allow
will need to be performed by the :class:`.Client` itself. To make this
intuitive, the Client deals primarily with :ref:`containers`, which are objects
that hold and specify these rules.

.. _entry_code:

Creating a New Entry
^^^^^^^^^^^^^^^^^^^^
A new item must be a subclass of the basic :class:`.HappiItem` container.
While you are free to use the initialized object wherever you see fit, the client
has a hook to create new items.

Before we can create our first client, we need to create a backend for our item
information to be stored.

.. ipython:: python
   :suppress:

   rm -f doc_test.json

.. ipython:: python

    from happi.backends.json_db import JSONBackend

    db = JSONBackend(path='doc_test.json', initialize=True)

If you are connecting to an existing database you can pass the information
directly into the :class:`.Client` itself at ``__init__``. See :ref:`db_choice`
about how to configure your default backend choice.

.. ipython:: python

    from happi import Client, HappiItem

    client = Client(path='doc_test.json')

    item = client.create_item(
        "HappiItem",
        name="my_device",
        device_class="types.SimpleNamespace",
        args=[],
        kwargs={},
        position=345.5,   # <- this is an extra field which happi allows
    )

    item

    item.save()

For this example, we have added an "extraneous" field to the item called
"position".  This is something that happi allows for.  If you wish to make
this a recognized field of an eforced type (e.g., don't allow the user to
make position a string value instead of a floating point value), please
see the documentation on making your own container class.

Alternatively, you can create the item separately and add it explicitly using
:meth:`.HappiItem.save`

.. ipython:: python

    item = HappiItem(
        name="my_device2",
        device_class="types.SimpleNamespace",
        position=355.5,   # <- this is an extra field which happi allows
    )

    item

    client.add_item(item)

The main advantage of the first method is that all of the container classes are
already managed by the client so they can be easily accessed with a string.
Keep in mind, that either way, all of the mandatory information needs to be
given to the item before it can be loaded into the database.

Searching the Database
^^^^^^^^^^^^^^^^^^^^^^
There are several ways to load information from the database
:meth:`.Client.find_item`, :meth:`.Client.search`, and dictionary-like access.

:meth:`.Client.find_item` is intended to only load one item at at a time. Both
accept criteria in the from of keyword-value pairs to find the item or items
you desire.

You can quickly query the client by item name and get a ``SearchResult`` that
can be used to introspect metadata or even instantiate the corresponding item
instance.

.. ipython:: python

    result = client["my_device"]

The client acts as a Python mapping, so you may inspect it as you would a
dictionary. For example:

.. ipython:: python

    # All of the item names:
    list(client.keys())
    # All of the database entries as SearchResults:
    list(client.values())
    # Pairs of (name, SearchResult):
    list(client.items())


You could, for example, grab the first key by name and access it using
``__getitem__``:

.. ipython:: python

    key_0 = list(client)[0]
    key_0
    client[key_0]

Or see how many entries are in the database:

.. ipython:: python

    len(client)

Here's a search that gets all the items of type generic ``HappiItem``:

.. ipython:: python

    results = client.search(type="HappiItem")


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

To search for items on a beamline such as 'MFX', one would use the following:


.. ipython:: python

    client.search(type='HappiItem', beamline='MFX')


Searching a range
"""""""""""""""""

In this example, we have added an extraneous field ``position`` that is not
present normally in the ``HappiItem`` container.

We can search a range of values with any arbitrary key using
:meth:`.Client.search_range`. For example:

.. ipython:: python

    client.search_range("position", start=314.4, end=348.6)

This would return all items between positions 314.4 and 348.6.

Any numeric key can be filtered in the same way, replacing ``'position'`` with
the key name.

Searching with regular expressions
""""""""""""""""""""""""""""""""""

Any key can use a regular expression for searching by using :meth:`.Client.search_regex`

.. ipython:: python

    client.search_regex(name='my_device[2345]')


Editing Item Information
^^^^^^^^^^^^^^^^^^^^^^^^
The workflow for editing an item looks very similar to the code within
:ref:`entry_code`, but instead of instantiating the item you use either
:meth:`.Client.find_item` or :meth:`.Client.search`. When the item is retrieved
this way the class method :meth:`.HappiItem.save` is overwritten, simply call
this when you are done editing.

.. ipython:: python

    my_motor = client.find_item(name="my_device")

    my_motor.position = 425.4

    my_motor.save()

.. note::

    Because the database uses the ``name`` key as an item's identification you
    can not edit this information in the same way. Instead you must explicitly
    remove the item and then use :meth:`.Client.add_item` to create a new
    entry.

Finally, lets clean up our example objects by using
:meth:`.Client.remove_item` to clean them from the database

.. ipython:: python

    item_1 = client.find_item(name='my_device')

    item_2 = client.find_item(name='my_device2')

    for item in (item_1, item_2):
        client.remove_item(item)

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

   rm -f doc_test.json
