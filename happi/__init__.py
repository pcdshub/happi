__all__ = ['Device', 'EntryInfo', 'Client', 'from_container',
           'load_devices', 'cache', 'HappiItem']
import logging
from .device import HappiItem, Device, EntryInfo
from .client import Client
from .loader import from_container, load_devices, cache
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

# Generic Logging Setup
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
