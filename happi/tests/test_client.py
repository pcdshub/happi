import os
import logging
import re
import tempfile
import types

import pytest

from happi import Client, OphydItem
from happi.backends.json_db import JSONBackend
from happi.errors import SearchError, DuplicateError, EntryError

logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def xdg_config_home(tmp_path):
    config_home = tmp_path / 'xdg_config_home'
    config_home.mkdir()
    return config_home


@pytest.fixture(scope='function')
def happi_cfg(tmp_path, xdg_config_home):
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


def test_find_document(happi_client, device_info):
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


def test_create_device(happi_client, device_info):
    device = happi_client.create_device(OphydItem, **device_info)
    assert device.prefix == device_info['prefix']
    assert device.name == device_info['name']
    # Invalid Entry
    with pytest.raises(TypeError):
        happi_client.create_device(int)


def test_all_devices(happi_client, device):
    assert happi_client.all_devices == [device]


def test_add_device(happi_client, valve):
    happi_client.add_device(valve)
    # No duplicates
    with pytest.raises(DuplicateError):
        happi_client.add_device(valve)
    # No incompletes
    d = OphydItem()
    with pytest.raises(EntryError):
        happi_client.add_device(d)


def test_add_and_find_device(happi_client, valve, valve_info):
    happi_client.add_device(valve)
    loaded_device = happi_client.find_device(**valve_info)
    assert loaded_device.prefix == valve.prefix
    assert loaded_device.name == valve.name


def test_find_device(happi_client, device_info):
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


def test_validate(happi_client):
    # No bad devices
    assert happi_client.validate() == list()
    # A single bad device
    happi_client.backend.save('_id', {happi_client._id_key: 'bad'},
                              insert=True)
    assert happi_client.validate() == ['bad']


def test_search(happi_client, device, valve, device_info, valve_info):
    happi_client.add_device(valve)
    res = happi_client.search(name=device_info['name'])
    # Single search return
    assert len(res) == 1
    loaded_device = res[0].device
    assert loaded_device.prefix == device_info['prefix']
    assert loaded_device.name == device_info['name']
    # No results
    assert not happi_client.search(name='not')
    # Returned as dict
    res = happi_client.search(**device_info)
    loaded_device = res[0].device
    assert loaded_device['prefix'] == device_info['prefix']
    assert loaded_device['name'] == device_info['name']
    # Search off keyword
    res = happi_client.search(beamline='LCLS')
    assert len(res) == 2


def test_search_range(happi_client, device, valve, device_info, valve_info):
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


def test_search_regex(happi_client, three_valves):
    def find(**kwargs):
        return [
            dict(item) for item in
            happi_client.search_regex(**kwargs, flags=re.IGNORECASE)
        ]

    valve1 = dict(happi_client['VALVE1'])
    valve2 = dict(happi_client['VALVE2'])
    valve3 = dict(happi_client['VALVE3'])

    assert find(beamline='LCLS') == [valve1, valve2, valve3]
    assert find(beamline='lcls') == [valve1, valve2, valve3]
    assert find(beamline='nomatch') == []
    assert find(_id=r'VALVE\d') == [valve1, valve2, valve3]
    assert find(_id='VALVE[13]') == [valve1, valve3]
    assert find(prefix='BASE:VGC[23]:PV') == [valve2, valve3]


def test_get_by_id(happi_client, device, valve, device_info, valve_info):
    happi_client.add_device(valve)
    name = valve_info['name']
    for k, v in valve_info.items():
        assert happi_client[name][k] == valve_info[k]


def test_remove_device(happi_client, device, valve, device_info):
    happi_client.remove_device(device)
    assert list(happi_client.backend.find(device_info)) == []
    # Invalid Device
    with pytest.raises(ValueError):
        happi_client.remove_device(5)
    # Valve not in dictionary
    with pytest.raises(SearchError):
        happi_client.remove_device(valve)


def test_export(happi_client, valve):
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


def test_load_device(happi_client, device):
    device = happi_client.load_device(name=device.name)
    assert isinstance(device, types.SimpleNamespace)
    assert device.hi == 'oh hello'


def test_find_cfg(happi_cfg):
    # Use our config directory
    assert happi_cfg == Client.find_config()
    # Set the path explicitly using HAPPI env variable
    os.environ['HAPPI_CFG'] = happi_cfg
    assert happi_cfg == Client.find_config()


def test_from_cfg(happi_cfg):
    client = Client.from_config()
    assert isinstance(client.backend, JSONBackend)
    assert client.backend.path == 'db.json'


def test_choices_for_field(happi_client):
    name_choices = happi_client.choices_for_field('name')
    assert name_choices == {'alias'}
    prefix_choices = happi_client.choices_for_field('prefix')
    assert prefix_choices == {'BASE:PV'}
    with pytest.raises(SearchError):
        happi_client.choices_for_field('not_a_field')


def test_searchresults(happi_client, three_valves):
    valve1 = happi_client['VALVE1']
    print(repr(valve1))
    print(dict(valve1))
    assert valve1.metadata == valve1
    assert isinstance(valve1.get(), types.SimpleNamespace)


def test_client_mapping(happi_client, three_valves):
    assert len(happi_client) == 3
    assert list(dict(happi_client)) == ['VALVE1', 'VALVE2', 'VALVE3']
    for name in happi_client:
        assert happi_client[name]['name']
