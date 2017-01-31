import logging
import pytest

from happi        import Device, EntryError
from happi.device import EntryInfo

#For Doc Testing
from conftest import ExampleDevice

logger = logging.getLogger(__name__)


def test_doc():
    assert ExampleDevice.doc.__doc__ == 'docstring'

def test_get(device):
    assert device.alias == 'alias'

def test_set(device):
    device.alias = 'new_alias'
    assert device.alias == 'new_alias'

def test_optional(device):
    assert device.optional == None

def test_default(device):
    assert device.default == True

def test_enforce(device):
    with pytest.raises(ValueError):
        device.enforced = 'non-integer'

def test_post(device):
    post = device.post()
    assert post['alias']    == 'alias'
    assert post['z']        ==  400
    assert post['base']     == 'BASE:PV'
    assert post['beamline'] == 'LCLS'
