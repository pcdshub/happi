import logging
import inspect
import entrypoints

from .item import HappiItem

logger = logging.getLogger(__name__)

_entries = entrypoints.get_group_all('happi.containers')

registry = set()

for entry in _entries:
    try:
        obj = entry.load()
    except Exception:
        logger.exception("Failed to load happi.containers entry: %s", entry)
        continue
    if inspect.isclass(obj) and HappiItem in obj.mro():
        registry.add(obj)
    elif inspect.ismodule(obj):
        registry.update(
            [var for _, var in inspect.getmembers(obj, inspect.isclass)
             if issubclass(var, HappiItem)
             # Avoid happi internal classes due to imports
             and not var.__module__.startswith('happi.')])

locals().update({c.__name__: c for c in registry})
