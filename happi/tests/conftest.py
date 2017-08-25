############
# Standard #
############

###############
# Third Party #
###############
import pytest
import simplejson
from mongomock import MongoClient

##########
# Module #
##########
from happi            import Client, Device
from happi.errors     import DatabaseError
from happi.containers import GateValve
from happi.backends   import JSONBackend, MongoBackend


@pytest.fixture(scope='function')
def device_info():
    return {'name' : 'alias',
            'z'     : 400,
            '_id'   : 'BASE:PV',
            'prefix'  : 'BASE:PV',
            'beamline' : 'LCLS',
            'type'  : 'Device',}


@pytest.fixture(scope='function')
def device(device_info):
    t = Device(**device_info)
    return t


@pytest.fixture(scope='function')
def valve_info():
    return {'name' : 'name',
            'z'     : 300,
            'prefix'  : 'BASE:VGC:PV',
            '_id'     : 'BASE:VGC:PV',
            'beamline':'LCLS',
            'mps' : 'MPS:VGC:PV'}


@pytest.fixture(scope='function')
def valve(valve_info):
    t = Device(**valve_info)
    return t


@pytest.fixture(scope='function')
def mockclient(device_info):
    #Instantiate Fake Mongo Client
    client = MockClient()
    #Insert a single device
    client.backend._collection.insert_one(device_info)
    return client

@pytest.fixture(scope='function')
def mockjsonclient(device_info):
    #Write underlying database
    with open('testing.json', 'w+') as handle:
        simplejson.dump({device_info['prefix'] : device_info},
                        handle)
    #Return handle name
    db = JSONBackend('testing.json')
    return Client(database=db)

#############################################
# Classes created to mock a running MongoDB #
#############################################
class MockMongoBackend(MongoBackend):
    """
    Mock a MongoDB database
    """
    def __init__(self, *args, **kwargs):
        #Try and connect to non-existant db
        try:
            super(MockMongoBackend, self).__init__(timeout=0.001)
        except:
            pass
        #Replace with mock client
        finally:
            self._client     = MongoClient()
            self._db         = self._client['test']
            self._collection = self._db['happi']


class MockClient(Client):
    """
    Mock a full Happi Client
    """
    def __init__(self, *args, **kwargs):
        super(MockClient, self).__init__(db_type=MockMongoBackend, **kwargs)


