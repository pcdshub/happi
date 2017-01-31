import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

#Devices
from .device     import Device
from .client     import Client

