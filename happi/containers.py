import inspect
import logging
from typing import ClassVar, Dict, Generator, Optional, Tuple, Type

import entrypoints

from .device import Device
from .item import HappiItem, OphydItem

logger = logging.getLogger(__name__)

HAPPI_ENTRY_POINT_KEY = "happi.containers"


DEFAULT_REGISTRY = {'Device': Device,
                    'OphydItem': OphydItem,
                    'HappiItem': HappiItem}


class HappiRegistry:
    """
    Happi Container Registry singleton.

    This registry keeps a mapping of full happi container names to their
    respective :class:`HappiItem` subclasses.

    Entries in the registry are populated in the following order:

    1. From the ``happi.containers.DEFAULT_REGISTRY`` dictionary.  The names
       of the containers are assumed to already include any relevant qualifiers
       such as package names.  That is, the default ``"OphydItem"`` will be
       used as-is and retrieved from the registry by that name alone.
    2. Through Python package-defined entrypoints with the key
       ``happi.containers``.

       For example, consider a package named ``"mypackagename"`` that defines
       the happi container ``ContainerName`` inside of the Python module
       ``mypackagename.happi.containers_module.ContainerName``.
       The fully qualified name - as accessed through the happi client for each
       item in the database - may be customized in the entrypoint.

       Here, we want the container to be accessible by way of
       ``"desired_prefix.ContainerName"``.  The following would be how this
       entrypoint should be configured in ``setup.py``.

    .. code::

        setup(
            name="mypackagename",
            entry_points={
                "happi.containers": [
                    "desired_prefix=mypackagename.happi.containers_module",
                ],
            },
        )

    Containers may also be added manually to the registry by way of:

    .. code::

        import happi

        happi.containers.registry[item_name] = ContainerClass
    """
    #: Has __init__ been called on the registry?
    __initialized: bool
    #: The singleton instance of the HappiRegistry.
    __instance: ClassVar[Optional["HappiRegistry"]] = None
    #: Has the registry been initialized once?
    _loaded: bool
    #: Registry of happi container name to class
    _registry: Dict[str, Type[HappiItem]]
    #: Registry of happi container class to name
    _reverse_registry: Dict[Type[HappiItem], str]

    def __init__(self):
        if self.__initialized:
            # This guard ensures that `__init__` is not called twice on the
            # singleton.
            return
        self._registry = {}
        self._reverse_registry = {}
        self._loaded = False
        self.__initialized = True

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = object.__new__(HappiRegistry)
            cls.__instance.__initialized = False
        return cls.__instance

    def __getitem__(self, item: str) -> Optional[Type[HappiItem]]:
        if not self._loaded or item not in self._registry:
            self.load()
        return self._registry.get(item)

    def __setitem__(self, item: str, klass: Type[HappiItem]) -> None:
        self._safe_add(item, klass)

    def __contains__(self, item: str) -> bool:
        if not self._loaded or item not in self._registry:
            self.load()
        return item in self._registry

    def items(self) -> Generator[Tuple[str, Type[HappiItem]], None, None]:
        """All (item_name, item_class) entries in the registry."""
        if not self._loaded:
            self.load()
        yield from self._registry.items()

    def entry_for_class(self, klass: Type[HappiItem]) -> Optional[str]:
        """
        Get the happi item container name given its class.

        Parameters
        ----------
        klass : HappiItem class
            The class to get the name of.

        Returns
        -------
        str or None
            The full container name, if in the registry.
        """
        if not self._loaded or klass not in self._reverse_registry:
            self.load()
        return self._reverse_registry.get(klass)

    def _safe_add(self, entry_name: str, klass: Type[HappiItem]):
        """
        Add and entry into the registry and raise RuntimeError in case a
        duplicated entry is found.

        Parameters
        ----------
        entry_name : str
            The entrypoint identifier
        klass : class
            The class to add

        Raises
        ------
        RuntimeError
            Raises this exception if the entry is duplicated.
        """
        def make_entry_name():
            """
            Cut out the package name and replace with the entrypoint name so it
            can later be moved if needed.

            Parameters
            ----------
            klass : class

            Returns
            -------
            str
                The formatted name.
            """
            module = ".".join(klass.__module__.split(".")[1:])
            return ".".join([entry_name, module, klass.__name__])

        key = make_entry_name()

        class_in_registry = self._registry.get(key, None)
        if class_in_registry is klass:
            return
        if class_in_registry is not None:
            raise RuntimeError(f"Duplicated entry found for key: {key} "
                               f"and class: {klass} {class_in_registry}")
        if klass in self._reverse_registry:
            dup_key = self._reverse_registry.get(klass)
            raise RuntimeError(f"Duplicated entry found. Keys: {key} "
                               f"and {dup_key} point to same class: {klass}")

        self._registry[key] = klass
        self._reverse_registry[klass] = key

    def load(self) -> None:
        """
        Load entries into the Registry.
        """
        def valid_entry(klass):
            # Avoid happi internal classes due to imports
            return inspect.isclass(klass) and issubclass(klass, HappiItem) \
                   and not klass.__module__.startswith('happi.')

        for name, klass in DEFAULT_REGISTRY.items():
            if name not in self._registry:
                self._registry[name] = klass
                self._reverse_registry[klass] = name

        _entries = entrypoints.get_group_all(HAPPI_ENTRY_POINT_KEY)

        for entry in _entries:
            try:
                entry_name = entry.name
                obj = entry.load()
            except Exception:
                logger.exception("Failed to load happi.containers entry: %s",
                                 entry)
                continue
            if valid_entry(obj):
                self._safe_add(entry_name, obj)
            elif inspect.ismodule(obj):
                for _, var in inspect.getmembers(obj):
                    if valid_entry(var):
                        self._safe_add(entry_name, var)

        self._loaded = True


registry = HappiRegistry()
