import pytest
import logging

from happi            import Device, Client
from happi.containers import GateValve
from happi.errors     import EntryError, SearchError

logger = logging.getLogger(__name__)


@pytest.fixture(scope='module')
def base_client():
    cl = Client(user='test',pw='test',db='test')
    print('client',cl)
    return cl

@pytest.fixture(scope='function')
def client(base_client, device_info):
    base_client._collection.insert_one(device_info)
    yield base_client
    print("Tearing down client ...")
    base_client._collection.delete_many({})


def test_find_document(client, device_info):
    doc = client.find_document(**device_info)
    assert doc.pop('base')     == device_info['base']
    assert doc.pop('alias')    == device_info['alias']
    assert doc.pop('z')        == device_info['z']
    assert doc.pop('beamline') == device_info['beamline']

def test_error_on_not_found_document(client):
    with pytest.raises(SearchError):
        doc = client.find_document(base='Does not Exist')

def test_create_device(client, device_info):
    device = client.create_device(Device, **device_info)
    assert device.base     == device_info['base']
    assert device.alias    == device_info['alias']
    assert device.z        == device_info['z']
    assert device.beamline == device_info['beamline']

def test_create_valve(client, device_info):
    device = client.create_device(GateValve, **device_info)
    assert isinstance(device, GateValve)
    assert device.base     == device_info['base']
    assert device.alias    == device_info['alias']
    assert device.z        == device_info['z']
    assert device.beamline == device_info['beamline']

def test_create_valve_with_string(client, device_info):
    device = client.create_device('GateValve', **device_info)
    assert isinstance(device, GateValve)
    assert device.base     == device_info['base']
    assert device.alias    == device_info['alias']
    assert device.z        == device_info['z']
    assert device.beamline == device_info['beamline']


def test_add_device(client, device2, device2_info):
    client.add_device(device2)
    doc = client._collection.find_one(device2_info)
    assert device2.base     == device2_info['base']
    assert device2.alias    == device2_info['alias']
    assert device2.z        == device2_info['z']
    assert device2.beamline == device2_info['beamline']

def test_add_device_error_on_mandatory_info(client, inc_device):
    with pytest.raises(EntryError):
        client.add_device(inc_device)


def test_load_device(client, device_info):
    device = client.load_device(**device_info)
    assert isinstance(device, Device)
    assert device.base     == device_info['base']
    assert device.alias    == device_info['alias']
    assert device.z        == device_info['z']
    assert device.beamline == device_info['beamline']


def test_load_and_save(client, device_info):
    device = client.load_device(**device_info)
    device.stand = 'DG3'
    device_info['stand'] = 'DG3'
    device.save()
    loaded_device = client.load_device(**device_info)
    assert loaded_device.alias == device.alias

def test_load_and_save_fail_on_fixed_change(client, device_info):
    device = client.load_device(**device_info)
    device.alias = 'new_alias'
    with pytest.raises(EntryError):
        device.save()


def test_validate(client):
    assert client.validate() == list()


def test_validate_failure(client):
    client._collection.insert_one({'id':'bad'})
    assert client.validate() == ['bad']

def test_search(client, device, device_info):
    res = client.search(**device_info)
    assert len(res) == 1
    loaded_device = res[0]
    assert loaded_device.base     == device_info['base']
    assert loaded_device.alias    == device_info['alias']
    assert loaded_device.z        == device_info['z']
    assert loaded_device.beamline == device_info['beamline']


def test_dict_search(client, device, device_info):
    res = client.search(**device_info, as_dict=True)
    loaded_device = res[0]
    assert loaded_device['base']     == device_info['base']
    assert loaded_device['alias']    == device_info['alias']
    assert loaded_device['z']        == device_info['z']
    assert loaded_device['beamline'] == device_info['beamline']

def test_z_search_in(client,device_info):
    res = client.search(start=0, end=500)
    assert len(res) == 1
    loaded_device = res[0]
    assert loaded_device.base     == device_info['base']
    assert loaded_device.alias    == device_info['alias']
    assert loaded_device.z        == device_info['z']
    assert loaded_device.beamline == device_info['beamline']

def test_z_search_out(client):
    res = client.search(start=10000, end=500000)
    assert res == None

def test_remove_device(client,device, device_info):
    client.remove_device(device)
    assert client._collection.find_one(device_info) == None
