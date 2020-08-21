# test_cli.py

import builtins
import logging
import pytest
import happi
from happi.cli import happi_cli
from unittest import mock


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


def test_cli_version(capsys):
    happi_cli(['--version'])
    readout = capsys.readouterr()
    assert happi.__version__ in readout.out
    assert happi.__file__ in readout.out


def test_cli_no_argument(capsys):
    happi.cli.happi_cli([])
    readout = capsys.readouterr()
    # TODO: figure out a way to get usage: happi
    # instead of usage: pytest or usage run_test.py..
    assert 'usage:' in readout.out
    assert '[-h] [--path PATH] [--verbose] [--version]\n'
    '                    {search,add,edit,load} ...\n' in readout.out


def test_search(happi_cfg):
    client = happi.client.Client.from_config(cfg=happi_cfg)
    res = client.search_regex(beamline="TST")
    res_cli = happi.cli.happi_cli(['--verbose', '--path', happi_cfg, 'search',
                                   'beamline=TST'])
    assert [r.device for r in res] == [r.device for r in res_cli]


def test_search_with_name(happi_cfg, caplog):
    client = happi.client.Client.from_config(cfg=happi_cfg)
    res = client.search_regex(name='TST_BASE_PIM2')
    res_cli = happi.cli.happi_cli(['--verbose', '--path', happi_cfg, 'search',
                                   'TST_BASE_PIM2'])
    assert [r.device for r in res] == [r.device for r in res_cli]
    # test duplicate search parameters
    with caplog.at_level(logging.ERROR):
        res_cli = happi.cli.happi_cli(['--verbose', '--path', happi_cfg,
                                       'search', 'TST_BASE_PIM2',
                                       'name=TST_BASE_PIM2'])
        assert "Received duplicate search criteria" in caplog.text
        caplog.clear()


def test_search_z(happi_cfg):
    client = happi.client.Client.from_config(cfg=happi_cfg)
    res = client.search_regex(z="6.0")
    res_cli = happi.cli.happi_cli(['--verbose', '--path', happi_cfg, 'search',
                                   'z=6.0'])
    assert [r.device for r in res] == [r.device for r in res_cli]


def test_search_z_range(happi_cfg, caplog):
    client = happi.client.Client.from_config(cfg=happi_cfg)
    res = client.search_range('z', 3.0, 6.0)
    res_cli = happi.cli.happi_cli(['--verbose', '--path', happi_cfg, 'search',
                                   'z=3.0,6.0'])
    assert [r.device for r in res] == [r.device for r in res_cli]
    # test invalid range
    with caplog.at_level(logging.ERROR):
        res_cli = happi.cli.happi_cli(['--verbose', '--path', happi_cfg,
                                       'search', 'z=6.0,3.0'])
        assert "Invalid range, make sure start < stop" in caplog.text
        caplog.clear()


def test_both_range_and_regex_search(happi_cfg):
    client = happi.client.Client.from_config(cfg=happi_cfg)
    # we're only interested in getting this entry (TST_BASE_PIM2)
    res = client.search_regex(z='6.0')
    # we're going to search for z=3,7 name=TST_BASE_PIM2
    # we should only get in return one entry, even though the z value found 2
    res_cli = happi.cli.happi_cli(['--verbose', '--path', happi_cfg, 'search',
                                   'name=TST_BASE_PIM2', 'z=3.0,7.0'])
    assert [r.device for r in res] == [r.device for r in res_cli]


@pytest.mark.parametrize("from_user, expected_output", [(
    ['HappiItem', 'happi_name', 'device_class', ['arg1', 'arg2'],
        {'name': 'my_name'}, True, 'docs', 'y'],
    [
        "Please select a container, or press enter for generic "
        "Ophyd Device container",
        "Enter value for name, default=None, "
        "enforce=re.compile('[a-z][a-z\\\\_0-9]{2,78}$')",
        "Enter value for device_class, default=None, enforce=<class 'str'>",
        "Enter value for args, default=[], enforce=<class 'list'>",
        "Enter value for kwargs, default={}, enforce=<class 'dict'>",
        "Enter value for active, default=True, enforce=<class 'bool'>",
        "Enter value for documentation, default=None, enforce=<class 'str'>",
        "Please confirm the following info is correct:",
        "Adding device",
        "Storing device HappiItem (name=happi_name) ...",
        "Adding / Modifying information for happi_name ...",
        "HappiItem HappiItem (name=happi_name) has been "
        "succesfully added to the database"
    ],
    )])
def test_add_cli(from_user, expected_output, caplog, happi_cfg):
    with mock.patch.object(builtins, 'input', lambda x=None: from_user.pop(0)):
        happi.cli.happi_cli(['--verbose', '--path', happi_cfg, 'add'])
        for message, expected in zip(caplog.messages, expected_output):
            assert expected in message


@pytest.mark.parametrize("from_user, expected_output", [(
    ['HappiItem', 'happi_name', 'device_class', ['arg1', 'arg2'],
        {'name': 'my_name'}, True, 'docs', 'N'],
    [
        "Please select a container, or press enter for generic "
        "Ophyd Device container",
        "Enter value for name, default=None, "
        "enforce=re.compile('[a-z][a-z\\\\_0-9]{2,78}$')",
        "Enter value for device_class, default=None, enforce=<class 'str'>",
        "Enter value for args, default=[], enforce=<class 'list'>",
        "Enter value for kwargs, default={}, enforce=<class 'dict'>",
        "Enter value for active, default=True, enforce=<class 'bool'>",
        "Enter value for documentation, default=None, enforce=<class 'str'>",
        "Please confirm the following info is correct:",
        "Aborting"
    ],
    )])
def test_add_cli_aborting(from_user, expected_output, caplog, happi_cfg):
    with mock.patch.object(builtins, 'input', lambda x=None: from_user.pop(0)):
        happi.cli.happi_cli(['--verbose', '--path', happi_cfg, 'add'])
        for message, expected in zip(caplog.messages, expected_output):
            assert expected in message


@pytest.mark.parametrize("from_user, expected_output", [(
    ['HappiInvalidItem'],
    [
        "Please select a container, or press enter for generic "
        "Ophyd Device container",
        "Invalid device container"
    ],
    )])
def test_add_invalid_container(from_user, expected_output, caplog, happi_cfg):
    with mock.patch.object(builtins, 'input', lambda x=None: from_user.pop(0)):
        happi.cli.happi_cli(['--verbose', '--path', happi_cfg, 'add'])
        for message, expected in zip(caplog.messages, expected_output):
            assert expected in message
