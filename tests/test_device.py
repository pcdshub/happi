import logging
import pytest

from happi        import Device
from happi.errors import ContainerError, EntryError
from happi.device import EntryInfo

logger = logging.getLogger(__name__)


def test_get(device, device_info):
    assert device.alias == device_info['alias']

def test_init(device, device_info):
    assert device.base     == device_info['base']
    assert device.alias    == device_info['alias']
    assert device.z        == device_info['z']
    assert device.beamline == device_info['beamline']

def test_set(device):
    device.alias = 'new_alias'
    assert device.alias == 'new_alias'

def test_optional(device):
    assert device.parent == None

def test_enforce(device):
    with pytest.raises(ValueError):
        device.z = 'Non-Float'

def test_container_error():
    with pytest.raises(ContainerError):
        class MyDevice(Device):
            fault = EntryInfo(enforce=int, default='not-int')

def test_mandatory_info(device):
    for info in ('base','alias','z','beamline'):
        assert info in device.mandatory_info

def test_restricted_attr():
    with pytest.raises(TypeError):
        class MyDevice(Device):
            info_names = EntryInfo()


def test_post(device, device_info):
    post = device.post()
    assert post['base']     == device_info['base']
    assert post['alias']    == device_info['alias']
    assert post['z']        == device_info['z']
    assert post['beamline'] == device_info['beamline']

