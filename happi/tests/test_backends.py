import fcntl
import os
import os.path
import tempfile
from typing import Any, Dict

import pytest
import simplejson

from happi import Client
from happi.backends.json_db import JSONBackend
from happi.errors import DuplicateError, SearchError
from happi.loader import load_devices

from .conftest import (requires_mongo, requires_pcdsdevices, requires_py39,
                       requires_questionnaire)


@pytest.fixture(scope='function')
def mockmongo(mockmongoclient):
    return mockmongoclient.backend


@pytest.fixture(scope='function')
def mockjson(item_info: Dict[str, Any], valve_info: Dict[str, Any]):
    # Write underlying database
    with tempfile.NamedTemporaryFile(mode='w') as handle:
        simplejson.dump({item_info['_id']: item_info},
                        handle)
        handle.flush()
        # Return handle name
        yield JSONBackend(handle.name)


@requires_mongo
def test_mongo_find(
    valve_info: Dict[str, Any],
    item_info: Dict[str, Any],
    mockmongo
):
    mm = mockmongo
    mm._collection.insert_one(valve_info)

    def find(**kwargs):
        return list(mm.find(kwargs))

    assert find(beamline='BLERG') == []
    # Single item by id
    assert [item_info] == find(_id=item_info['_id'])
    # Single item by kwarg
    assert [valve_info] == find(prefix=valve_info['prefix'])
    # No multiple items expected
    assert find(beamline='BLERG') == []
    # Multiple items by id
    assert [item_info] == find(_id=item_info['_id'])
    # Multiple items by kwarg
    assert [item_info] == find(prefix=item_info['prefix'])
    # Multiple items expected
    assert all(info in find(beamline='LCLS')
               for info in (item_info, valve_info))


@requires_mongo
def test_mongo_save(
    mockmongo,
    item_info: Dict[str, Any],
    valve_info: Dict[str, Any]
):
    # Duplicate item
    with pytest.raises(DuplicateError):
        mockmongo.save(item_info[Client._id_key], item_info, insert=True)

    # Item not found
    with pytest.raises(SearchError):
        mockmongo.save(valve_info[Client._id_key], valve_info, insert=False)

    # Add to database
    mockmongo.save(valve_info[Client._id_key], valve_info, insert=True)
    assert mockmongo._collection.find_one(valve_info) == valve_info


@requires_mongo
def test_mongo_delete(mockmongo, item_info: Dict[str, Any]):
    mockmongo.delete(item_info[Client._id_key])
    assert mockmongo._collection.find_one(item_info) is None


def test_json_find(
    valve_info: Dict[str, Any],
    item_info: Dict[str, Any],
    mockjson
):
    mm = mockjson
    # Write underlying database
    with open(mm.path, 'w+') as handle:
        simplejson.dump({valve_info['_id']: valve_info,
                         item_info['_id']: item_info},
                        handle)

    def find(**kwargs):
        return list(mm.find(kwargs))

    # No single item expected
    assert find(beamline='BLERG') == []
    # Single item by id
    assert [item_info] == find(_id=item_info['_id'])
    # Single item by kwarg
    assert [valve_info] == find(prefix=valve_info['prefix'])
    # No multiple items expected
    assert find(beamline='BLERG') == []
    # Multiple items by id
    assert [item_info] == find(_id=item_info['_id'])
    # Multiple items by kwarg
    assert [item_info] == find(prefix=item_info['prefix'])
    # Multiple items expected
    assert all(info in find(beamline='LCLS')
               for info in (item_info, valve_info))


def test_find_regex(client_with_three_valves, three_valves):
    client = client_with_three_valves

    def find(**kwargs):
        return list(client.backend.find_regex(kwargs))

    valve1 = three_valves['VALVE1']
    valve2 = three_valves['VALVE2']
    valve3 = three_valves['VALVE3']
    assert find(beamline='LCLS') == [valve1, valve2, valve3]
    assert find(beamline='lcls') == [valve1, valve2, valve3]
    assert find(beamline='nomatch') == []
    assert find(_id=r'VALVE\d') == [valve1, valve2, valve3]
    assert find(_id='VALVE[13]') == [valve1, valve3]
    assert find(prefix='BASE:VGC[23]:PV') == [valve2, valve3]


def test_json_delete(mockjson, item_info: Dict[str, Any]):
    mockjson.delete(item_info[Client._id_key])
    assert item_info not in mockjson.all_items


def test_json_save(mockjson, item_info: Dict[str, Any], valve_info):
    # Duplicate item
    with pytest.raises(DuplicateError):
        mockjson.save(item_info[Client._id_key], item_info, insert=True)

    # Item not found
    with pytest.raises(SearchError):
        mockjson.save(valve_info[Client._id_key], valve_info, insert=False)

    # Add to database
    mockjson.save(valve_info[Client._id_key], valve_info, insert=True)
    assert valve_info in mockjson.all_items


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
    assert len(list(mockqsbackend.find(dict(beamline='TST')))) == 14
    assert len(list(mockqsbackend.find(dict(name='sam_r')))) == 1


@requires_questionnaire
@requires_pcdsdevices
def test_qsbackend_with_client(mockqsbackend):
    c = Client(database=mockqsbackend)
    assert len(c.all_items) == 14
    assert all(
        d.__class__.__name__ in {'Trigger', 'Motor', 'Acromag', 'LCLSItem'}
        for d in c.all_items
    )
    item_types = [item.__class__.__name__ for item in c.all_items]
    assert item_types.count('Motor') == 7
    assert item_types.count('Trigger') == 2
    # Acromag: six entries, but one erroneously has the same name
    assert item_types.count('Acromag') == 5


@requires_questionnaire
@requires_pcdsdevices
@requires_py39
def test_qsbackend_with_acromag(mockqsbackend):
    c = Client(database=mockqsbackend)
    d = load_devices(*c.all_items, pprint=False).__dict__
    ai1 = d.get('ai_7')
    ao1 = d.get('ao_6')
    assert ai1.__class__.__name__ == 'EpicsSignalRO'
    assert ao1.__class__.__name__ == 'EpicsSignal'


@requires_questionnaire
@requires_pcdsdevices
@requires_py39
def test_beckoff_axis_device_class(mockqsbackend):
    c = Client(database=mockqsbackend)
    d = load_devices(*c.all_items).__dict__
    vh_y = d.get('vh_y')
    sam_x = d.get('sam_x')
    assert vh_y.__class__.__name__ == 'BeckhoffAxis'
    assert sam_x.__class__.__name__ == 'IMS'
