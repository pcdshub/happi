import logging


from .device import Device, EntryInfo
from .client import Client

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
