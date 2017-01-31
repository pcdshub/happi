import pytest
from happi import Device
from happi.device import EntryInfo

@pytest.fixture(scope='function')
def device_info():
    return {'alias':'alias', 'z':400, 'id':'BASE:PV',
            'base':'BASE:PV', 'beamline':'LCLS',
            'type':'Device', '_id':'BASE:PV'}

@pytest.fixture(scope='function')
def device(device_info):
    t = Device(**device_info)
    print('device',t)
    return t

@pytest.fixture(scope='function')
def device2_info():
    return {'alias':'name', 'z':300, 'id':'BASE:PV2',
            'base':'BASE:PV2', 'beamline':'LCLS'}

@pytest.fixture(scope='function')
def device2(device2_info):
    t = Device(**device2_info)
    print('device',t)
    return t


@pytest.fixture(scope='function')
def inc_device():
    t = Device()
    print('device',t)
    return t



