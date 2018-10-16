import os
import logging
import tempfile
import types

import pytest

from happi import Device
from happi.containers import GateValve
from happi.errors import SearchError, DuplicateError, EntryError
from .conftest import has_mongomock, mockmongoclient, mockjsonclient

logger = logging.getLogger(__name__)


def pytest_generate_tests(metafunc):
    idlist = []
    argvalues = []
    # Select clients for current environment
    clients = [('json', mockjsonclient)]
    if has_mongomock:
        clients.append(('mongo', mockmongoclient))
    # Load clients into test suite
    for case in clients:
        idlist.append(case[0])
        argvalues.append(case[1])
    metafunc.parametrize('mc', argvalues, ids=idlist, scope='class')


class TestClient:

    def teardown_method(self, method):
        if os.path.exists('testing.json'):
            os.remove('testing.json')

    def test_find_document(self, mc, device_info):
        client = mc()
        doc = client.find_document(**device_info)
        assert doc.pop('prefix') == device_info['prefix']
        assert doc.pop('name') == device_info['name']
        assert doc.pop('z') == device_info['z']
        assert doc.pop('beamline') == device_info['beamline']
        # Remove id and check
        prefix = device_info.pop('prefix')
        doc = client.find_document(**device_info)

        assert doc.pop('prefix') == prefix
        assert doc.pop('name') == device_info['name']
        assert doc.pop('z') == device_info['z']
        assert doc.pop('beamline') == device_info['beamline']
        # Not available
        with pytest.raises(SearchError):
            doc = client.find_document(prefix='Does not Exist')

    def test_create_device(self, mc, device_info):
        client = mc()
        device = client.create_device(Device, **device_info)
        assert device.prefix == device_info['prefix']
        assert device.name == device_info['name']
        assert device.z == device_info['z']
        assert device.beamline == device_info['beamline']
        # Invalid Entry
        with pytest.raises(TypeError):
            client.create_device(int)

    def test_create_valve(self, mc, valve_info):
        client = mc()
        device = client.create_device(GateValve, **valve_info)
        assert isinstance(device, GateValve)
        assert device.prefix == valve_info['prefix']
        assert device.name == valve_info['name']
        assert device.z == valve_info['z']
        assert device.beamline == valve_info['beamline']
        # Specify string as class
        device = client.create_device('GateValve', **valve_info)
        assert isinstance(device, GateValve)
        assert device.prefix == valve_info['prefix']
        assert device.name == valve_info['name']
        assert device.z == valve_info['z']
        assert device.beamline == valve_info['beamline']
        # Save
        device.save()
        loaded_device = client.find_device(**valve_info)
        assert loaded_device.prefix == valve_info['prefix']
        assert loaded_device.name == valve_info['name']
        assert loaded_device.z == valve_info['z']
        assert loaded_device.beamline == valve_info['beamline']

    def test_all_devices(self, mc, device):
        client = mc()
        assert client.all_devices == [device]

    def test_add_device(self, mc, valve, device, valve_info):
        client = mc()
        client.add_device(valve)
        doc = client.backend.find(multiples=False, **valve_info)
        assert valve.prefix == doc['prefix']
        assert valve.name == doc['name']
        assert valve.z == doc['z']
        assert valve.beamline == doc['beamline']
        # No duplicates
        with pytest.raises(DuplicateError):
            client.add_device(device)
        # No incompletes
        d = Device()
        with pytest.raises(EntryError):
            client.add_device(d)

    def test_add_and_find_device(self, mc, valve, valve_info):
        client = mc()
        client.add_device(valve)
        loaded_device = client.find_device(**valve_info)
        assert loaded_device.prefix == valve.prefix
        assert loaded_device.name == valve.name
        assert loaded_device.z == valve.z
        assert loaded_device.beamline == valve.beamline

    def test_find_device(self, mc, device_info):
        client = mc()
        device = client.find_device(**device_info)
        assert isinstance(device, Device)
        assert device.prefix == device_info['prefix']
        assert device.name == device_info['name']
        assert device.z == device_info['z']
        assert device.beamline == device_info['beamline']
        # Test edit and save
        device.stand = 'DG3'
        device.save()
        loaded_device = client.find_device(**device_info)
        assert loaded_device.prefix == device_info['prefix']
        assert loaded_device.name == device_info['name']
        assert loaded_device.z == device_info['z']
        assert loaded_device.beamline == device_info['beamline']
        assert loaded_device.stand == 'DG3'
        # Bad load
        bad = {'a': 'b'}
        client.backend.save('a', bad, insert=True)
        with pytest.raises(EntryError):
            client.find_device(**bad)

    def test_validate(self, mc):
        client = mc()
        # No bad devices
        assert client.validate() == list()
        # A single bad device
        client.backend.save('_id', {'prefix': 'bad'}, insert=True)
        assert client.validate() == ['bad']

    def test_search(self, mc, device, valve, device_info, valve_info):
        client = mc()
        client.add_device(valve)
        res = client.search(name=device_info['name'])
        # Single search return
        assert len(res) == 1
        loaded_device = res[0]
        assert loaded_device.prefix == device_info['prefix']
        assert loaded_device.name == device_info['name']
        assert loaded_device.z == device_info['z']
        assert loaded_device.beamline == device_info['beamline']
        # No results
        assert client.search(name='not') is None
        # Returned as dict
        res = client.search(as_dict=True, **device_info)
        loaded_device = res[0]
        assert loaded_device['prefix'] == device_info['prefix']
        assert loaded_device['name'] == device_info['name']
        assert loaded_device['z'] == device_info['z']
        assert loaded_device['beamline'] == device_info['beamline']
        # Search between two points
        res = client.search(start=0, end=500)
        assert len(res) == 2
        loaded_device = res[0]
        # Search between two points, nothing found
        res = client.search(start=10000, end=500000)
        assert res is None
        # Search without an endpoint
        res = client.search(start=0)
        assert len(res) == 2
        loaded_device = res[1]
        # Search invalid range
        with pytest.raises(ValueError):
            client.search(start=1000, end=5)
        # Search off keyword
        res = client.search(beamline='LCLS')
        assert len(res) == 2

    def test_remove_device(self, mc, device, valve, device_info):
        client = mc()
        client.remove_device(device)
        assert client.backend.find(**device_info) == []
        # Invalid Device
        with pytest.raises(ValueError):
            client.remove_device(5)
        # Valve not in dictionary
        with pytest.raises(SearchError):
            client.remove_device(valve)

    def test_export(self, mc, valve):
        client = mc()
        # Setup client with both devices
        client.add_device(valve)
        fd, temp_path = tempfile.mkstemp()
        client.export(open(temp_path, 'w+'), sep=',', attrs=['name', 'prefix'])
        exp = open(temp_path, 'r').read()
        assert "alias,BASE:PV" in exp
        assert "name,BASE:VGC:PV" in exp
        # Cleanup
        os.remove(temp_path)
        os.close(fd)

    def test_load_device(self, mc, device):
        client = mc()
        device = client.load_device(name=device.name)
        assert isinstance(device, types.SimpleNamespace)
        assert device.hi == 'oh hello'
