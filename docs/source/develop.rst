Creating New Device Types
*************************


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
