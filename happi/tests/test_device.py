############
# Standard #
############
import re
import time

###############
# Third Party #
###############
import six
import pytest
import logging

##########
# Module #
##########
from happi        import Device
from happi.errors import ContainerError, EntryError
from happi.device import EntryInfo

def test_get(device, device_info):
    assert device.name == device_info['name']

def test_init(device, device_info):
    assert device.prefix     == device_info['prefix']
    assert device.name    == device_info['name']
    assert device.z        == device_info['z']
    assert device.beamline == device_info['beamline']

def test_list_enforce():
    class MyDevice(Device):
        list_attr = EntryInfo(enforce=['a','b','c'])

    d = MyDevice()
    d.list_attr = 'b'

    d = MyDevice()
    with pytest.raises(ValueError):
        d.list_attr = 'd'

def test_regex_enforce():
    class MyDevice(Device):
        re_attr = EntryInfo(enforce=re.compile(r'[A-Z]{2}$'))

    d = MyDevice()
    d.re_attr = 'AB'

    d = MyDevice()
    with pytest.raises(ValueError):
        d.re_attr = 'ABC'

def test_set(device):
    device.name = 'new_name'
    assert device.name == 'new_name'

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
    for info in ('prefix','name','beamline'):
        assert info in device.mandatory_info

def test_restricted_attr():
    with pytest.raises(TypeError):
        class MyDevice(Device):
            info_names = EntryInfo()

def test_post(device, device_info):
    post = device.post()
    assert post['prefix']     == device_info['prefix']
    assert post['name']    == device_info['name']
    assert post['z']        == device_info['z']
    assert post['beamline'] == device_info['beamline']

def test_show_info(device, device_info):
    f = six.StringIO()
    device.show_info(handle=f)
    f.seek(0)
    out = f.read()
    device_info.pop('_id')
    assert '_id' not in out
    assert all([info in out for info in device_info.keys()])

