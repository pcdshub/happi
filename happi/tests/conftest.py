import logging
from unittest.mock import patch

import pytest
import simplejson

from happi import Client, Device
from happi.backends.json_db import JSONBackend
from happi.backends.mongo_db import MongoBackend

logger = logging.getLogger(__name__)


# Conditional import of mongomock
try:
    from mongomock import MongoClient
    has_mongomock = True
except ImportError as exc:
    logger.warning('Error importing mongomock : -> %s', exc)
    has_mongomock = False


requires_mongomock = pytest.mark.skipif(not has_mongomock,
                                        reason='Missing mongomock')


@pytest.fixture(scope='function')
def device_info():
    return {'name': 'alias',
            'z': 400,
            '_id': 'BASE:PV',
            'prefix': 'BASE:PV',
            'beamline': 'LCLS',
            'type': 'Device'}


@pytest.fixture(scope='function')
def device():
    t = Device(**device_info())
    return t


@pytest.fixture(scope='function')
def valve_info():
    return {'name': 'name',
            'z': 300,
            'prefix': 'BASE:VGC:PV',
            '_id': 'BASE:VGC:PV',
            'beamline': 'LCLS',
            'mps': 'MPS:VGC:PV'}


@pytest.fixture(scope='function')
def valve():
    t = Device(**valve_info())
    return t


@pytest.fixture(scope='function')
def mockjsonclient():
    # Write underlying database
    with open('testing.json', 'w+') as handle:
        simplejson.dump({device_info()['prefix']: device_info()},
                        handle)
    # Return handle name
    db = JSONBackend('testing.json')
    return Client(database=db)


@pytest.fixture(scope='function')
def mockmongoclient(*args):
    with patch('happi.backends.mongo_db.MongoClient') as mock_mongo:
        mc = MongoClient()
        mc['test_db'].create_collection('test_collect')
        mock_mongo.return_value = mc
        # Client
        backend = MongoBackend(db='test_db',
                               collection='test_collect')
        client = Client(database=backend)
        # Insert a single device
        client.backend._collection.insert_one(device_info())
        return client
