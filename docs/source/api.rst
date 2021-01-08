Happi API
*********

Client
^^^^^^

.. autoclass:: happi.Client
   :members:


.. autoclass:: happi.SearchResult
   :members:


Backends
^^^^^^^^

.. autoclass:: happi.backends.core._Backend
   :members:

.. autosummary::
   :toctree: generated

   happi.backends.mongo_db.MongoBackend
   happi.backends.json_db.JSONBackend
   happi.backends.qs_db.QSBackend


Containers
^^^^^^^^^^^

Built-ins
+++++++++

.. autoclass:: happi.HappiItem
    :members:

.. autoclass:: happi.OphydItem
    :members:

Loading
+++++++

.. autofunction:: happi.from_container

.. autofunction:: happi.load_devices

Registry
++++++++

.. autoclass:: happi.containers.HappiRegistry
