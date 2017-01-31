import pytest
from happi import Device
from happi.device import EntryInfo

class ExampleDevice(Device):
    optional  = EntryInfo()
    default   = EntryInfo(default=True)
    enforced  = EntryInfo(enforce=int,default=1)
    doc       = EntryInfo('docstring')

@pytest.fixture(scope='function')
def device():
    t = ExampleDevice(alias='alias', z='400',
                   base='BASE:PV',beamline='LCLS')
    print('device',t)
    return t

@pytest.fixture(scope='function')
def device2():
    t = ExampleDevice(alias='name', z='300',
                   base='BASE:PV2',beamline='LCLS')
    print('device',t)
    return t


@pytest.fixture(scope='function')
def inc_device():
    t = ExampleDevice(alias='alias', z='400')
    print('device',t)
    return t



