import logging
import pytest

from happi        import Device, EntryError
from happi.device import EntryInfo

logger = logging.getLogger(__name__)

class TestDevice(Device):
    optional  = EntryInfo()
    default   = EntryInfo(default=True)
    enforced  = EntryInfo(enforce=int,default=1)
    doc       = EntryInfo('docstring')

def test_doc():
    assert ExampleDevice.doc.__doc__ == 'docstring'

@pytest.fixture(scope='function')
def device():
    t = ExampleDevice(alias='alias', z='400',
                   base='BASE:PV',beamline='LCLS')
    print('device',t)
    return t

def test_get(device):
    assert device.alias == 'alias'

def test_set(device):
    device.alias = 'new_alias'
    assert device.alias == 'new_alias'

def test_optional(device):
    device.optional == None

def test_default(device):
    assert device.default == True

def test_enforce(device):
    with pytest.raises(ValueError):
        device.enforced = 'non-integer'

def test_post(device):
    post = device.post()
    assert post['type'] == 'TestDevice'
