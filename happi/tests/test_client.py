import os
import logging
import tempfile
import types

import pytest

from happi import Client, Device
from happi.backends.json_db import JSONBackend
from happi.containers import GateValve
from happi.errors import SearchError, DuplicateError, EntryError

logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def happi_cfg():
    # Store current happi config
    xdg_cfg = os.environ.get("XDG_CONFIG_HOME", '')
    happi_cfg = os.environ.get("HAPPI_CFG", '')
    # Setup environment variables
    os.environ['XDG_CONFIG_HOME'] = os.getcwd()
    os.environ['HAPPI_CFG'] = ''
    # Write file
    fname = os.path.join(os.getcwd(), 'happi.cfg')
    with open(fname, 'w+') as handle:
        handle.write("""\
[DEFAULT]
backend=json
path=db.json
""")
    yield fname
    # Restore environment variables
    os.environ["HAPPI_CFG"] = happi_cfg
    os.environ["XDG_CONFIG_HOME"] = xdg_cfg
    os.remove(fname)


def test_find_document(happi_client, device_info):
    doc = happi_client.find_document(**device_info)
    assert doc.pop('prefix') == device_info['prefix']
    assert doc.pop('name') == device_info['name']
    assert doc.pop('z') == device_info['z']
    assert doc.pop('beamline') == device_info['beamline']
    # Remove id and check
    prefix = device_info.pop('prefix')
    doc = happi_client.find_document(**device_info)

    assert doc.pop('prefix') == prefix
    assert doc.pop('name') == device_info['name']
    assert doc.pop('z') == device_info['z']
    assert doc.pop('beamline') == device_info['beamline']
    # Not available
    with pytest.raises(SearchError):
        doc = happi_client.find_document(prefix='Does not Exist')


def test_create_device(happi_client, device_info):
    device = happi_client.create_device(Device, **device_info)
    assert device.prefix == device_info['prefix']
    assert device.name == device_info['name']
    assert device.z == device_info['z']
    assert device.beamline == device_info['beamline']
    # Invalid Entry
    with pytest.raises(TypeError):
        happi_client.create_device(int)


def test_create_valve(happi_client, valve_info):
    device = happi_client.create_device(GateValve, **valve_info)
    assert isinstance(device, GateValve)
    assert device.prefix == valve_info['prefix']
    assert device.name == valve_info['name']
    assert device.z == valve_info['z']
    assert device.beamline == valve_info['beamline']
    # Specify string as class
    device = happi_client.create_device('GateValve', **valve_info)
    assert isinstance(device, GateValve)
    assert device.prefix == valve_info['prefix']
    assert device.name == valve_info['name']
    assert device.z == valve_info['z']
    assert device.beamline == valve_info['beamline']
    # Save
    device.save()
    loaded_device = happi_client.find_device(**valve_info)
    assert loaded_device.prefix == valve_info['prefix']
    assert loaded_device.name == valve_info['name']
    assert loaded_device.z == valve_info['z']
    assert loaded_device.beamline == valve_info['beamline']


def test_all_devices(happi_client, device):
    assert happi_client.all_devices == [device]


def test_add_device(happi_client, valve):
    happi_client.add_device(valve)
    # No duplicates
    with pytest.raises(DuplicateError):
        happi_client.add_device(valve)
    # No incompletes
    d = Device()
    with pytest.raises(EntryError):
        happi_client.add_device(d)


def test_add_and_find_device(happi_client, valve, valve_info):
    happi_client.add_device(valve)
    loaded_device = happi_client.find_device(**valve_info)
    assert loaded_device.prefix == valve.prefix
    assert loaded_device.name == valve.name
    assert loaded_device.z == valve.z
    assert loaded_device.beamline == valve.beamline


def test_find_device(happi_client, device_info):
    device = happi_client.find_device(**device_info)
    assert isinstance(device, Device)
    assert device.prefix == device_info['prefix']
    assert device.name == device_info['name']
    assert device.z == device_info['z']
    assert device.beamline == device_info['beamline']
    # Test edit and save
    device.stand = 'DG3'
    device.save()
    loaded_device = happi_client.find_device(**device_info)
    assert loaded_device.prefix == device_info['prefix']
    assert loaded_device.name == device_info['name']
    assert loaded_device.z == device_info['z']
    assert loaded_device.beamline == device_info['beamline']
    assert loaded_device.stand == 'DG3'
    # Bad load
    bad = {'a': 'b'}
    happi_client.backend.save('a', bad, insert=True)
    with pytest.raises(EntryError):
        happi_client.find_device(**bad)


def test_validate(happi_client):
    # No bad devices
    assert happi_client.validate() == list()
    # A single bad device
    happi_client.backend.save('_id', {happi_client._id: 'bad'}, insert=True)
    assert happi_client.validate() == ['bad']


def test_search(happi_client, device, valve, device_info, valve_info):
    happi_client.add_device(valve)
    res = happi_client.search(name=device_info['name'])
    # Single search return
    assert len(res) == 1
    loaded_device = res[0]
    assert loaded_device.prefix == device_info['prefix']
    assert loaded_device.name == device_info['name']
    assert loaded_device.z == device_info['z']
    assert loaded_device.beamline == device_info['beamline']
    # No results
    assert happi_client.search(name='not') is None
    # Returned as dict
    res = happi_client.search(as_dict=True, **device_info)
    loaded_device = res[0]
    assert loaded_device['prefix'] == device_info['prefix']
    assert loaded_device['name'] == device_info['name']
    assert loaded_device['z'] == device_info['z']
    assert loaded_device['beamline'] == device_info['beamline']
    # Search between two points
    res = happi_client.search(start=0, end=500)
    assert len(res) == 2
    loaded_device = res[0]
    # Search between two points, nothing found
    res = happi_client.search(start=10000, end=500000)
    assert res is None
    # Search without an endpoint
    res = happi_client.search(start=0)
    assert len(res) == 2
    loaded_device = res[1]
    # Search invalid range
    with pytest.raises(ValueError):
        happi_client.search(start=1000, end=5)
    # Search off keyword
    res = happi_client.search(beamline='LCLS')
    assert len(res) == 2


def test_remove_device(happi_client, device, valve, device_info):
    happi_client.remove_device(device)
    assert happi_client.backend.find(**device_info) == []
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
    beamline_choices = happi_client.choices_for_field('beamline')
    assert beamline_choices == {'LCLS'}
    name_choices = happi_client.choices_for_field('name')
    assert name_choices == {'alias'}
    prefix_choices = happi_client.choices_for_field('prefix')
    assert prefix_choices == {'BASE:PV'}
    with pytest.raises(SearchError):
        happi_client.choices_for_field('not_a_field')
