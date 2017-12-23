Creating New Device Types
*************************
Container objects are built using both the base :class:`.Device` class as well
as instances of the :class:`.EntryInfo`.

Entry Info
^^^^^^^^^^
In order to regulate and template the information that gets entered into the
Happi database, we use the concept of device containers. This allows a
developer to specify fields that are inherit to every device of a specific
type, in addition by specifying these keys using the :class:`.EntryInfo`
object, you have even greater control by declaring optional vs. mandatory,
default options when a user does not enter the value, and enforce specific
types. 

.. autoclass:: happi.device.EntryInfo
   :members:

Using a Device
^^^^^^^^^^^^^^
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

Example Class
^^^^^^^^^^^^^
In order to show the flexibility of the :class:`.EntryInfo` class, we'll put
together an example container. The class can be invoked in the same way you
would usually handle class inheritance, the only difference is that you specify
class attributes as EntryInfo objects:

.. code::

    import re
    from happi.device import Device, EntryInfo

    class MyDevice(Device):

        model_no      = EntryInfo('Model Number of Device', optional=False)
        count         = EntryInfo('Count of Device', enforce=int, default=0)
        choices       = EntryInfo('Choice Info', enforce=['a','b','c'])
        no_whitespace = EntryInfo('Enforce no whitespace',
                                   enforce = re.compile(r'[\S]*$')

By default, EntryInfo will create an optional keyword, whose default is
``None`` with the same name as the class attribute. You can always see how this
information will be put into the the database by looking at the output of the
:meth:`.Device.post` method. As shown in the example above, using the EntryInfo
keywords, you can put a short doc string to give a better explanation of the
field, and also enforce that user enter a specific format of information.

While the user will always be able to enter ``None`` for the attribute, if a
real value is given it will be checked against the specified ``enforce``
keyword, raising ``ValueError`` if invalid. Here is a table for how the
:class:`.EntryInfo` check the type

=======   ===========================
Enforce   Method of enforcement
=======   ===========================
None      Any value will work
type      type(value)
list      list.index(value)
regex     regex.match(value) != None
=======   ===========================

Finally, fields that are important to the device can be marked as mandatory.
These should have no default value. When entering information you will not
neccesarily see a difference in between optional and mandatory
:class:`.EntryInfo`, however the database client will reject the device if
these fields don't have values associated with them. 
