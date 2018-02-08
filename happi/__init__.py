import logging
from .device import Device, EntryInfo  # noqa
from .client import Client  # noqa
from .loader import load_devices, cache  # noqa
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

# Generic Logging Setup
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
