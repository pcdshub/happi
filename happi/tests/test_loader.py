from typing import Any

import pytest

from happi import EntryInfo, OphydItem, cache
from happi.item import HappiItem
from happi.loader import fill_template, from_container, load_devices
from happi.utils import create_alias


class TimeDevice(OphydItem):
    days = EntryInfo("Number of days", enforce=int)


def test_fill_template(item: OphydItem):
    # Check that we can properly render a template
    template = "{{name}}"
    assert item.name == fill_template(template, item)
    # Check that we can enforce a type
    template = '{{active}}'
    active = fill_template(template, item, enforce_type=True)
    assert isinstance(active, bool)
    # Check that we will convert a more complex template
    template = '{{name|length()}}'
    text_len = fill_template(template, item, enforce_type=False)
    assert len(item.name) == int(text_len)
    # Check that we can handle non-jinja template
    template = "blah"
    assert template == fill_template(template, item, enforce_type=True)
    # Check that we do not enforce a NoneType
    template = "{{detailed_screen}}"
    assert fill_template(template, item, enforce_type=True) == ""


def test_from_container():
    # Create a datetime item
    d = TimeDevice(name='test', prefix='Tst:This:1', beamline='TST',
                   device_class='datetime.timedelta', args=list(), days=10,
                   kwargs={'days': '{{days}}', 'seconds': 30})
    td = from_container(d)
    # Now import datetime and check that we constructed ours correctly
    import datetime
    assert td == datetime.timedelta(days=10, seconds=30)


def test_caching():
    # Create a datetime item
    d = TimeDevice(name='test', prefix='Tst:This:2', beamline='TST',
                   device_class='types.SimpleNamespace', args=list(), days=10,
                   kwargs={'days': '{{days}}', 'seconds': 30})
    td = from_container(d)
    assert d.name in cache
    assert id(td) == id(from_container(d))
    assert id(td) != id(from_container(d, use_cache=False))
    # Modify md and check we see a reload
    d.days = 12
    assert id(td) != id(from_container(d, use_cache=True))
    # Check with an item where metadata is unavailable
    d = TimeDevice(name='test', prefix='Tst:Delta:3', beamline='TST',
                   device_class='datetime.timedelta', args=list(), days=10,
                   kwargs={'days': '{{days}}', 'seconds': 30})
    td = from_container(d)
    assert id(td) != id(from_container(d))
    assert id(td) != id(from_container(d, use_cache=False))


def test_add_md():
    d = HappiItem(name='test', prefix='Tst:This:3',
                  beamline="TST", args=list(),
                  device_class="happi.HappiItem")
    obj = from_container(d, attach_md=True)
    assert obj.md.extraneous['beamline'] == 'TST'
    assert obj.md.name == 'test'


@pytest.mark.parametrize(
    "threaded",
    [
        pytest.param(False, id="unthreaded"),
        pytest.param(True, id="threaded")
    ],
)
@pytest.mark.parametrize(
    "post_load",
    [
        pytest.param(None, id="no_post_load"),
        pytest.param(lambda x: None, id="post_load"),
    ],
)
@pytest.mark.parametrize(
    "include_load_time",
    [
        pytest.param(False, id="no_load_times"),
        pytest.param(True, id="load_times")
    ],
)
def test_load_devices(threaded: bool, post_load: Any, include_load_time: bool):
    # Create a bunch of devices to load
    devs = [TimeDevice(name='test_1', prefix='Tst1:This', beamline='TST',
                       device_class='datetime.timedelta', args=list(), days=10,
                       kwargs={'days': '{{days}}', 'seconds': 30}),
            TimeDevice(name='test_2', prefix='Tst2:This', beamline='TST',
                       device_class='datetime.timedelta', args=list(), days=10,
                       kwargs={'days': '{{days}}', 'seconds': 30}),
            TimeDevice(name='test_3', prefix='Tst3:This', beamline='TST',
                       device_class='datetime.timedelta', args=list(), days=10,
                       kwargs={'days': '{{days}}', 'seconds': 30}),
            HappiItem(name='bad', prefix='Not:Here', beamline='BAD',
                      device_class='non.existant')]
    # Load our devices
    space = load_devices(
        *devs,
        pprint=True,
        use_cache=False,
        threaded=threaded,
        post_load=post_load,
        include_load_time=include_load_time,
    )
    # Check all our devices are there
    assert all([create_alias(dev.name) in space.__dict__ for dev in devs])
    # Devices were loading properly or exceptions were stored
    import datetime
    assert space.test_1 == datetime.timedelta(days=10, seconds=30)
    assert isinstance(space.bad, ImportError)
