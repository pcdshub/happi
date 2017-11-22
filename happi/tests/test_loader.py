############
# Standard #
############

###############
# Third Party #
###############


##########
# Module #
##########
from happi import Device, EntryInfo
from happi.loader import fill_template, from_container


def test_fill_template(device):
    # Check that we can properly render a template
    template = "{{name}}"
    assert device.name == fill_template(template, device)
    # Check that we can enforce a type
    template = '{{z}}'
    z = fill_template(template, device, enforce_type=True)
    assert isinstance(z, float)


def test_from_container():
    class TimeDevice(Device):
        days = EntryInfo("Number of days", enforce=int)
    # Create a datetime device
    d = TimeDevice(name='Test', prefix='Tst:This', beamline='TST',
                   device_class='datetime.timedelta', args=list(), days=10,
                   kwargs={'days': '{{days}}', 'seconds': 30})
    td = from_container(d)
    # Now import datetime and check that we constructed ours correctly
    import datetime
    assert td == datetime.timedelta(days=10, seconds=30)
