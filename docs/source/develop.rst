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

Example Class
^^^^^^^^^^^^^
In order to show the flexibility of the :class:`.EntryInfo` class, we'll put
together an example container. The class can be invoked in the same way you
would usually handle class inheritance, the only difference is that you specify
class attributes as EntryInfo objects:

.. code::

    from happi.device import Device, EntryInfo

    class MyDevice(Device):

        model_no = EntryInfo('Model Number of Device', optional=False)
        count    = EntryInfo('Count of Device', enforce=int, default=0)

By default, EntryInfo will create an optional keyword, whose default is
``None`` with the same name as the class attribute. You can always see how this
information will be put into the the database by looking at the output of the
:meth:`.Device.post` method. As shown in the example above, using the EntryInfo
keywords, you can put a short doc string to give a better explanation of the
field, and also enforce a type. It is important to note that if you change the
enforced type you should also change the default value. For instance in the
above example, if we had kept the default as ``None``,  ``int(None)`` would
have given a ``TypeError`` upon intialization. Finally, fields that are
important to the device can be marked as mandatory. These should have no
default value. The device methods will function fine without the mandatory
information, however the database client will reject the device if these fields
don't have values associated with them. 
