.. _containers:

Containers
**********

In order to regulate and template the information that gets entered into the
Happi database, we use the concept of containers. Containers serve two primary
roles:

* Identifying how to instantiate the object it represents (by way of class
  name, arguments, and keyword arguments).
* Storing pertinent and structured metadata for the given instance.

Containers are created by instantiating the :class:`.HappiItem` class or a
subclass of it. The metadata associated with the instance is broken up into
fields or "entries" of type :class:`.EntryInfo`. This allows a developer to
specify fields that are essential to every instance of a specific container
type.

EntryInfo
^^^^^^^^^

These fields are specified using an instance of :class:`.EntryInfo`. This class
provides several primary features:

* Mark a field as required (or optional)
* Add default values when unspecified
* Enforce - or validate - a certain format for the field

.. autoclass:: happi.EntryInfo
   :members:

HappiItem
^^^^^^^^^

In order to ensure that information is entered into the database in an
organized fashion, the client will only accept classes that inherit from
:class:`.HappiItem`. Each item will have the key information represented as
class attributes, available to be manipulated like any other regular property

Editing the information for a container is a simple as:

.. ipython:: python

    from happi import HappiItem

    item = HappiItem(name='my_device')

    item.name = 'new_name'


.. note::

    :class:`happi.Device` class is **deprecated** due to ambiguous name,
    conflicting with :class:`ophyd.Device`.
    :class:`happi.HappiItem` should be used instead.


Example Container
^^^^^^^^^^^^^^^^^

In order to show the flexibility of the :class:`.EntryInfo` class, we'll put
together a new example container. The class can be invoked in the same way you
would usually handle class inheritance, the only difference is that you specify
class attributes as EntryInfo objects:

.. ipython:: python

    import re
    from happi import HappiItem, EntryInfo

    class MyItem(HappiItem):
        """My new item, with a known model number."""
        model_no      = EntryInfo('Model Number of Item', optional=False)
        count         = EntryInfo('Count of Item', enforce=int, default=0)
        choices       = EntryInfo('Choice Info', enforce=['a','b','c'])
        no_whitespace = EntryInfo('Enforce no whitespace',
                                   enforce = re.compile(r'[\S]*$'),
                                   enforce_doc = 'This item cannot have whitespace')

By default, :class:`.EntryInfo` will create an optional init keyword argument with a
default of ``None`` with the same name as the class attribute. A quick way
to see how this information will be put into the the database is taking a look
at ``dict(item)``:

.. ipython:: python

    item = MyItem(name="my_item", model_no="QABC1234")
    dict(item)

As shown in the example above, using the EntryInfo keywords, you can put a
short docstring to give a better explanation of the field, and also enforce
that user enter a specific format of information.

While the user will always be able to enter ``None`` for the attribute, if a
real value is given it will be checked against the specified ``enforce``
keyword, raising ``ValueError`` if invalid. Here is a table for how the
:class:`.EntryInfo` check the type

========   ===========================
Enforce    Method of enforcement
========   ===========================
None       Any value will work
type       type(value)
list       list.index(value)
regex      regex.match(value) != None
function   function(value)
========   ===========================

If your enforce condition is complicated or obfuscated, you can add a
docstring using the ``enforce_doc`` keyword that explains the rule.
(This may be helpful for regex matches which are difficult for humans
to read)

Fields that are important to the item can be marked as mandatory with
``optional=False`` and should have no default value.

When entering information you will not necessarily see a difference between
optional and mandatory :class:`.EntryInfo`, however the database client will
reject the item if these fields do not have the requisite values set.

Loading your Object
^^^^^^^^^^^^^^^^^^^

A container's primary role is containing the information necessary to load the
Python representation of an object.

Internally, happi keeps track of all containers by way of its registry, the
:class:`~happi.containers.HappiRegistry`.

This information is stored as a ``device_class``, ``args`` and ``kwargs``. The
former stores a string that indicates the Python class of the item, the other
two indicate the information that is needed to instantiate it. With this
information both :func:`.from_container` and :func:`.load_device` are able to
handle importing modules and instantiating your object.

.. note::

    happi will attach the original metadata with a fixed attribute name ``.md``
    to your object.  You can use this to keep track of the container metadata
    used to instantiate your object.

    This can be disabled by setting ``attach_md`` to ``False`` in
    :func:`.from_container`.

Often, information contained in the ``args`` or ``kwargs`` will be duplicated
in other parts of the container. For instance, most ``ophyd`` objects will want
a ``name`` and ``prefix`` on initialization. Instead of repeating that
information you can just use a template and have the information automatically
populated for you by the container itself. For instance, in the aforementioned
example, ``container.args = ["{{name}}"]`` would substitute the value of
``container.name`` in as an argument. If the template contains the substituted
attribute alone, the type will also be converted.

.. ipython:: python

    from happi import from_container

    container = MyItem(name="my_item", model_no="QABC1234",
                       device_class='ophyd.sim.SynSignal',
                       kwargs={'name': '{{name}}'})
    obj = from_container(container, attach_md=True)
    obj


Integrating with your package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Happi provides some containers for your convenience, but intentionally does
not support all use cases or control systems in a monolithic fashion.

The suggested method for supporting your new package would be to make your
package have a dependency on happi, of course, and subclass :class:`.HappiItem`
to make a new container in your own package.

Then, add an
`entry point <https://packaging.python.org/specifications/entry-points/>`_
specified by the **happi.containers** keyword to your package's ``pyproject.toml``.
Example entry points can be found `here
<https://github.com/pcdshub/pcdsdevices/blob/master/pyproject.toml>`_.

:class:`~happi.containers.HappiRegistry` takes care of loading the entry points
and making them available throughout the library.


.. _convention_label:

Built-in Container Conventions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order for the database to be as easy to parse as possible we need to
establish conventions on how information is entered. Please read through this
before entering any information into the database.


HappiItem Entries
+++++++++++++++++

These are fields that are common to all Happi items.

    **name**

    This is simply a short name we can use to refer to the item.


    **device_class**

    This is the full class name, which lets happi know how to instantiate your
    item.

    The ``device_class`` name remains for backward-compatibility reasons.  Thinking
    of it as ``class_name`` or ``creator_callable`` would be more apt.

    .. note::

        This may also be the name of a factory function - happi only cares that
        it's callable.

    **args**

    Argument list to be passed on instantiation.  May contain templated macros such
    as ``{{name}}``.

    **kwargs**

    Keyword argument dictionary to be passed on instantiation.  May contain
    templated macros such as ``{{name}}``.

    **active**

    Is the object actively deployed?

    **documentation**

    A brief set of information about the object.


OphydItem entries
+++++++++++++++++

`ophyd <https://blueskyproject.io/ophyd>`_ has first-class support in happi - but
not much is required on top of the base HappiItem to support it.

    **prefix**

    This should be the prefix for all of the PVs contained within the device. It
    does not matter if this is an invalid record by itself.

LCLSItem entries
++++++++++++++++

This class is now part of `pcdsdevices
<https://github.com/pcdshub/pcdsdevices>`_.  It remains documented here as
PCDS is the original developer and primary user of happi as of the time of
writing. If you intend to use the same metadata that we do, please copy and
repurpose the ``LCLSItem`` class.

    **beamline**

    Beamline is required.  While it is expected to be one of the following, it
    is not enforced::

        CXI
        HXD
        ICL
        KFE
        LFE
        MEC
        MFX
        PBT
        RIX
        TMO
        TXI
        XCS
        XPP


    **z**

    Position of the device on the z-axis in the LCLS coordinates.

    **location_group**

    The group of this device in terms of its location.  This is primarily
    used for LUCID's grid.

    **functional_group**

    The group of this device in terms of its function.  This is primarily
    used for LUCID's grid.

    **stand**

    Acronym for stand, must be three alphanumeric characters like an LCLSI stand
    (e.g. DG3) or follow the LCLSII stand naming convention (e.g. L0S04).

    **lightpath**

    If the device should be included in the LCLS `Lightpath
    <https://github.com/pcdshub/lightpath>`_.

    **embedded_screen**

    Path to an embeddable PyDM control screen for this device.

    **detailed_screen**

    Path to a detailed PyDM control screen for this device.

    **engineering_screen**

    Path to a detailed engineering PyDM control screen for this device.
