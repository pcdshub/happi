import copy
import io
import re

import pytest

from happi import Device
from happi.errors import ContainerError
from happi.device import EntryInfo


def test_get(device, device_info):
    assert device.name == device_info['name']


def test_init(device, device_info):
    assert device.prefix == device_info['prefix']
    assert device.name == device_info['name']


def test_list_enforce():
    # Generic device with a list enforce
    class MyDevice(Device):
        list_attr = EntryInfo(enforce=['a', 'b', 'c'])

    # Make sure we can set without error
    d = MyDevice()
    d.list_attr = 'b'
    assert d.list_attr == 'b'
    # Mase sure we can not set outside the list
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
    assert device.documentation is None


def test_enforce(device):
    with pytest.raises(ValueError):
        device.name = 'Invalid!Name'


def test_container_error():
    with pytest.raises(ContainerError):
        class MyDevice(Device):
            fault = EntryInfo(enforce=int,  default='not-int')


def test_mandatory_info(device):
    for info in ('prefix', 'name'):
        assert info in device.mandatory_info


def test_restricted_attr():
    with pytest.raises(TypeError):
        class MyDevice(Device):
            info_names = EntryInfo()


def test_post(device, device_info):
    post = device.post()
    assert post['prefix'] == device_info['prefix']
    assert post['name'] == device_info['name']


def test_show_info(device, device_info):
    f = io.StringIO()
    device.show_info(handle=f)
    f.seek(0)
    out = f.read()
    device_info.pop('_id')
    assert '_id' not in out
    assert all([info in out for info in device_info.keys()])


def test_device_equivalance():
    a = Device(name='abcd', prefix='b')
    b = Device(name='abcd', prefix='b')
    c = Device(name='cbcd', prefix='b')
    assert a == b
    assert not c == a


def test_dictify():
    a = Device(name='abcd', prefix='b')
    assert dict(a) == a.post()


def test_device_copy():
    a = Device(name='abcd', prefix='b')
    b = copy.copy(a)
    assert dict(a) == dict(b)


def test_device_deepcopy():
    a = Device(name='abcd', prefix='abc', kwargs={'abc': 'def'})

    c = copy.deepcopy(a)
    assert a.kwargs == c.kwargs
    assert id(a.kwargs) != id(c.kwargs)


def test_add_and_save(three_valves, device, happi_client):
    device.active = True
    happi_client.add_device(device)
    device.active = False
    device.save()

    assert not happi_client[device.name].device.active
