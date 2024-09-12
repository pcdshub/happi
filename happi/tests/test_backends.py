import os
import os.path
import tempfile
from typing import Any

import pytest
import simplejson

from happi import Client
from happi.backends.json_db import JSONBackend
from happi.backends.multi_db import MultiBackend
from happi.errors import DuplicateError, SearchError
from happi.loader import load_devices

from .conftest import (requires_mongo, requires_pcdsdevices, requires_py39,
                       requires_questionnaire)


@pytest.fixture(scope='function')
def mockmongo(mockmongoclient):
    return mockmongoclient.backend


@pytest.fixture(scope='function')
def mockjson(item_info: dict[str, Any], valve_info: dict[str, Any]):
    # Write underlying database
    with tempfile.NamedTemporaryFile(mode='w') as handle:
        simplejson.dump({item_info['_id']: item_info},
                        handle)
        handle.flush()
        # Return handle name
        yield JSONBackend(handle.name)


@pytest.fixture(scope='function')
def mockmulti(mockjson, mockmongo, valve_info, item_info):
    """ Create a multi-backend database with a mongo and json backend """
    # modify json backend to have group = 'JSON', mongo to have group='MONGO'
    for backend, group_name in zip([mockjson, mockmongo], ['JSON', 'MONGO']):
        all_docs = backend.all_items
        for doc in all_docs:
            backend.delete(doc[Client._id_key])
            doc['group'] = group_name
            backend.save(doc[Client._id_key], doc, insert=True)

    # add extra device to json backend
    mockjson.save(valve_info[Client._id_key], valve_info, insert=True)

    # add extra device to mongo backend
    extra_info = item_info.copy()
    extra_info['name'] = 'mongo_alias'
    extra_info['_id'] = 'mongo_alias'
    mockmongo.save(extra_info[Client._id_key], extra_info, insert=True)

    # json takes priority over mongo
    return MultiBackend(backends=[mockjson, mockmongo])


@requires_mongo
def test_mongo_find(
    valve_info: dict[str, Any],
    item_info: dict[str, Any],
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
    item_info: dict[str, Any],
    valve_info: dict[str, Any]
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
def test_mongo_delete(mockmongo, item_info: dict[str, Any]):
    mockmongo.delete(item_info[Client._id_key])
    assert mockmongo._collection.find_one(item_info) is None


def test_json_find(
    valve_info: dict[str, Any],
    item_info: dict[str, Any],
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


def test_json_delete(mockjson, item_info: dict[str, Any]):
    mockjson.delete(item_info[Client._id_key])
    assert item_info not in mockjson.all_items


def test_json_save(mockjson, item_info: dict[str, Any], valve_info):
    # Duplicate item
    with pytest.raises(DuplicateError):
        mockjson.save(item_info[Client._id_key], item_info, insert=True)

    # Item not found
    with pytest.raises(SearchError):
        mockjson.save(valve_info[Client._id_key], valve_info, insert=False)

    # Add to database
    mockjson.save(valve_info[Client._id_key], valve_info, insert=True)
    assert valve_info in mockjson.all_items


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


def test_json_tempfile_location():
    jb = JSONBackend("testing.json", initialize=False)
    assert os.path.dirname(jb.path) == os.path.dirname(jb._temp_path())


def test_json_tempfile_uniqueness():
    jb = JSONBackend("testing.json", initialize=False)
    tempfiles = []
    for _ in range(100):
        tempfiles.append(jb._temp_path())
    assert len(set(tempfiles)) == len(tempfiles)


def test_json_tempfile_remove(monkeypatch):
    # Set consistent temppath
    jb = JSONBackend("testing.json", initialize=False)
    temp_path = jb._temp_path()
    jb._temp_path = lambda: temp_path

    # Ensure file is created, then throw error through patching
    def shutil_move_patch(*args, **kwargs):
        assert os.path.isfile(os.path.join(os.getcwd(), temp_path))
        raise RuntimeError('Simulated testing error.')

    monkeypatch.setattr('shutil.move', shutil_move_patch)

    # Test, and ensure file is deleted appropriately
    with pytest.raises(RuntimeError):
        jb.initialize()
    assert os.path.exists(temp_path) is False


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


@requires_mongo
def test_multi_backend(mockmulti, item_info, valve_info):
    mm = mockmulti
    assert len(mm.all_items) == 3
    assert len(mm.backends[0].all_items) == 2
    assert len(mm.backends[1].all_items) == 2

    # duplicate name/id in both backends
    assert len(list(mm.backends[0].find({'_id': item_info['_id']})))
    assert len(list(mm.backends[1].find({'_id': item_info['_id']})))
    # JSON backend takes priority
    assert list(mm.find({'_id': item_info['_id']}))[0]['group'] == 'JSON'

    # get_id works similarly
    assert mm.backends[0].get_by_id(item_info['_id'])
    assert mm.backends[1].get_by_id(item_info['_id'])
    assert mm.backends[1].get_by_id(item_info['_id'])['group'] == 'MONGO'

    assert mm.get_by_id(item_info['_id'])['group'] == 'JSON'

    dev = list(mm.find_regex({'_id': item_info['_id']}))[0]
    assert mm.get_by_id(item_info['_id']) == dev

    # extra items in backend
    assert mm.get_by_id(valve_info['_id'])
    assert list(mm.find({'_id': valve_info['_id']}))

    assert mm.get_by_id('mongo_alias')
    assert list(mm.find({'_id': 'mongo_alias'}))
