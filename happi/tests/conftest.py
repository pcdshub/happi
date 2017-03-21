############
# Standard #
############


###############
# Third Party #
###############
import pytest
from mongomock import MongoClient

##########
# Module #
##########
from happi            import Client, Device
from happi.errors     import DatabaseError
from happi.containers import GateValve

@pytest.fixture(scope='function')
def device_info():
    return {'alias' : 'alias',
            'z'     : 400,
            '_id'   : 'BASE:PV',
            'base'  : 'BASE:PV',
            'beamline' : 'LCLS',
            'type'  : 'Device',}

@pytest.fixture(scope='function')
def device(device_info):
    t = Device(**device_info)
    return t

@pytest.fixture(scope='function')
def valve_info():
    return {'alias' : 'name',
            'z'     : 300,
            'base'  : 'BASE:VGC:PV',
            'beamline':'LCLS',
            'mps' : 'MPS:VGC:PV'}

@pytest.fixture(scope='function')
def valve(valve_info):
    t = Device(**valve_info)
    return t


class MockClient(Client):


    def __init__(self, *args, **kwargs):
        try:
            super(MockClient, self).__init__(timeout=0.001)

        except DatabaseError:
            pass

        finally:
            self._client     = MongoClient(self._conn_str.format(user=self._user,
                                                                 pw=self._pw,
                                                                 host=self._host,
                                                                 db=self._db_name))
            self._db         = self._client['test']
            self._collection = self._db['happi']
            self.device_types = {'GateValve'  : GateValve,
                                 'Device' : Device}


@pytest.fixture(scope='function')
def mockclient(device_info):
    client = MockClient()
    client._collection.insert_one(device_info)
    return client


