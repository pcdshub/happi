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

def test_find_document(mockclient, device_info):
    doc = mockclient.find_document(**device_info)
    assert doc.pop('base')     == device_info['base']
    assert doc.pop('alias')    == device_info['alias']
    assert doc.pop('z')        == device_info['z']
    assert doc.pop('beamline') == device_info['beamline']


    #Remove id and check
    base = device_info.pop('base')
    doc  = mockclient.find_document(**device_info)
    assert doc.pop('base')     == base
    assert doc.pop('alias')    == device_info['alias']
    assert doc.pop('z')        == device_info['z']
    assert doc.pop('beamline') == device_info['beamline']

    #Not available
    with pytest.raises(SearchError):
        doc = mockclient.find_document(base='Does not Exist')

def test_create_device(mockclient, device_info):
    device = mockclient.create_device(Device, **device_info)
    assert device.base     == device_info['base']
    assert device.alias    == device_info['alias']
    assert device.z        == device_info['z']
    assert device.beamline == device_info['beamline']

    #Invalid Entry
    with pytest.raises(TypeError):
        mockclient.create_device(int)

def test_create_valve(mockclient, valve_info):
    device = mockclient.create_device(GateValve, **valve_info)
    assert isinstance(device, GateValve)
    assert device.base     == valve_info['base']
    assert device.alias    == valve_info['alias']
    assert device.z        == valve_info['z']
    assert device.beamline == valve_info['beamline']

    #Specify string as class
    device = mockclient.create_device('GateValve', **valve_info)
    assert isinstance(device, GateValve)
    assert device.base     == valve_info['base']
    assert device.alias    == valve_info['alias']
    assert device.z        == valve_info['z']
    assert device.beamline == valve_info['beamline']

    #Save
    device.save()
    loaded_device = mockclient.load_device(**valve_info)
    assert loaded_device.base     == valve_info['base']
    assert loaded_device.alias    == valve_info['alias']
    assert loaded_device.z        == valve_info['z']
    assert loaded_device.beamline == valve_info['beamline']


def test_all_devices(mockclient, device):
    assert mockclient.all_devices == [device]

def test_add_device(mockclient, valve, device, valve_info):
    mockclient.add_device(valve)
    doc = mockclient._collection.find_one(valve_info)
    assert valve.base     == doc['base']
    assert valve.alias    == doc['alias']
    assert valve.z        == doc['z']
    assert valve.beamline == doc['beamline']

    #No duplicates
    with pytest.raises(DuplicateError):
        mockclient.add_device(device)
    
    #No incompletes
    d = Device()
    with pytest.raises(EntryError):
        mockclient.add_device(d)


def test_add_and_load_device(mockclient, valve, valve_info):
    mockclient.add_device(valve)
    loaded_device = mockclient.load_device(**valve_info)
    assert loaded_device.base     == valve.base
    assert loaded_device.alias    == valve.alias
    assert loaded_device.z        == valve.z
    assert loaded_device.beamline == valve.beamline



def test_load_device(mockclient, device_info):
    device = mockclient.load_device(**device_info)
    assert isinstance(device, Device)
    assert device.base     == device_info['base']
    assert device.alias    == device_info['alias']
    assert device.z        == device_info['z']
    assert device.beamline == device_info['beamline']

    #Test edit and save
    device.stand = 'DG3'
    device.save()

    loaded_device = mockclient.load_device(**device_info)
    assert loaded_device.base     == device_info['base']
    assert loaded_device.alias    == device_info['alias']
    assert loaded_device.z        == device_info['z']
    assert loaded_device.beamline == device_info['beamline']
    assert loaded_device.stand    == 'DG3'

    #Bad load
    bad = {'a':'b'}
    mockclient._collection.insert_one(bad)
    with pytest.raises(EntryError):
        mockclient.load_device(**bad)


def test_validate(mockclient):
    #No bad devices
    assert mockclient.validate() == list()
    #A single bad device
    mockclient._collection.insert_one({'_id':'bad'})
    assert mockclient.validate() == ['bad']


def test_search(mockclient, device, valve, device_info, valve_info):
    mockclient.add_device(valve)
    res = mockclient.search(alias=device_info['alias'])
    #Single search return
    assert len(res) == 1
    loaded_device = res[0]
    assert loaded_device.base     == device_info['base']
    assert loaded_device.alias    == device_info['alias']
    assert loaded_device.z        == device_info['z']
    assert loaded_device.beamline == device_info['beamline']

    #No results
    assert mockclient.search(alias='not') == None

    #returned as dict
    res = mockclient.search(**device_info, as_dict=True)
    loaded_device = res[0]
    assert loaded_device['base']     == device_info['base']
    assert loaded_device['alias']    == device_info['alias']
    assert loaded_device['z']        == device_info['z']
    assert loaded_device['beamline'] == device_info['beamline']

    #Search between two points
    res = mockclient.search(start=0, end=500)
    assert len(res) == 2
    loaded_device = res[0]
    assert loaded_device.base     == device_info['base']
    assert loaded_device.alias    == device_info['alias']
    assert loaded_device.z        == device_info['z']
    assert loaded_device.beamline == device_info['beamline']

    #Search between two points, nothing found
    res = mockclient.search(start=10000, end=500000)
    assert res == None

    #Search without an endpoint
    res = mockclient.search(start=0)
    assert len(res) == 2
    loaded_device = res[1]
    assert loaded_device.base     == valve_info['base']
    assert loaded_device.alias    == valve_info['alias']
    assert loaded_device.z        == valve_info['z']
    assert loaded_device.beamline == valve_info['beamline']

    #Search invalid range
    with pytest.raises(ValueError):
        mockclient.search(start=1000,end=5)
    
    #Search off keyword
    res = mockclient.search(beamline='LCLS')
    assert len(res) == 2


def test_remove_device(mockclient,device, valve, device_info):
    mockclient.remove_device(device)
    assert mockclient._collection.find_one(device_info) == None

    #Invalid Device
    with pytest.raises(ValueError):
        mockclient.remove_device(5)
    
    #Valve not in dictionary
    with pytest.raises(SearchError):
        mockclient.remove_device(valve)

def test_export(mockclient, valve):
    #Setup client with both devices
    mockclient.add_device(valve)
    fd, temp_path = tempfile.mkstemp()

    mockclient.export(open(temp_path, 'w+'), sep=',', attrs=['alias','base'])
    assert open(temp_path,'r').read() == "alias,BASE:PV\nname,BASE:VGC:PV\n"
   
    #Cleanup
    os.remove(temp_path)
    os.close(fd)

