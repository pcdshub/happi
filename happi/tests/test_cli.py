# test_cli.py

import builtins
import logging
import re
from unittest import mock

import IPython
import pytest
from click.testing import CliRunner

import happi
from happi.cli import happi_cli, search
from happi.errors import SearchError


@pytest.fixture(scope='function')
def happi_cfg(tmp_path, db):
    happi_cfg_path = tmp_path / 'happi.cfg'
    happi_cfg_path.write_text(f"""\
[DEFAULT]'
backend=json
path={db}
""")
    return str(happi_cfg_path.absolute())


@pytest.fixture(scope='function')
def db(tmp_path):
    json_path = tmp_path / 'db.json'
    json_path.write_text("""\
{
    "TST_BASE_PIM": {
        "_id": "TST_BASE_PIM",
        "active": true,
        "args": [
            "{{prefix}}"
        ],
        "beamline": "TST",
        "creation": "Tue Jan 29 09:46:00 2019",
        "device_class": "types.SimpleNamespace",
        "kwargs": {
            "name": "{{name}}"
        },
        "last_edit": "Thu Apr 12 14:40:08 2018",
        "macros": null,
        "name": "tst_base_pim",
        "parent": null,
        "prefix": "TST:BASE:PIM",
        "screen": null,
        "stand": "BAS",
        "system": "diagnostic",
        "type": "OphydItem",
        "z": 3.0
    },
    "TST_BASE_PIM2": {
        "_id": "TST_BASE_PIM2",
        "active": true,
        "args": [
            "{{prefix}}"
        ],
        "beamline": "TST",
        "creation": "Wed Jan 30 09:46:00 2019",
        "device_class": "types.SimpleNamespace",
        "kwargs": {
            "name": "{{name}}"
        },
        "last_edit": "Fri Apr 13 14:40:08 2018",
        "macros": null,
        "name": "tst_base_pim2",
        "parent": null,
        "prefix": "TST:BASE:PIM2",
        "screen": null,
        "stand": "BAS",
        "system": "diagnostic",
        "type": "OphydItem",
        "z": 6.0
    }
}
""")
    return str(json_path.absolute())


@pytest.fixture(scope='function')
def runner():
    return CliRunner()


@pytest.fixture(scope='function')
def client(happi_cfg):
    return happi.client.Client.from_config(cfg=happi_cfg)


def trim_split_output(strings, delim='\n'):
    """
    Trim output of timestamped messages and registry lists.
    Split on delimiter (newline by default)
    """
    date_pattern = r"\[(\d{4})[-](0[1-9]|1[012])[-].*\]"

    bad_substrs = [
        r"^pcdsdevices"
    ]

    # remove registry items
    new_out = [
        st for st in strings.split(delim)
        if not any([re.search(substr, st) for substr in bad_substrs])
    ]

    # string date-time from logging messages
    new_out = [re.sub(date_pattern, '', st) for st in new_out]
    return new_out


def assert_match_expected(result, expected_output):
    """standard checks for a cli result, confirms output matches expected"""
    assert result.exit_code == 0
    assert not result.exception

    trimmed_output = trim_split_output(result.output)
    for message, expected in zip(trimmed_output, expected_output):
        assert message == expected


def test_cli_version(runner):
    result = runner.invoke(happi_cli, ['--version'])
    assert result.exit_code == 0
    assert result.exception is None
    assert happi.__version__ in result.outut
    assert happi.__file__ in result.output


def test_cli_no_argument(runner):
    result = runner.invoke(happi_cli)
    assert result.exit_code == 0
    assert result.exception is None
    assert 'Usage:' in result.output
    assert 'Options:' in result.output
    assert 'Commands:' in result.output


def test_search(client):
    res = client.search_regex(beamline="TST")

    with search.make_context('search', ['beamline=TST'], obj=client) as ctx:
        res_cli = search.invoke(ctx)

    assert [r.device for r in res] == [r.device for r in res_cli]


def test_search_with_name(client, caplog):
    res = client.search_regex(name='TST_BASE_PIM2')

    with search.make_context('search', ['TST_BASE_PIM2'], obj=client) as ctx:
        res_cli = search.invoke(ctx)

    assert [r.device for r in res] == [r.device for r in res_cli]
    # test duplicate search parameters
    with caplog.at_level(logging.ERROR):
        with search.make_context('search', ['TST_BASE_PIM2',
                                 'name=TST_BASE_PIM2'],
                                 obj=client) as ctx:
            res_cli = search.invoke(ctx)

    assert "Received duplicate search criteria" in caplog.text


def test_search_z(client):
    res = client.search_regex(z="6.0")
    with search.make_context('search', ['z=6.0'], obj=client) as ctx:
        res_cli = search.invoke(ctx)

    assert [r.device for r in res] == [r.device for r in res_cli]


def test_search_z_range(client, caplog):
    res = client.search_range('z', 3.0, 6.0)

    with search.make_context('search', ['z=3.0,6.0'], obj=client) as ctx:
        res_cli = search.invoke(ctx)

    assert [r.device for r in res] == [r.device for r in res_cli]
    # test invalid range
    with caplog.at_level(logging.ERROR):
        with search.make_context('search', ['z=6.0,3.0'], obj=client) as ctx:
            res_cli = search.invoke(ctx)

        assert "Invalid range, make sure start < stop" in caplog.text
        caplog.clear()


def test_both_range_and_regex_search(client):
    # we're only interested in getting this entry (TST_BASE_PIM2)
    res = client.search_regex(z='6.0')
    # we're going to search for z=3,7 name=TST_BASE_PIM2
    # we should only get in return one entry, even though the z value found 2
    with search.make_context('search', ['name=TST_BASE_PIM2', 'z=3.0,7.0'],
                             obj=client) as ctx:
        res_cli = search.invoke(ctx)

    assert [r.device for r in res] == [r.device for r in res_cli]


@pytest.mark.parametrize("from_user, expected_output", [
    # Test add item - succeeding
    pytest.param('\n'.join(['HappiItem', 'happi_nname', 'device_class',
                            '', '', 'Y', 'docs', 'y']), (
        'Please select a container, or press enter for generic '
        'Ophyd Device container: ', 'OphydItem', 'HappiItem', '',
        'Selection [OphydItem]: HappiItem',
        'Enter value for name, enforce=is_valid_identifier_not_keyword: '
        'happi_nname',
        'Selecting value: happi_nname',
        'Enter value for device_class, enforce=str [optional]: '
        'device_class',
        'Selecting value: device_class',
        'Enter value for args, enforce=list [[]]: ',
        'Selecting value: []',
        'Enter value for kwargs, enforce=dict',
        'Key must be a string.  Enter a blank key to complete dict entry.',
        '  key: ', 'Selecting value: {}',
        'Enter value for active, enforce=bool [Y/n]: Y',
        'Selecting value: True',
        'Enter value for documentation, enforce=str [optional]: docs',
        'Selecting value: docs',
        'Please confirm the device info is correct [y/N]: y',
        ' - INFO -  Adding device',
        ' - INFO -  Storing device HappiItem (name=happi_nname) ...',
        ' - INFO -  Adding / Modifying information for happi_nname ...',
        ' - INFO -  HappiItem HappiItem (name=happi_nname) has been '
        'succesfully added to the database'),
    ),
    # Test add item - aborting
    pytest.param('\n'.join(['HappiItem', 'happi_name2', 'device_class',
                            '["arg1", "arg2"]', 'name', 'my_name', '',
                            'Y', 'docs', 'N']), (
        'Please select a container, or press enter for generic '
        'Ophyd Device container: ', 'OphydItem', 'HappiItem', '',
        'Selection [OphydItem]: HappiItem',
        'Enter value for name, enforce=is_valid_identifier_not_keyword: '
        'happi_name2',
        'Selecting value: happi_name2',
        'Enter value for device_class, enforce=str [optional]: '
        'device_class',
        'Selecting value: device_class',
        'Enter value for args, enforce=list [[]]: ["arg1", "arg2"]',
        "Selecting value: ['arg1', 'arg2']",
        'Enter value for kwargs, enforce=dict',
        'Key must be a string.  Enter a blank key to complete dict entry.',
        '  key: name', '  value: my_name', '  key: ',
        "Selecting value: {'name': 'my_name'}",
        'Enter value for active, enforce=bool [Y/n]: Y',
        'Selecting value: True',
        'Enter value for documentation, enforce=str [optional]: docs',
        'Selecting value: docs',
        'Please confirm the device info is correct [y/N]: N',
        ' - INFO -  Aborting'),
    ),
    # Test add item - invalid container
    pytest.param('HappiInvalidItem', (
        'Please select a container, or press enter for generic '
        'Ophyd Device container: ', 'OphydItem', 'HappiItem', '',
        'Selection [OphydItem]: HappiInvalidItem',
        ' - INFO -  Invalid device container HappiInvalidItem'),
    ),
    # Test add item - no reponse, not an optional field,
    # invalid value, add OphydItem
    pytest.param('\n'.join(['', '7', 'ophyd_name', 'device_class',
                            "['arg1', 'arg2']", 'name', 'my_name', '',
                            'Y', 'docs', '', 'some_prefix', 'y']), (
        'Please select a container, or press enter for generic '
        'Ophyd Device container: ', 'OphydItem', 'HappiItem', '',
        'Selection [OphydItem]: ',
        'Enter value for name, enforce=is_valid_identifier_not_keyword: 7',
        'Error: 7 is either not a valid Python identifier, or is a '
        'reserved keyword.',
        'Enter value for name, enforce=is_valid_identifier_not_keyword: '
        'ophyd_name',
        'Selecting value: ophyd_name',
        'Enter value for device_class, enforce=str [optional]: device_class',
        'Selecting value: device_class',
        "Enter value for args, enforce=list [['{{prefix}}']]: "
        "['arg1', 'arg2']", "Selecting value: ['arg1', 'arg2']",
        'Enter value for kwargs, enforce=dict',
        'Key must be a string.  Enter a blank key to complete dict entry.',
        '  key: name', '  value: my_name', '  key: ',
        "Selecting value: {'name': 'my_name'}",
        'Enter value for active, enforce=bool [Y/n]: Y',
        'Selecting value: True',
        'Enter value for documentation, enforce=str [optional]: docs',
        'Selecting value: docs',
        'Enter value for prefix, enforce=str: ',
        'Enter value for prefix, enforce=str: some_prefix',
        'Selecting value: some_prefix',
        'Please confirm the device info is correct [y/N]: y',
        ' - INFO -  Adding device',
        ' - INFO -  Storing device OphydItem (name=ophyd_name) ...',
        ' - INFO -  Adding / Modifying information for ophyd_name ...',
        ' - INFO -  HappiItem OphydItem (name=ophyd_name) has been '
        'succesfully added to the database'
         ),
    ),
    ], ids=["add_succeeding", "add_aborting",
            "add_invalid_container", "add_not_optional_field"])
def test_add_cli(from_user, expected_output, caplog, runner, happi_cfg):
    result = runner.invoke(happi_cli, ['--path', happi_cfg, 'add'],
                           input=from_user)
    assert_match_expected(result, expected_output)


@pytest.mark.parametrize("from_user, expected_output", [
    # Test add --clone item - succeeding
    pytest.param('\n'.join(['happi_new_name', 'device_class',
                            "['arg1', 'arg2']", 'name', 'my_name', '',
                            '', '', 'y']), [
        'Enter value for name, enforce=is_valid_identifier_not_keyword '
        '[happi_name]: happi_new_name', 'Selecting value: happi_new_name',
        'Enter value for device_class, enforce=str [device_class]: '
        'device_class', 'Selecting value: device_class',
        "Enter value for args, enforce=list [['arg1', 'arg2']]: "
        "['arg1', 'arg2']", "Selecting value: ['arg1', 'arg2']",
        'Enter value for kwargs, enforce=dict',
        'Key must be a string.  Enter a blank key to complete dict entry.',
        '  key: name', '  value: my_name', '  key: ',
        "Selecting value: {'name': 'my_name'}", 'Enter value for active, '
        'enforce=bool [Y/n]: ', 'Selecting value: True',
        'Enter value for documentation, enforce=str [docs]: ',
        'Selecting value: docs', 'Please confirm the device info is '
        'correct [y/N]: y', ' - INFO -  Adding device',
        ' - INFO -  Storing device HappiItem (name=happi_new_name) ...',
        ' - INFO -  Adding / Modifying information for happi_new_name ...',
        ' - INFO -  HappiItem HappiItem (name=happi_new_name) has been '
        'succesfully added to the database', ''], id="clone_succeeding",
    )])
def test_add_clone(from_user, expected_output, happi_cfg, runner):
    device_info = '\n'.join(['HappiItem', 'happi_name', 'device_class',
                             "['arg1', 'arg2']", 'name', 'my_name', '',
                             'Y', 'docs', 'y'])
    # add device first
    add_result = runner.invoke(happi_cli, ['--path', happi_cfg, 'add'],
                               input=device_info)
    assert add_result.exit_code == 0

    clone_result = runner.invoke(
        happi_cli, ['--path', happi_cfg, 'add', '--clone', 'happi_name'],
        input=from_user)

    assert_match_expected(clone_result, expected_output)


def test_add_clone_device_not_fount(happi_cfg, runner):
    result = runner.invoke(
        happi_cli,
        ['--verbose', '--path', happi_cfg, 'add', '--clone', 'happi_name']
    )
    assert isinstance(result.exception, SearchError)


@pytest.mark.parametrize("from_user, expected_output", [
    # Test edit item name
    pytest.param(['name=new_name'], [
        "Setting happi_name.name = new_name",
        "Saving new entry new_name ...",
        "Removing old entry happi_name ..."], id="edit_name",
    )])
def test_edit(from_user, expected_output, caplog, happi_cfg):
    device_info = ['HappiItem', 'happi_name', 'device_class',
                   ['arg1', 'arg2'], {'name': 'my_name'}, True, 'docs', 'y']
    with mock.patch.object(
            builtins, 'input', lambda x=None: device_info.pop(0)):
        # add device first
        happi.cli.happi_cli(['--verbose', '--path', happi_cfg, 'add'])
    caplog.clear()
    # try edit a previous added device
    happi.cli.happi_cli(
        ['--verbose', '--path', happi_cfg, 'edit',
         'happi_name', from_user.pop(0)])
    for message in caplog.messages:
        for message, expected in zip(caplog.messages, expected_output):
            assert expected in message
    # Test invalid field, note the name is changed to new_name
    with pytest.raises(SystemExit):
        happi.cli.happi_cli(
            ['--verbose', '--path', happi_cfg, 'edit', 'new_name',
             'some_invalid_field=sif'])
    with caplog.at_level(logging.ERROR):
        assert "Could not edit new_name.some_invalid_field: "\
               "'HappiItem' object has no attribute "\
               "'some_invalid_field" in caplog.text


def test_load(caplog, happi_cfg):
    device_info = ['HappiItem', 'happi_name', 'types.SimpleNamespace',
                   [], {'name': 'my_name'}, True, 'docs', 'y']
    with mock.patch.object(
             builtins, 'input', lambda x=None: device_info.pop(0)):
        # add device first
        happi.cli.happi_cli(['--verbose', '--path', happi_cfg, 'add'])
    caplog.clear()
    # try to load the device
    devices = {}
    client = happi.client.Client.from_config(cfg=happi_cfg)
    devices['happi_name'] = client.load_device(name='happi_name')
    with mock.patch.object(IPython, 'start_ipython') as m:
        happi.cli.happi_cli(['--verbose', '--path',
                             happi_cfg, 'load', 'happi_name'])
        m.assert_called_once_with(argv=['--quick'], user_ns=devices)
    with caplog.at_level(logging.INFO):
        assert "Creating shell with devices" in caplog.text


def test_update(happi_cfg):
    new = """[ {
        "_id": "TST_BASE_PIM2",
        "active": true,
        "args": [
            "{{prefix}}"
        ],
        "beamline": "TST",
        "creation": "Wed Jan 30 09:46:00 2019",
        "device_class": "types.SimpleNamespace",
        "kwargs": {
            "name": "{{name}}"
        },
        "last_edit": "Fri Apr 13 14:40:08 2018",
        "macros": null,
        "name": "tst_base_pim2",
        "parent": null,
        "prefix": "TST:BASE:PIM2",
        "screen": null,
        "stand": "BAS",
        "system": "diagnostic",
        "type": "OphydItem",
        "z": 6.0,
        "from_update": true
    } ] """
    happi.cli.happi_cli(["--verbose", "--path", happi_cfg, "update", new])
    #
    client = happi.client.Client.from_config(cfg=happi_cfg)
    item = client.find_device(name="tst_base_pim2")
    assert item["from_update"]


@pytest.mark.parametrize("from_user, expected_output", [
    pytest.param('\n'.join(['n', 'n', 'n', 'n', 'N', 'n', 'n', '']), [
        'Attempting to transfer tst_base_pim to OphydItem...',
        '+---------------+---------------+',
        '|  tst_base_pim |   OphydItem   |',
        '+---------------+---------------+',
        '|     active    |     active    |',
        '|      args     |      args     |',
        '|  device_class |  device_class |',
        '| documentation | documentation |',
        '|     kwargs    |     kwargs    |',
        '|      name     |      name     |',
        '|     prefix    |     prefix    |',
        '|    beamline   |       -       |',
        '|     macros    |       -       |',
        '|     parent    |       -       |',
        '|     screen    |       -       |',
        '|     stand     |       -       |',
        '|     system    |       -       |',
        '|       z       |       -       |',
        '+---------------+---------------+', '',
        '----------Prepare Entries-----------',
        'Include entry from tst_base_pim: beamline = "TST"? [Y/n]: n',
        'Include entry from tst_base_pim: macros = "None"? [Y/n]: n',
        'Include entry from tst_base_pim: parent = "None"? [Y/n]: n',
        'Include entry from tst_base_pim: screen = "None"? [Y/n]: n',
        'Include entry from tst_base_pim: stand = "BAS"? [Y/n]: N',
        'Include entry from tst_base_pim: system = "diagnostic"? [Y/n]: n',
        'Include entry from tst_base_pim: z = "3.0"? [Y/n]: n', '',
        '----------Amend Entries-----------', 'Save final device? [y/N]: ',
        ''], id="transfer_succeeding",
    )])
def test_transfer_cli(from_user, expected_output, happi_cfg, runner):
    results = runner.invoke(happi_cli, ['--path', happi_cfg, 'transfer',
                            'tst_base_pim', 'OphydItem'], input=from_user)
    assert_match_expected(results, expected_output)
