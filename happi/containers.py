import logging
import inspect
import entrypoints

from .item import HappiItem, OphydItem
from .device import Device

logger = logging.getLogger(__name__)

HAPPI_ENTRY_POINT_KEY = "happi.containers"


DEFAULT_REGISTRY = {'Device': Device,
                    'OphydItem': OphydItem,
                    'HappiItem': HappiItem}


class HappiRegistry:
    __instance = None

    def __init__(self):
        if self.__initialized:
            return
        self._registry = {}
        self._reverse_registry = {}
        self.load()
        self.__initialized = True

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = object.__new__(HappiRegistry)
            cls.__instance.__initialized = False
        return cls.__instance

    def __getitem__(self, item):
        return self._registry.get(item)

    def __contains__(self, item):
        return item in self._registry

    def items(self):
        yield from self._registry.items()

    def entry_for_class(self, klass):
        return self._reverse_registry.get(klass)

    def _safe_add(self, entry_name, klass):
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
        if key in self._registry:
            raise RuntimeError(f"Duplicated entry found for key: {key} "
                               f"and class: {klass}")
        if klass in self._reverse_registry:
            dup_key = self._reverse_registry.get(klass)
            raise RuntimeError(f"Duplicated entry found. Keys: {key} "
                               f"and {dup_key} point to same class: {klass}")

        self._registry[key] = klass
        self._reverse_registry[klass] = key

    def load(self):
        """
        Load entries into the Registry.
        """
        def valid_entry(klass):
            # Avoid happi internal classes due to imports
            return inspect.isclass(klass) and issubclass(klass, HappiItem) \
                   and not klass.__module__.startswith('happi.')

        self._registry = {k: v for k, v in DEFAULT_REGISTRY.items()}
        self._reverse_registry = {v: k for k, v in self._registry.items()}
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


registry = HappiRegistry()
