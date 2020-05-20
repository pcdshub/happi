.. _device_label:

Containers
==========

A generic container is available for use that holds a few basic traits
pertinent to Ophyd devices. Largely this is available to provide a common
base that more specific devices will inherit from.

.. autoclass:: happi.OphydItem
    :members:

These inherit from the most generic information that can be included:

.. autoclass:: happi.HappiItem
    :members:

Extending Containers
--------------------

Happi allow users to extend the containers list via Python
`entry points <https://packaging.python.org/specifications/entry-points/>`_
specified by the **happi.containers** keyword. An example entry points can be
found `here <https://github.com/pcdshub/pcdsdevices/blob/master/setup.py>`_.

`HappiRegistry` takes care of loading the entry points and making them
available throughout the library.

Loading Containers
------------------

.. autofunction:: happi.from_container

.. autofunction:: happi.load_devices
