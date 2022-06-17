import copy
import io
import re
from typing import Any, Dict, Type

import pytest

from ..client import Client
from ..errors import ContainerError
from ..item import EntryInfo, HappiItem, OphydItem


def test_get(item: OphydItem, item_info: Dict[str, Any]):
    assert item.name == item_info['name']


def test_init(item: OphydItem, item_info: Dict[str, Any]):
    assert item.prefix == item_info['prefix']
    assert item.name == item_info['name']


def test_list_enforce():
    # Generic HappiItem with a list enforce
    class MyDevice(HappiItem):
        list_attr = EntryInfo(enforce=['a', 'b', 'c'],
                              enforce_doc='list only')

    # Make sure we can set without error
    d = MyDevice()
    d.list_attr = 'b'
    assert d.list_attr == 'b'
    # Mase sure we can not set outside the list
    d = MyDevice()
    with pytest.raises(ValueError) as excinfo:
        d.list_attr = 'd'

    assert 'list only' in str(excinfo)


def test_regex_enforce():
    class MyDevice(HappiItem):
        re_attr = EntryInfo(enforce=re.compile(r'[A-Z]{2}$'),
                            enforce_doc='only 2 chars')

    d = MyDevice()
    d.re_attr = 'AB'

    d = MyDevice()
    with pytest.raises(ValueError) as excinfo:
        d.re_attr = 'ABC'

    assert 'only 2 chars' in str(excinfo)


@pytest.mark.parametrize('type_spec, value, expected',
                         [(int, 0, 0), (int, 1, 1), (int, 2.0, 2),
                          (str, 'hat', 'hat'), (str, 5, '5'),
                          (bool, True, True), (bool, 0, False),
                          (bool, 'true', True), (bool, 'NO', False)])
def test_type_enforce_ok(type_spec: Type, value: Any, expected: Any):
    entry = EntryInfo(enforce=type_spec)
    assert entry.enforce_value(value) == expected


@pytest.mark.parametrize('type_spec, value',
                         [(int, 'cats'),
                          (bool, '24'), (bool, 'catastrophe')])
def test_type_enforce_exceptions(type_spec: Type, value: Any):
    entry = EntryInfo(enforce=type_spec, enforce_doc='bad type')
    with pytest.raises(ValueError) as excinfo:
        entry.enforce_value(value)

    assert 'bad type' in str(excinfo)


def test_set(item: OphydItem):
    item.name = 'new_name'
    assert item.name == 'new_name'


def test_optional(item: OphydItem):
    assert item.documentation is None


def test_enforce(item: OphydItem):
    with pytest.raises(ValueError):
        item.name = 'Invalid!Name'


def test_container_error():
    with pytest.raises(ContainerError):
        class MyDevice(HappiItem):
            fault = EntryInfo(enforce=int,  default='not-int')


def test_mandatory_info(item: OphydItem):
    for info in ('prefix', 'name'):
        assert info in item.mandatory_info


def test_restricted_attr():
    with pytest.raises(TypeError):
        class MyDevice(HappiItem):
            info_names = EntryInfo()


def test_post(item: OphydItem, item_info: Dict[str, Any]):
    post = item.post()
    assert post['prefix'] == item_info['prefix']
    assert post['name'] == item_info['name']


def test_show_info(item: OphydItem, item_info: Dict[str, Any]):
    f = io.StringIO()
    item.show_info(handle=f)
    f.seek(0)
    out = f.read()
    item_info.pop('_id')
    assert '_id' not in out
    assert all([info in out for info in item_info.keys()])


def test_device_equivalance():
    a = HappiItem(name='abcd', prefix='b')
    b = HappiItem(name='abcd', prefix='b')
    c = HappiItem(name='cbcd', prefix='b')
    assert a == b
    assert not c == a


def test_dictify():
    a = HappiItem(name='abcd', prefix='b')
    assert dict(a) == a.post()


def test_device_copy():
    a = HappiItem(name='abcd', prefix='b')
    b = copy.copy(a)
    assert dict(a) == dict(b)


def test_device_deepcopy():
    a = HappiItem(name='abcd', prefix='abc', kwargs={'abc': 'def'})

    c = copy.deepcopy(a)
    assert a.kwargs == c.kwargs
    assert id(a.kwargs) != id(c.kwargs)


def test_add_and_save(valve: OphydItem, happi_client: Client):
    valve.active = True
    happi_client.add_item(valve)
    valve.active = False
    valve.save()

    assert not happi_client[valve.name].item.active


def test_add_and_save_deprecated(valve: OphydItem, happi_client: Client):
    valve.active = True
    happi_client.add_device(valve)  # intentionally raise DeprecationWarning
    valve.active = False
    valve.save()

    assert not happi_client[valve.name].item.active
