import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

#Devices
from .device     import Device
from .client     import Client


from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
