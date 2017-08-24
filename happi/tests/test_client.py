############
# Standard #
############
import os
import logging
import tempfile

###############
# Third Party #
###############
import pytest

##########
# Module #
##########
from happi            import Device, Client
from happi.containers import GateValve
from happi.errors     import *
from .conftest import mockclient, mockjsonclient, device_info


# Have to do this the sloppy way until you can use fixtures as 
# pytest parameters see https://github.com/pytest-dev/pytest/issues/349
@pytest.fixture(scope='function', params=[mockclient, mockjsonclient],
                ids=['mongo', 'json'])
def mc(request):
    #Give the instantiated client
    client = request.param(device_info())
    yield client
    if getattr(client.backend, 'path', None):
        os.remove(client.backend.path)

def test_find_document(mc, device_info):
    doc = mc.find_document(**device_info)
    assert doc.pop('prefix')     == device_info['prefix']
    assert doc.pop('name')    == device_info['name']
    assert doc.pop('z')        == device_info['z']
    assert doc.pop('beamline') == device_info['beamline']

    #Remove id and check
    prefix = device_info.pop('prefix')
    doc  = mc.find_document(**device_info)
    assert doc.pop('prefix')     == prefix
    assert doc.pop('name')    == device_info['name']
    assert doc.pop('z')        == device_info['z']
    assert doc.pop('beamline') == device_info['beamline']

    #Not available
    with pytest.raises(SearchError):
        doc = mc.find_document(prefix='Does not Exist')

def test_create_device(mc, device_info):
    device = mc.create_device(Device, **device_info)
    assert device.prefix     == device_info['prefix']
    assert device.name    == device_info['name']
    assert device.z        == device_info['z']
    assert device.beamline == device_info['beamline']

    #Invalid Entry
    with pytest.raises(TypeError):
        mc.create_device(int)

def test_create_valve(mc, valve_info):
    device = mc.create_device(GateValve, **valve_info)
    assert isinstance(device, GateValve)
    assert device.prefix     == valve_info['prefix']
    assert device.name    == valve_info['name']
    assert device.z        == valve_info['z']
    assert device.beamline == valve_info['beamline']

    #Specify string as class
    device = mc.create_device('GateValve', **valve_info)
    assert isinstance(device, GateValve)
    assert device.prefix     == valve_info['prefix']
    assert device.name    == valve_info['name']
    assert device.z        == valve_info['z']
    assert device.beamline == valve_info['beamline']

    #Save
    device.save()
    loaded_device = mc.load_device(**valve_info)
    assert loaded_device.prefix     == valve_info['prefix']
    assert loaded_device.name    == valve_info['name']
    assert loaded_device.z        == valve_info['z']
    assert loaded_device.beamline == valve_info['beamline']


def test_all_devices(mc, device):
    assert mc.all_devices == [device]

def test_add_device(mc, valve, device, valve_info):
    mc.add_device(valve)
    doc = mc.backend.find(multiples=False, **valve_info)
    assert valve.prefix     == doc['prefix']
    assert valve.name    == doc['name']
    assert valve.z        == doc['z']
    assert valve.beamline == doc['beamline']

    #No duplicates
    with pytest.raises(DuplicateError):
        mc.add_device(device)

    #No incompletes
    d = Device()
    with pytest.raises(EntryError):
        mc.add_device(d)


def test_add_and_load_device(mc, valve, valve_info):
    mc.add_device(valve)
    loaded_device = mc.load_device(**valve_info)
    assert loaded_device.prefix     == valve.prefix
    assert loaded_device.name    == valve.name
    assert loaded_device.z        == valve.z
    assert loaded_device.beamline == valve.beamline



def test_load_device(mc, device_info):
    device = mc.load_device(**device_info)
    assert isinstance(device, Device)
    assert device.prefix     == device_info['prefix']
    assert device.name    == device_info['name']
    assert device.z        == device_info['z']
    assert device.beamline == device_info['beamline']

    #Test edit and save
    device.stand = 'DG3'
    device.save()

    loaded_device = mc.load_device(**device_info)
    assert loaded_device.prefix     == device_info['prefix']
    assert loaded_device.name    == device_info['name']
    assert loaded_device.z        == device_info['z']
    assert loaded_device.beamline == device_info['beamline']
    assert loaded_device.stand    == 'DG3'

    #Bad load
    bad = {'a':'b'}
    mc.backend.save('a', bad, insert=True)
    with pytest.raises(EntryError):
        mc.load_device(**bad)


def test_validate(mc):
    #No bad devices
    assert mc.validate() == list()
    #A single bad device
    mc.backend.save('_id', {'prefix':'bad'}, insert=True)
    assert mc.validate() == ['bad']


def test_search(mc, device, valve, device_info, valve_info):
    mc.add_device(valve)
    res = mc.search(name=device_info['name'])
    #Single search return
    assert len(res) == 1
    loaded_device = res[0]
    assert loaded_device.prefix     == device_info['prefix']
    assert loaded_device.name    == device_info['name']
    assert loaded_device.z        == device_info['z']
    assert loaded_device.beamline == device_info['beamline']

    #No results
    assert mc.search(name='not') == None

    #returned as dict
    res = mc.search(as_dict=True, **device_info)
    loaded_device = res[0]
    assert loaded_device['prefix']     == device_info['prefix']
    assert loaded_device['name']    == device_info['name']
    assert loaded_device['z']        == device_info['z']
    assert loaded_device['beamline'] == device_info['beamline']

    #Search between two points
    res = mc.search(start=0, end=500)
    assert len(res) == 2
    loaded_device = res[0]

    #Search between two points, nothing found
    res = mc.search(start=10000, end=500000)
    assert res == None

    #Search without an endpoint
    res = mc.search(start=0)
    assert len(res) == 2
    loaded_device = res[1]

    #Search invalid range
    with pytest.raises(ValueError):
        mc.search(start=1000,end=5)
    
    #Search off keyword
    res = mc.search(beamline='LCLS')
    assert len(res) == 2


def test_remove_device(mc,device, valve, device_info):
    mc.remove_device(device)
    assert mc.backend.find(**device_info) == []

    #Invalid Device
    with pytest.raises(ValueError):
        mc.remove_device(5)
    
    #Valve not in dictionary
    with pytest.raises(SearchError):
        mc.remove_device(valve)

def test_export(mc, valve):
    #Setup client with both devices
    mc.add_device(valve)
    fd, temp_path = tempfile.mkstemp()

    mc.export(open(temp_path, 'w+'), sep=',', attrs=['name','prefix'])
    exp = open(temp_path,'r').read()
    assert "alias,BASE:PV"    in exp
    assert "name,BASE:VGC:PV" in exp
   
    #Cleanup
    os.remove(temp_path)
    os.close(fd)

