import logging
import os
import re
import tempfile
import types
from typing import Any, Dict

import pytest

from happi import Client, HappiItem, OphydItem
from happi.backends.json_db import JSONBackend
from happi.errors import DuplicateError, EntryError, SearchError, TransferError

logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def xdg_config_home(tmp_path):
    config_home = tmp_path / 'xdg_config_home'
    config_home.mkdir()
    return config_home


@pytest.fixture(scope='function')
def happi_cfg(xdg_config_home):
    # Store current happi config
    xdg_cfg = os.environ.get("XDG_CONFIG_HOME", '')
    happi_cfg = os.environ.get("HAPPI_CFG", '')

    # Setup environment variables
    os.environ['XDG_CONFIG_HOME'] = str(xdg_config_home)
    os.environ['HAPPI_CFG'] = ''

    # Write file
    happi_cfg = xdg_config_home / 'happi.cfg'
    happi_cfg.write_text("""\
[DEFAULT]
backend=json
path=db.json
""")
    yield str(happi_cfg)
    # Restore environment variables
    os.environ["HAPPI_CFG"] = str(happi_cfg)
    os.environ["XDG_CONFIG_HOME"] = xdg_cfg


@pytest.fixture(scope='function')
def happi_cfg_abs(xdg_config_home):
    # Store current happi config
    xdg_cfg = os.environ.get("XDG_CONFIG_HOME", '')
    happi_cfg = os.environ.get("HAPPI_CFG", '')

    # Setup environment variables
    os.environ['XDG_CONFIG_HOME'] = str(xdg_config_home)
    os.environ['HAPPI_CFG'] = ''

    # Write file
    happi_cfg = xdg_config_home / 'happi.cfg'
    happi_cfg.write_text("""\
[DEFAULT]
backend=json
path=/var/run/db.json
""")
    yield str(happi_cfg)
    # Restore environment variables
    os.environ["HAPPI_CFG"] = str(happi_cfg)
    os.environ["XDG_CONFIG_HOME"] = xdg_cfg


def test_find_document(happi_client: Client, item_info: Dict[str, Any]):
    doc = happi_client.find_document(**item_info)
    assert doc.pop('prefix') == item_info['prefix']
    assert doc.pop('name') == item_info['name']
    # Remove id and check
    prefix = item_info.pop('prefix')
    doc = happi_client.find_document(**item_info)

    assert doc.pop('prefix') == prefix
    assert doc.pop('name') == item_info['name']
    # Not available
    with pytest.raises(SearchError):
        doc = happi_client.find_document(prefix='Does not Exist')


def test_create_item(happi_client: Client, item_info: Dict[str, Any]):
    item = happi_client.create_item(OphydItem, **item_info)
    assert item.prefix == item_info['prefix']
    assert item.name == item_info['name']
    # Invalid Entry
    with pytest.raises(TypeError):
        happi_client.create_item(int)


def test_all_items(happi_client: Client, item: OphydItem):
    assert happi_client.all_items == [item]


def test_add_item(happi_client: Client, valve: OphydItem):
    happi_client.add_item(valve)
    # No duplicates
    with pytest.raises(DuplicateError):
        happi_client.add_item(valve)
    # No incompletes
    d = OphydItem()
    with pytest.raises(EntryError):
        happi_client.add_item(d)


def test_add_and_find_item(
    happi_client: Client,
    valve: OphydItem,
    valve_info: Dict[str, Any]
):
    happi_client.add_item(valve)
    loaded_item = happi_client.find_item(**valve_info)
    assert loaded_item.prefix == valve.prefix
    assert loaded_item.name == valve.name


def test_find_item(happi_client: Client, item_info: Dict[str, Any]):
    item = happi_client.find_item(**item_info)
    assert isinstance(item, OphydItem)
    assert item.prefix == item_info['prefix']
    assert item.name == item_info['name']
    # Test edit and save
    item.stand = 'DG3'
    item.save()
    loaded_item = happi_client.find_item(**item_info)
    assert loaded_item.prefix == item_info['prefix']
    assert loaded_item.name == item_info['name']
    # Bad load
    bad = {'a': 'b'}
    happi_client.backend.save('a', bad, insert=True)
    with pytest.raises(EntryError):
        happi_client.find_item(**bad)


def test_change_item_name(happi_client: Client, item_info: Dict[str, Any]):
    item = happi_client.find_item(**item_info)
    assert item.name != 'new_name'
    item.name = 'new_name'
    item.save()
    # old entry should not exist anymore
    with pytest.raises(SearchError):
        happi_client.find_item(**item_info)
    # new entry with new name should be there
    new_item = happi_client.find_item(name=item.name)
    # prefix or other attributes should be the same
    assert new_item.prefix == item.prefix
    # we should only have one deivce now which is the new one
    assert happi_client.all_items == [new_item]


def test_validate(happi_client: Client):
    # No bad items
    assert happi_client.validate() == list()
    # A single bad item
    happi_client.backend.save('_id', {happi_client._id_key: 'bad'},
                              insert=True)
    assert happi_client.validate() == ['bad']


def test_search(
    happi_client: Client,
    valve: OphydItem,
    item_info: Dict[str, Any]
):
    happi_client.add_item(valve)
    res = happi_client.search(name=item_info['name'])
    # Single search return
    assert len(res) == 1
    loaded_item = res[0].item
    assert loaded_item.prefix == item_info['prefix']
    assert loaded_item.name == item_info['name']
    # No results
    assert not happi_client.search(name='not')
    # Returned as dict
    res = happi_client.search(**item_info)
    loaded_item = res[0].item
    assert loaded_item['prefix'] == item_info['prefix']
    assert loaded_item['name'] == item_info['name']
    # Search off keyword
    res = happi_client.search(beamline='LCLS')
    assert len(res) == 2


def test_search_range(happi_client: Client, valve: OphydItem):
    happi_client.add_item(valve)
    # Search between two points
    res = happi_client.search_range('z', start=0, end=500)
    assert len(res) == 2
    # Search between two points, nothing found
    res = happi_client.search_range('z', start=10000, end=500000)
    assert not res
    # Search without an endpoint
    res = happi_client.search_range('z', start=0)
    assert len(res) == 2
    # Search invalid range
    with pytest.raises(ValueError):
        happi_client.search_range('z', start=1000, end=5)


def test_search_regex(
    client_with_three_valves: Client
):
    client = client_with_three_valves

    def find(**kwargs):
        return [
            dict(item) for item in
            client.search_regex(**kwargs, flags=re.IGNORECASE)
        ]

    valve1 = dict(client['VALVE1'])
    valve2 = dict(client['VALVE2'])
    valve3 = dict(client['VALVE3'])

    assert find(beamline='LCLS') == [valve1, valve2, valve3]
    assert find(beamline='lcls') == [valve1, valve2, valve3]
    assert find(beamline='nomatch') == []
    assert find(_id=r'VALVE\d') == [valve1, valve2, valve3]
    assert find(_id='VALVE[13]') == [valve1, valve3]
    assert find(prefix='BASE:VGC[23]:PV') == [valve2, valve3]


def test_get_by_id(
    happi_client: Client,
    valve: OphydItem,
    valve_info: Dict[str, Any]
):
    happi_client.add_item(valve)
    name = valve_info['name']
    for k, v in valve_info.items():
        assert happi_client[name][k] == valve_info[k]


def test_remove_item(
    happi_client: Client,
    item: OphydItem,
    valve: OphydItem,
    item_info: Dict[str, Any]
):
    happi_client.remove_item(item)
    assert list(happi_client.backend.find(item_info)) == []
    # Invalid item
    with pytest.raises(ValueError):
        happi_client.remove_item(5)
    # Valve not in dictionary
    with pytest.raises(SearchError):
        happi_client.remove_item(valve)


def test_export(happi_client: Client, valve: OphydItem):
    # Setup client with both items
    happi_client.add_item(valve)
    fd, temp_path = tempfile.mkstemp()
    happi_client.export(open(temp_path, 'w+'),
                        sep=',',
                        attrs=['name', 'prefix'])
    exp = open(temp_path, 'r').read()
    assert "alias,BASE:PV" in exp
    assert "name,BASE:VGC:PV" in exp
    # Cleanup
    os.remove(temp_path)
    os.close(fd)


def test_load_device(happi_client: Client, item: OphydItem):
    device = happi_client.load_device(name=item.name)
    assert isinstance(device, types.SimpleNamespace)
    assert device.hi == 'oh hello'


@pytest.mark.parametrize(
    'item, target',
    [
        ('item2_dev', 'Item1'),
        ('item1_dev', 'Item2'),
        ('valve', 'Item1')
    ],
)
def test_change_container_fail(
    happi_client: Client,
    item: str,
    target: str,
    request: pytest.FixtureRequest
):
    i = request.getfixturevalue(item)
    t = request.getfixturevalue(target)
    with pytest.raises(TransferError):
        happi_client.change_container(i, t)


def test_change_fail_mandatory(happi_client: Client, item2_dev: HappiItem):
    with pytest.raises(TransferError):
        happi_client.change_container(item2_dev, OphydItem)


@pytest.mark.parametrize(
    'item, target', [('item1_dev', 'Item1'), ('item2_dev', 'Item2')],
)
def test_change_container_pass(
    happi_client: Client,
    item: str,
    target: str,
    request: pytest.FixtureRequest
):
    i = request.getfixturevalue(item)
    t = request.getfixturevalue(target)
    kw = happi_client.change_container(i, t)

    for k in kw:
        assert i.post()[k] == kw[k]


def test_find_cfg(happi_cfg: str):
    # Use our config directory
    assert happi_cfg == Client.find_config()
    # Set the path explicitly using HAPPI env variable
    os.environ['HAPPI_CFG'] = happi_cfg
    assert happi_cfg == Client.find_config()


def test_from_cfg(happi_cfg: str):
    # happi_cfg modifies environment variables to make config discoverable
    client = Client.from_config()
    # Internal db path should be constructed relative to the happi cfg dir
    expected_db = os.path.abspath(os.path.join(os.path.dirname(happi_cfg), 'db.json'))
    print(happi_cfg)
    assert isinstance(client.backend, JSONBackend)
    assert client.backend.path == expected_db


def test_from_cfg_abs(happi_cfg_abs: str):
    # happi_cfg modifies environment variables to make config discoverable
    client = Client.from_config()
    assert isinstance(client.backend, JSONBackend)
    # Ensure the json backend is using the db that we gave an absolute path to.
    assert client.backend.path == '/var/run/db.json'


def test_choices_for_field(happi_client: Client):
    name_choices = happi_client.choices_for_field('name')
    assert name_choices == {'alias'}
    prefix_choices = happi_client.choices_for_field('prefix')
    assert prefix_choices == {'BASE:PV'}
    with pytest.raises(SearchError):
        happi_client.choices_for_field('not_a_field')


def test_searchresults(client_with_three_valves: Client):
    valve1 = client_with_three_valves['VALVE1']
    assert valve1['name'] == 'valve1'
    assert valve1['type'] == 'OphydItem'
    assert valve1['z'] == 300
    assert isinstance(valve1.get(), types.SimpleNamespace)


def test_hashable_searchresults(client_with_three_valves: Client):
    client = client_with_three_valves
    valve1 = client['VALVE1']
    valve2 = client['VALVE2']
    valve3 = client['VALVE3']
    results1 = set(client.search_regex(name='valve1|valve2'))
    results2 = set(client.search_regex(name='valve.*'))

    assert valve1 != 'VALVE1'
    assert valve1 != valve1.metadata

    assert len(results1 & results2) == 2
    assert valve1 in (results1 & results2)
    assert valve2 in (results1 & results2)
    assert len(results1 ^ results2) == 1
    assert valve3 in (results1 ^ results2)
    assert valve2 not in (results1 ^ results2)
    assert results2 == (results1 | results2)


def test_client_mapping(
    client_with_three_valves: Client,
    three_valves: Dict[str, Dict[str, Any]]
):
    client = client_with_three_valves
    assert len(client) == 3
    assert list(dict(client)) == list(three_valves.keys())
    for name in client:
        assert client[name]['name']


def test_cache_context(monkeypatch, client_with_three_valves: Client):
    client = client_with_three_valves
    valve1 = client['VALVE1']
    valve2 = client['VALVE2']
    valve3 = client['VALVE3']

    cache_clear_count = 0
    orig_clear_cache = client.backend.clear_cache

    def clear_cache():
        nonlocal cache_clear_count
        cache_clear_count += 1
        return orig_clear_cache()

    monkeypatch.setattr(client.backend, "clear_cache", clear_cache)
    with client.retain_cache_context():
        results1 = set(client.search_regex(name='valve1|valve2'))
        results2 = set(client.search_regex(name='valve.*'))

    assert cache_clear_count == 1

    assert valve1 != 'VALVE1'
    assert valve1 != valve1.metadata

    assert len(results1 & results2) == 2
    assert valve1 in (results1 & results2)
    assert valve2 in (results1 & results2)
    assert len(results1 ^ results2) == 1
    assert valve3 in (results1 ^ results2)
    assert valve2 not in (results1 ^ results2)
    assert results2 == (results1 | results2)
