import pytest
import logging

from happi import Device, Client

logger = logging.getLogger(__name__)


@pytest.fixture(scope='module')
def client(device):
    client = TestClient(user='test',pw='test',db='test')
    print('client',client)
    client._session.insert_one(device.post())
    yield client
    print("Tearing down client ...")
    client._session.delete_one(device.post())


def test_create_device(client):
    info = {'base':'PV',
            'z'   : 10.}

    device = client.create_device(Device, **info)
    assert device.base = info['base']
    assert device.z    = info['z']

def test_add_device_failure(client):
    with 
def test_find_document(client):
    doc = client.find_document(base='BASE:PV')
    assert doc.pop('base') == 'BASE:PV'

def test_load_device(client):
    device = client.load_device(base='BASE:PV')
    assert isinstance(device, Device)
    assert device.base == 'BASE:PV'

def test_search

def test_dict_search(client):

def test_z_search(client):

def test_remove_device(client,device):
