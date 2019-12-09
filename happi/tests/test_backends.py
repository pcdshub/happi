import os
import fcntl
import os.path

import pytest
import simplejson

from .conftest import requires_questionnaire, requires_mongomock
from happi.backends.json_db import JSONBackend
from happi.errors import DuplicateError, SearchError
from happi import Client
from happi.containers import Motor, Trigger, Acromag


@pytest.fixture(scope='function')
def mockmongo(mockmongoclient):
    return mockmongoclient.backend


@pytest.fixture(scope='function')
def mockjson(device_info, valve_info):
    # Write underlying database
    with open('testing.json', 'w+') as handle:
        simplejson.dump({device_info['_id']: device_info},
                        handle)
    # Return handle name
    yield JSONBackend('testing.json')

    # Delete file
    os.remove('testing.json')


@requires_mongomock
def test_mongo_find(valve_info, device_info, mockmongo):
    mm = mockmongo
    mm._collection.insert_one(valve_info)
    # No single device expected
    assert mm.find(beamline='BLERG', multiples=False) == []
    # Single device by id
    assert device_info == mm.find(_id=device_info['_id'],
                                  multiples=False)
    # Single device by kwarg
    assert valve_info == mm.find(prefix=valve_info['prefix'],
                                 multiples=False)
    # No multiple devices expected
    assert mm.find(beamline='BLERG', multiples=False) == []
    # Multiple devices by id
    assert [device_info] == mm.find(_id=device_info['_id'],
                                    multiples=True)
    # Multiple devices by kwarg
    assert [device_info] == mm.find(prefix=device_info['prefix'],
                                    multiples=True)
    # Multiple devices expected
    result = mm.find(beamline='LCLS', multiples=True)
    assert all([info in result for info in (device_info, valve_info)])


@requires_mongomock
def test_mongo_save(mockmongo, device_info, valve_info):
    # Duplicate device
    with pytest.raises(DuplicateError):
        mockmongo.save(device_info[Client._id], device_info, insert=True)

    # Device not found
    with pytest.raises(SearchError):
        mockmongo.save(valve_info[Client._id], valve_info, insert=False)

    # Add to database
    mockmongo.save(valve_info[Client._id], valve_info, insert=True)
    assert mockmongo._collection.find_one(valve_info) == valve_info


@requires_mongomock
def test_mongo_delete(mockmongo, device_info):
    mockmongo.delete(device_info[Client._id])
    assert mockmongo._collection.find_one(device_info) is None


def test_json_find(valve_info, device_info, mockjson):
    mm = mockjson
    # Write underlying database
    with open(mm.path, 'w+') as handle:
        simplejson.dump({valve_info['_id']: valve_info,
                         device_info['_id']: device_info},
                        handle)
    # No single device expected
    assert mm.find(beamline='BLERG', multiples=False) == []
    # Single device by id
    assert device_info == mm.find(_id=device_info['_id'],
                                  multiples=False)
    # Single device by kwarg
    assert valve_info == mm.find(prefix=valve_info['prefix'],
                                 multiples=False)
    # No multiple devices expected
    assert mm.find(beamline='BLERG', multiples=False) == []
    # Multiple devices by id
    assert [device_info] == mm.find(_id=device_info['_id'],
                                    multiples=True)
    # Multiple devices by kwarg
    assert [device_info] == mm.find(prefix=device_info['prefix'],
                                    multiples=True)
    # Multiple devices expected
    result = mm.find(beamline='LCLS', multiples=True)
    assert all([info in result for info in (device_info, valve_info)])


def test_json_delete(mockjson, device_info):
    mockjson.delete(device_info[Client._id])
    assert device_info not in mockjson.all_devices


def test_json_save(mockjson, device_info, valve_info):
    # Duplicate device
    with pytest.raises(DuplicateError):
        mockjson.save(device_info[Client._id], device_info, insert=True)

    # Device not found
    with pytest.raises(SearchError):
        mockjson.save(valve_info[Client._id], valve_info, insert=False)

    # Add to database
    mockjson.save(valve_info[Client._id], valve_info, insert=True)
    assert valve_info in mockjson.all_devices


def test_json_locking(mockjson):
    # Place lock on file
    handle = open(mockjson.path, 'w')
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # Attempt to save
    with pytest.raises(IOError):
        mockjson.store({"_ID": "ID"})


def test_json_initialize():
    jb = JSONBackend("testing.json", initialize=True)
    # Check that the file was made
    assert os.path.exists("testing.json")
    # Check it is a valid json file
    assert jb.load() == {}
    # Check that we can not overwrite the database
    with pytest.raises(PermissionError):
        JSONBackend("testing.json", initialize=True)
    # Cleanup
    os.remove("testing.json")


@requires_questionnaire
def test_qs_find(mockqsbackend):
    assert len(mockqsbackend.find(beamline='TST', multiples=True)) == 14
    assert len(mockqsbackend.find(name='sam_r', multiples=True)) == 1


@requires_questionnaire
def test_qsbackend_with_client(mockqsbackend):
    c = Client(database=mockqsbackend)
    assert len(c.all_devices) == 14
    assert all([isinstance(d, Motor) or isinstance(d, Trigger)
                or isinstance(d, Acromag) for d in c.all_devices])
    device_types = [device.__class__ for device in c.all_devices]
    assert device_types.count(Motor) == 6
    assert device_types.count(Trigger) == 2
    assert device_types.count(Acromag) == 6
