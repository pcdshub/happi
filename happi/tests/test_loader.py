from happi import Device, EntryInfo
from happi.loader import fill_template, from_container, load_devices
from happi.utils import create_alias


class TimeDevice(Device):
    days = EntryInfo("Number of days", enforce=int)


def test_fill_template(device):
    # Check that we can properly render a template
    template = "{{name}}"
    assert device.name == fill_template(template, device)
    # Check that we can enforce a type
    template = '{{z}}'
    z = fill_template(template, device, enforce_type=True)
    assert isinstance(z, float)


def test_from_container():
    # Create a datetime device
    d = TimeDevice(name='Test', prefix='Tst:This', beamline='TST',
                   device_class='datetime.timedelta', args=list(), days=10,
                   kwargs={'days': '{{days}}', 'seconds': 30})
    td = from_container(d)
    # Now import datetime and check that we constructed ours correctly
    import datetime
    assert td == datetime.timedelta(days=10, seconds=30)


def test_load_devices():
    # Create a bunch of devices to load
    devs = [TimeDevice(name='Test 1', prefix='Tst1:This', beamline='TST',
                       device_class='datetime.timedelta', args=list(), days=10,
                       kwargs={'days': '{{days}}', 'seconds': 30}),
            TimeDevice(name='Test 2', prefix='Tst2:This', beamline='TST',
                       device_class='datetime.timedelta', args=list(), days=10,
                       kwargs={'days': '{{days}}', 'seconds': 30}),
            TimeDevice(name='Test 3', prefix='Tst3:This', beamline='TST',
                       device_class='datetime.timedelta', args=list(), days=10,
                       kwargs={'days': '{{days}}', 'seconds': 30}),
            Device(name='Bad', prefix='Not:Here', beamline='BAD',
                   device_class='non.existant')]
    # Load our devices
    space = load_devices(*devs, pprint=True)
    # Check all our devices are there
    assert all([create_alias(dev.name) in space.__dict__ for dev in devs])
    # Devices were loading properly or exceptions were stored
    import datetime
    assert space.test_1 == datetime.timedelta(days=10, seconds=30)
    assert isinstance(space.bad, ImportError)
