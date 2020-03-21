import logging
import inspect
import entrypoints

from .item import HappiItem

logger = logging.getLogger(__name__)

_entries = entrypoints.get_group_all('happi.containers')

registry = {}

for entry in _entries:
    try:
        name = entry.name
        obj = entry.load()
    except Exception:
        logger.exception("Failed to load happi.containers entry: %s", entry)
        continue
    if inspect.isclass(obj) and issubclass(obj, HappiItem):
        registry[f"{name}.{obj.__name__}"] = obj
    elif inspect.ismodule(obj):
        registry.update({f"{name}.{var.__name__}": var
                         for _, var in inspect.getmembers(obj, inspect.isclass)
                         if issubclass(var, HappiItem)
                         # Avoid happi internal classes due to imports
                         and not var.__module__.startswith('happi.')})
