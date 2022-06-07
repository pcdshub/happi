import logging
import os
import re
import tempfile
import types
from typing import Any, Dict

import pytest

from happi import Client, HappiItem, OphydItem
from happi.backends.json_db import JSONBackend
from happi.errors import DuplicateError, EntryError, SearchError, TransferError

logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def xdg_config_home(tmp_path):
    config_home = tmp_path / 'xdg_config_home'
    config_home.mkdir()
    return config_home


@pytest.fixture(scope='function')
def happi_cfg(xdg_config_home):
    # Store current happi config
    xdg_cfg = os.environ.get("XDG_CONFIG_HOME", '')
    happi_cfg = os.environ.get("HAPPI_CFG", '')

    # Setup environment variables
    os.environ['XDG_CONFIG_HOME'] = str(xdg_config_home)
    os.environ['HAPPI_CFG'] = ''

    # Write file
    happi_cfg = xdg_config_home / 'happi.cfg'
    happi_cfg.write_text("""\
[DEFAULT]
backend=json
path=db.json
""")
    yield str(happi_cfg)
    # Restore environment variables
    os.environ["HAPPI_CFG"] = str(happi_cfg)
    os.environ["XDG_CONFIG_HOME"] = xdg_cfg


def test_find_document(happi_client: Client, device_info: Dict[str, Any]):
    doc = happi_client.find_document(**device_info)
    assert doc.pop('prefix') == device_info['prefix']
    assert doc.pop('name') == device_info['name']
    # Remove id and check
    prefix = device_info.pop('prefix')
    doc = happi_client.find_document(**device_info)

    assert doc.pop('prefix') == prefix
    assert doc.pop('name') == device_info['name']
    # Not available
    with pytest.raises(SearchError):
        doc = happi_client.find_document(prefix='Does not Exist')


def test_create_device(happi_client: Client, device_info: Dict[str, Any]):
    device = happi_client.create_device(OphydItem, **device_info)
    assert device.prefix == device_info['prefix']
    assert device.name == device_info['name']
    # Invalid Entry
    with pytest.raises(TypeError):
        happi_client.create_device(int)


def test_all_devices(happi_client: Client, device: OphydItem):
    assert happi_client.all_items == [device]


def test_add_device(happi_client: Client, valve: OphydItem):
    happi_client.add_device(valve)
    # No duplicates
    with pytest.raises(DuplicateError):
        happi_client.add_device(valve)
    # No incompletes
    d = OphydItem()
    with pytest.raises(EntryError):
        happi_client.add_device(d)


def test_add_and_find_device(
    happi_client: Client,
    valve: OphydItem,
    valve_info: Dict[str, Any]
):
    happi_client.add_device(valve)
    loaded_device = happi_client.find_device(**valve_info)
    assert loaded_device.prefix == valve.prefix
    assert loaded_device.name == valve.name


def test_find_device(happi_client: Client, device_info: Dict[str, Any]):
    device = happi_client.find_device(**device_info)
    assert isinstance(device, OphydItem)
    assert device.prefix == device_info['prefix']
    assert device.name == device_info['name']
    # Test edit and save
    device.stand = 'DG3'
    device.save()
    loaded_device = happi_client.find_device(**device_info)
    assert loaded_device.prefix == device_info['prefix']
    assert loaded_device.name == device_info['name']
    # Bad load
    bad = {'a': 'b'}
    happi_client.backend.save('a', bad, insert=True)
    with pytest.raises(EntryError):
        happi_client.find_device(**bad)


def test_change_item_name(happi_client: Client, device_info: Dict[str, Any]):
    device = happi_client.find_device(**device_info)
    assert device.name != 'new_name'
    device.name = 'new_name'
    device.save()
    # old entry should not exist anymore
    with pytest.raises(SearchError):
        happi_client.find_device(**device_info)
    # new entry with new name should be there
    new_device = happi_client.find_device(name=device.name)
    # prefix or other attributes should be the same
    assert new_device.prefix == device.prefix
    # we should only have one deivce now which is the new one
    assert happi_client.all_items == [new_device]


def test_validate(happi_client: Client):
    # No bad devices
    assert happi_client.validate() == list()
    # A single bad device
    happi_client.backend.save('_id', {happi_client._id_key: 'bad'},
                              insert=True)
    assert happi_client.validate() == ['bad']


def test_search(
    happi_client: Client,
    valve: OphydItem,
    device_info: Dict[str, Any]
):
    happi_client.add_device(valve)
    res = happi_client.search(name=device_info['name'])
    # Single search return
    assert len(res) == 1
    loaded_device = res[0].item
    assert loaded_device.prefix == device_info['prefix']
    assert loaded_device.name == device_info['name']
    # No results
    assert not happi_client.search(name='not')
    # Returned as dict
    res = happi_client.search(**device_info)
    loaded_device = res[0].item
    assert loaded_device['prefix'] == device_info['prefix']
    assert loaded_device['name'] == device_info['name']
    # Search off keyword
    res = happi_client.search(beamline='LCLS')
    assert len(res) == 2


def test_search_range(happi_client: Client, valve: OphydItem):
    happi_client.add_device(valve)
    # Search between two points
    res = happi_client.search_range('z', start=0, end=500)
    assert len(res) == 2
    # Search between two points, nothing found
    res = happi_client.search_range('z', start=10000, end=500000)
    assert not res
    # Search without an endpoint
    res = happi_client.search_range('z', start=0)
    assert len(res) == 2
    # Search invalid range
    with pytest.raises(ValueError):
        happi_client.search_range('z', start=1000, end=5)


def test_search_regex(
    client_with_three_valves: Client
):
    client = client_with_three_valves

    def find(**kwargs):
        return [
            dict(item) for item in
            client.search_regex(**kwargs, flags=re.IGNORECASE)
        ]

    valve1 = dict(client['VALVE1'])
    valve2 = dict(client['VALVE2'])
    valve3 = dict(client['VALVE3'])

    assert find(beamline='LCLS') == [valve1, valve2, valve3]
    assert find(beamline='lcls') == [valve1, valve2, valve3]
    assert find(beamline='nomatch') == []
    assert find(_id=r'VALVE\d') == [valve1, valve2, valve3]
    assert find(_id='VALVE[13]') == [valve1, valve3]
    assert find(prefix='BASE:VGC[23]:PV') == [valve2, valve3]


def test_get_by_id(
    happi_client: Client,
    valve: OphydItem,
    valve_info: Dict[str, Any]
):
    happi_client.add_device(valve)
    name = valve_info['name']
    for k, v in valve_info.items():
        assert happi_client[name][k] == valve_info[k]


def test_remove_device(
    happi_client: Client,
    device: OphydItem,
    valve: OphydItem,
    device_info: Dict[str, Any]
):
    happi_client.remove_device(device)
    assert list(happi_client.backend.find(device_info)) == []
    # Invalid Device
    with pytest.raises(ValueError):
        happi_client.remove_device(5)
    # Valve not in dictionary
    with pytest.raises(SearchError):
        happi_client.remove_device(valve)


def test_export(happi_client: Client, valve: OphydItem):
    # Setup client with both devices
    happi_client.add_device(valve)
    fd, temp_path = tempfile.mkstemp()
    happi_client.export(open(temp_path, 'w+'),
                        sep=',',
                        attrs=['name', 'prefix'])
    exp = open(temp_path, 'r').read()
    assert "alias,BASE:PV" in exp
    assert "name,BASE:VGC:PV" in exp
    # Cleanup
    os.remove(temp_path)
    os.close(fd)


def test_load_device(happi_client: Client, device: OphydItem):
    device = happi_client.load_device(name=device.name)
    assert isinstance(device, types.SimpleNamespace)
    assert device.hi == 'oh hello'


@pytest.mark.parametrize(
    'item, target',
    [
        ('item2_dev', 'Item1'),
        ('item1_dev', 'Item2'),
        ('valve', 'Item1')
    ],
)
def test_change_container_fail(
    happi_client: Client,
    item: str,
    target: str,
    request: pytest.FixtureRequest
):
    i = request.getfixturevalue(item)
    t = request.getfixturevalue(target)
    with pytest.raises(TransferError):
        happi_client.change_container(i, t)


def test_change_fail_mandatory(happi_client: Client, item2_dev: HappiItem):
    with pytest.raises(TransferError):
        happi_client.change_container(item2_dev, OphydItem)


@pytest.mark.parametrize(
    'item, target', [('item1_dev', 'Item1'), ('item2_dev', 'Item2')],
)
def test_change_container_pass(
    happi_client: Client,
    item: str,
    target: str,
    request: pytest.FixtureRequest
):
    i = request.getfixturevalue(item)
    t = request.getfixturevalue(target)
    kw = happi_client.change_container(i, t)

    for k in kw:
        assert i.post()[k] == kw[k]


def test_find_cfg(happi_cfg: str):
    # Use our config directory
    assert happi_cfg == Client.find_config()
    # Set the path explicitly using HAPPI env variable
    os.environ['HAPPI_CFG'] = happi_cfg
    assert happi_cfg == Client.find_config()


def test_from_cfg(happi_cfg: str):
    # happi_cfg modifies environment variables to make config discoverable
    client = Client.from_config()
    assert isinstance(client.backend, JSONBackend)
    assert client.backend.path == 'db.json'


def test_choices_for_field(happi_client: Client):
    name_choices = happi_client.choices_for_field('name')
    assert name_choices == {'alias'}
    prefix_choices = happi_client.choices_for_field('prefix')
    assert prefix_choices == {'BASE:PV'}
    with pytest.raises(SearchError):
        happi_client.choices_for_field('not_a_field')


def test_searchresults(client_with_three_valves: Client):
    valve1 = client_with_three_valves['VALVE1']
    assert isinstance(valve1.get(), types.SimpleNamespace)


def test_hashable_searchresults(client_with_three_valves: Client):
    client = client_with_three_valves
    valve1 = client['VALVE1']
    valve2 = client['VALVE2']
    valve3 = client['VALVE3']
    results1 = set(client.search_regex(name='valve1|valve2'))
    results2 = set(client.search_regex(name='valve.*'))

    assert len(results1 & results2) == 2
    assert valve1 in (results1 & results2)
    assert valve2 in (results1 & results2)
    assert len(results1 ^ results2) == 1
    assert valve3 in (results1 ^ results2)
    assert valve2 not in (results1 ^ results2)
    assert results2 == (results1 | results2)


def test_client_mapping(
    client_with_three_valves: Client,
    three_valves: Dict[str, Dict[str, Any]]
):
    client = client_with_three_valves
    assert len(client) == 3
    assert list(dict(client)) == list(three_valves.keys())
    for name in client:
        assert client[name]['name']
