# test_cli.py

import functools
import itertools
import logging
import re
from collections.abc import Iterable
from typing import Any
from unittest import mock

import click
import IPython
import pytest
from click.testing import CliRunner

import happi
from happi.cli import happi_cli, search
from happi.errors import SearchError

try:
    import pcdsutils.profile
    if pcdsutils.profile.has_line_profiler:
        test_line_prof = True
    else:
        test_line_prof = False
except ImportError:
    test_line_prof = False


logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def client(happi_cfg: str):
    return happi.client.Client.from_config(cfg=happi_cfg)


def trim_split_output(strings: str, delim: str = '\n'):
    """
    Trim output of timestamped messages and registry lists.
    Split on delimiter (newline by default)
    """
    date_pattern = r"\[(\d{4})[-](0[1-9]|1[012])[-].*\]"

    omit_substrs = [r"happi.containers.", r"- DEBUG -"]

    # remove registry items
    new_out = strings.split(delim)

    # strip registry items from outside entrypoints?
    new_out = [st for st in new_out
               if not any([re.search(substr, st) for substr in omit_substrs])]
    # strip date-time from logging messages
    new_out = [re.sub(date_pattern, '', st) for st in new_out]
    return new_out


def assert_match_expected(
    result: click.testing.Result,
    expected_output: Iterable[str],
    expected_return: int = 0,
    raise_failures: bool = False
):
    """
    standard checks for a cli result, confirms output matches expected
    SystemExit exception is acceptable if the expected return code is some failure code
    """
    logger.debug(result.output)
    assert result.exit_code == expected_return
    assert not result.exception or (isinstance(result.exception, SystemExit) and
                                    expected_return != 0)

    trimmed_output = trim_split_output(result.output)
    for message, expected in zip(trimmed_output, expected_output):
        if raise_failures:
            assert message == expected
        else:
            if not message == expected:
                print('Output does not match expected value:\n'
                      f'- Output: {message}\n- Expected: {expected}')


def assert_in_expected(
    result: click.testing.Result,
    expected_inclusion: str,
    expected_return: int = 0
):
    """
    standard checks for a cli result, confirms output matches expected
    SystemExit exception is acceptable if the expected return code is some failure code
    """
    logger.debug(result.output)
    assert result.exit_code == expected_return
    assert not result.exception or (isinstance(
        result.exception, SystemExit) and expected_return != 0)
    assert expected_inclusion in result.output


def test_cli_no_argument(runner: CliRunner):
    result = runner.invoke(happi_cli)
    # click >= 8.2.0 returns 2, not 0.
    # Non-0 with no args the case in other cli's (git), even if help text is shown
    # to support older versions of click we'll just skip the exit code check
    assert 'Usage:' in result.output
    assert 'Options:' in result.output
    assert 'Commands:' in result.output


def test_repair_name(runner: CliRunner, bad_happi_cfg: str):
    search_string = '_id=tst_id'

    # make sure the name and id are different
    with search.make_context('search', [search_string], obj=bad_happi_cfg) as ctx:
        res = search.invoke(ctx)
    assert all([r['_id'] != r['name'] for r in res])

    # run repair
    runner.invoke(happi_cli, ['--path', bad_happi_cfg, 'repair', search_string])

    # make sure the name and id are the same
    with search.make_context('search', [search_string], obj=bad_happi_cfg) as ctx:
        res = search.invoke(ctx)
    assert all([r['_id'] == r['name'] for r in res])


def test_repair_no_save_if_no_changes(runner: CliRunner, happi_cfg: str):
    # some arbitrary entry
    search_string = '_id=tst_base_pim'

    # get last edit time of item, so can make sure it isn't changed by repair
    with search.make_context('search', [search_string], obj=happi_cfg) as ctx:
        res = search.invoke(ctx)
    pre_repair_edit_time = res[0]['last_edit']

    # run repair, which should find it doesn't need to repair the item's name and so doesn't need to save
    runner.invoke(happi_cli, ['--path', happi_cfg, 'repair', search_string])

    with search.make_context('search', [search_string], obj=happi_cfg) as ctx:
        res = search.invoke(ctx)
    after_repair_edit_time = res[0]['last_edit']

    # should not have saved, so edit time should be unchanged
    assert after_repair_edit_time == pre_repair_edit_time


def test_search(client: happi.client.Client, happi_cfg: str):
    res = client.search_regex(beamline="TST")

    with search.make_context('search', ['beamline=TST'], obj=happi_cfg) as ctx:
        res_cli = search.invoke(ctx)

    assert [r.item for r in res] == [r.item for r in res_cli]


def test_search_with_name(
    client: happi.client.Client,
    runner: CliRunner,
    happi_cfg: str
):
    res = client.search_regex(name='TST_BASE_PIM2')

    with search.make_context('search', ['TST_BASE_PIM2'], obj=happi_cfg) as ctx:
        res_cli = search.invoke(ctx)

    assert [r.item for r in res] == [r.item for r in res_cli]
    # test duplicate search parameters
    bad_result = runner.invoke(happi_cli, ['--path', happi_cfg,
                                           'search', 'TST_BASE_PIM2',
                                           'name=TST_BASE_PIM2'])

    assert bad_result.exit_code == 1
    assert 'duplicate search criteria' in bad_result.output


def test_search_glob_regex(runner: CliRunner, happi_cfg: str):
    glob_result = runner.invoke(happi_cli, ['--path', happi_cfg, 'search',
                                '--names', 'tst_*2'])

    regex_result = runner.invoke(happi_cli, ['--path', happi_cfg, 'search',
                                 '--names', '--regex', r'tst_.*\d'])

    assert glob_result.output == regex_result.output


def test_search_z(happi_cfg: str, client: happi.client.Client):
    res = client.search_regex(z="6.0")
    with search.make_context('search', ['z=6.0'], obj=happi_cfg) as ctx:
        res_cli = search.invoke(ctx)

    assert [r.item for r in res] == [r.item for r in res_cli]


def test_search_z_range(
    client: happi.client.Client,
    runner: CliRunner,
    happi_cfg: str
):
    res = client.search_range('z', 3.0, 6.0)

    with search.make_context('search', ['z=3.0,6.0'], obj=happi_cfg) as ctx:
        res_cli = search.invoke(ctx)

    assert [r.item for r in res] == [r.item for r in res_cli]

    # test range intersection
    result = runner.invoke(happi_cli, ['--path', happi_cfg, 'search',
                           '--names', 'z=3.0,6.1', 'y=9.0,12.0'])

    assert result.exit_code == 0
    assert result.output == 'tst_base_pim2\n'

    # test invalid range
    bad_result = runner.invoke(happi_cli, ['--path', happi_cfg,
                               'search', 'z=6.0,3.0'])

    assert bad_result.exit_code == 1
    assert "Invalid range, make sure start < stop" in bad_result.output

    # test conflicting ranges (should return no items)
    conflict_result = runner.invoke(happi_cli, ['--path', happi_cfg,
                                    'search', 'y=1,3', 'z=3.0,6.0'])

    assert conflict_result.exit_code == 0
    assert 'No items found' in conflict_result.output

    # test conflicting ranges but with opposite order
    conflict_result = runner.invoke(happi_cli, ['--path', happi_cfg,
                                    'search', 'z=3.0,6.0', 'y=1,3'])

    assert conflict_result.exit_code == 0
    assert 'No items found' in conflict_result.output


def test_search_int_float(runner: CliRunner, happi_cfg: str):
    int_result = runner.invoke(happi_cli, ['--path', happi_cfg,
                               'search', '--names', 'z=3'])
    float_result = runner.invoke(happi_cli, ['--path', happi_cfg,
                                 'search', '--names', 'z=3.0'])
    assert int_result.output == float_result.output

    # # TODO: add this test case once edit works on extraneous info
    # edit_result = runner.invoke(
    #     happi_cli,
    #     ['-v', '--path', happi_cfg, 'edit', 'tst_base_pim', 'z=3.001'],
    #     input='y'
    # )
    # assert edit_result.exit_code == 0

    # int_result = runner.invoke(happi_cli, ['--path', happi_cfg,
    #                            'search', '--names', 'z=3'])
    # float_result = runner.invoke(happi_cli, ['--path', happi_cfg,
    #                              'search', '--names', 'z=3.0'])
    # assert int_result.output == ''
    # assert float_result.output == ''


def test_both_range_and_regex_search(happi_cfg: str, client: happi.client.Client):
    # we're only interested in getting this entry (TST_BASE_PIM2)
    res = client.search_regex(z='6.0')
    # we're going to search for z=3,7 name=TST_BASE_PIM2
    # we should only get in return one entry, even though the z value found 2
    with search.make_context('search', ['name=TST_BASE_PIM2', 'z=3.0,7.0'],
                             obj=happi_cfg) as ctx:
        res_cli = search.invoke(ctx)

    assert [r.item for r in res] == [r.item for r in res_cli]


def test_search_json(runner: CliRunner, happi_cfg: str):
    expected_output = '''[
  {
    "name": "tst_base_pim2",
    "device_class": "types.SimpleNamespace",
    "args": [],
    "kwargs": {
      "name": "{{name}}"
    },
    "active": true,
    "documentation": null,
    "_id": "tst_base_pim2",
    "beamline": "TST",
    "creation": "Wed Jan 30 09:46:00 2019",
    "last_edit": "Fri Apr 13 14:40:08 2018",
    "macros": null,
    "parent": null,
    "prefix": "TST:BASE:PIM2",
    "screen": null,
    "stand": "BAS",
    "system": "diagnostic",
    "type": "HappiItem",
    "z": 6.0,
    "y": 10.0
  }
]'''

    result = runner.invoke(
        happi_cli, ['--path', happi_cfg, 'search', '-j', 'TST_BASE_PIM2']
    )

    assert result.exit_code == 0
    assert_match_expected(result, expected_output.split('\n'), raise_failures=True)


@pytest.mark.parametrize("from_user, expected_output, expected_return", [
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
        'Please confirm the item info is correct [y/N]: y',
        ' - INFO -  Adding item',
        ' - INFO -  Storing item HappiItem (name=happi_nname) ...',
        ' - INFO -  Adding / Modifying information for happi_nname ...',
        ' - INFO -  HappiItem HappiItem (name=happi_nname) has been '
        'succesfully added to the database'),
        0
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
        'Please confirm the item info is correct [y/N]: N',
        ' - INFO -  Aborting'),
        0
    ),
    # Test add item - invalid container
    pytest.param('HappiInvalidItem', (
        'Please select a container, or press enter for generic '
        'Ophyd Device container: ', 'OphydItem', 'HappiItem', '',
        'Selection [OphydItem]: HappiInvalidItem',
        'Error: Invalid item container HappiInvalidItem'),
        1
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
        'Please confirm the item info is correct [y/N]: y',
        ' - INFO -  Adding item',
        ' - INFO -  Storing item OphydItem (name=ophyd_name) ...',
        ' - INFO -  Adding / Modifying information for ophyd_name ...',
        ' - INFO -  HappiItem OphydItem (name=ophyd_name) has been '
        'succesfully added to the database'),
        0
    )
], ids=["add_succeeding", "add_aborting",
        "add_invalid_container", "add_not_optional_field"])
def test_add_cli(
    from_user: str,
    expected_output: tuple[str, ...],
    expected_return: int,
    happi_cfg: str,
    runner: CliRunner
):
    result = runner.invoke(happi_cli, ['--path', happi_cfg, 'add'],
                           input=from_user)
    assert_match_expected(result, expected_output, expected_return)
    # check this has been added
    dev_name = from_user[1]
    if '_' not in dev_name:  # special case for errored
        return
    client = happi.client.Client.from_config(cfg=happi_cfg)
    item = client.find_item(name=dev_name)
    assert item["_id"]


def test_delete_cli(
    happi_cfg: str,
    runner: CliRunner
):
    delete_result = runner.invoke(
        happi_cli,
        ['--path', happi_cfg, 'delete', 'tst_base_pim'],
        input='y\n'
    )
    assert delete_result.exit_code == 0

    # confirm item is gone
    search_result = runner.invoke(
        happi_cli, ['--path', happi_cfg, 'search', 'tst_base_pim']
    )
    assert_in_expected(search_result, 'No items found', 0)


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
        'Selecting value: docs', 'Please confirm the item info is '
        'correct [y/N]: y', ' - INFO -  Adding item',
        ' - INFO -  Storing item HappiItem (name=happi_new_name) ...',
        ' - INFO -  Adding / Modifying information for happi_new_name ...',
        ' - INFO -  HappiItem HappiItem (name=happi_new_name) has been '
        'succesfully added to the database', ''], id="clone_succeeding",
    )])
def test_add_clone(
    from_user: str,
    expected_output: tuple[str, ...],
    happi_cfg: str,
    runner: CliRunner
):
    item_info = "\n".join(
        [
            "HappiItem",
            "happi_name",
            "device_class",
            "['arg1', 'arg2']",
            "name",
            "my_name",
            "",
            "Y",
            "docs",
            "y",
        ]
    )
    # add item first
    add_result = runner.invoke(happi_cli, ['--path', happi_cfg, 'add'],
                               input=item_info)
    assert add_result.exit_code == 0

    clone_result = runner.invoke(
        happi_cli, ['--path', happi_cfg, 'add', '--clone', 'happi_name'],
        input=from_user)

    assert_match_expected(clone_result, expected_output)
    client = happi.client.Client.from_config(cfg=happi_cfg)
    item = client.find_item(name="happi_new_name")
    assert item["type"] == 'HappiItem'
    assert item["device_class"] == 'device_class'


def test_add_clone_item_not_found(happi_cfg: str, runner: CliRunner):
    result = runner.invoke(
        happi_cli,
        ['--verbose', '--path', happi_cfg, 'add', '--clone', 'happi_name']
    )
    assert isinstance(result.exception, SearchError)


@pytest.mark.parametrize("from_user, fields, values", [
    # simple edit
    (["documentation=new_docs"], ['documentation'], ['new_docs']),
    # edit kwargs with dictionary
    (["kwargs={\'name\':\'fart\'}"], ['kwargs'], [{'name': 'fart'}]),
    # edit argument list
    (['args=[1,2,3,4]'], ['args'], [[1, 2, 3, 4]]),
    # change multiple entries
    (["active=False", "documentation=yes"], ['active', 'documentation'],
     [False, 'yes'])
])
def test_edit(
    from_user: list[str],
    fields: list[str],
    values: list[Any],
    client: happi.client.Client,
    happi_cfg: str,
    runner: CliRunner
):
    item_info = "\n".join(
        [
            "HappiItem",
            "happi_name",
            "device_class",
            "['arg1', 'arg2']",
            "name",
            "my_name",
            "",
            "Y",
            "docs",
            "y",
        ]
    )
    # add item first
    add_result = runner.invoke(
        happi_cli,
        ['--verbose', '--path', happi_cfg, 'add'],
        input=item_info
    )
    assert add_result.exit_code == 0

    # try edit the previous added item
    edit_result = runner.invoke(
        happi_cli,
        ['--path', happi_cfg, 'edit', 'happi_name', *from_user],
        input='y'  # to confirm edit
    )
    assert edit_result.exit_code == 0

    res = client.search_regex(name='happi_name')
    assert len(res) > 0
    # check fields and values have been modifiedj
    # verify fields match expected python types
    for new_field, new_value in zip(fields, values):
        assert getattr(res[0].item, new_field) == new_value


@pytest.mark.parametrize("edit_args", [
    ["some_invalid_field=sif"],  # invalid field
    ["name=2"],  # bad value for name
    ["kwargs={\'str\':\'beh\'}"],  # bad key in kwarg
])
def test_bad_edit(edit_args: list[str], happi_cfg: str, runner: CliRunner):
    # Test invalid field, note the name is changed to new_name
    bad_edit_result = runner.invoke(
        happi_cli,
        ['--path', happi_cfg, 'edit', 'TST_BASE_PIM', *edit_args]
    )
    assert bad_edit_result.exit_code == 1


def test_load_one_arg(
    caplog: pytest.LogCaptureFixture,
    client: happi.client.Client,
    happi_cfg: str,
    runner: CliRunner
):
    item_info = "\n".join(
        [
            "HappiItem",
            "happi_name",
            "types.SimpleNamespace",
            "",
            "name",
            "my_name",
            "",
            "y",
            "docs",
            "y",
        ]
    )
    # add item first
    add_result = runner.invoke(happi_cli, ['--path', happi_cfg, 'add'],
                               input=item_info)
    assert add_result.exit_code == 0

    # try to load the item
    devices = {}
    devices['happi_name'] = client.load_device(name='happi_name')
    with mock.patch.object(IPython, 'start_ipython') as m:
        _ = runner.invoke(
            happi_cli, ['--path', happi_cfg, 'load', 'happi_name']
        )
        m.assert_called_once_with(argv=['--quick'], user_ns=devices)
    with caplog.at_level(logging.INFO):
        assert "Creating shell with devices" in caplog.text


def test_load_multiple_args(
    caplog: pytest.LogCaptureFixture,
    client: happi.client.Client,
    happi_cfg: str,
    runner: CliRunner
):
    # try to load the item
    devices = {}
    devices['tst_base_pim'] = client.load_device(name='tst_base_pim')
    devices['tst_base_pim2'] = client.load_device(name='tst_base_pim2')
    with mock.patch.object(IPython, 'start_ipython') as m:
        _ = runner.invoke(
            happi_cli, ['--path', happi_cfg, 'load', 'tst_base_pim', 'tst_base_pim2']
        )
        m.assert_called_once_with(argv=['--quick'], user_ns=devices)
    with caplog.at_level(logging.INFO):
        assert "Creating shell with devices" in caplog.text


def test_load_glob_one_arg(
    caplog: pytest.LogCaptureFixture,
    client: happi.client.Client,
    happi_cfg: str,
    runner: CliRunner
):
    # try to load the item
    devices = {}
    devices['tst_base_pim'] = client.load_device(name='tst_base_pim')
    devices['tst_base_pim2'] = client.load_device(name='tst_base_pim2')
    devices['tst_minimal'] = client.load_device(name='tst_minimal')

    with mock.patch.object(IPython, 'start_ipython') as m:
        _ = runner.invoke(
            happi_cli, ['--path', happi_cfg, 'load', 'tst_*']
        )
        m.assert_called_once_with(argv=['--quick'], user_ns=devices)

    with caplog.at_level(logging.INFO):
        assert "Creating shell with devices" in caplog.text


def test_load_glob_multiple_args(
    caplog: pytest.LogCaptureFixture,
    client: happi.client.Client,
    happi_cfg: str,
    runner: CliRunner
):
    # try to load the item
    devices = {}
    devices['tst_base_pim'] = client.load_device(name='tst_base_pim')
    devices['tst_base_pim2'] = client.load_device(name='tst_base_pim2')
    devices['tst_minimal'] = client.load_device(name='tst_minimal')

    with mock.patch.object(IPython, 'start_ipython') as m:
        _ = runner.invoke(
            happi_cli, ['--path', happi_cfg, 'load', 'tst_*', 'device_class=types*']
        )
        m.assert_called_once_with(argv=['--quick'], user_ns=devices)

    with caplog.at_level(logging.INFO):
        assert "Creating shell with devices" in caplog.text


@pytest.mark.parametrize("wrapper", ['{{ "tst_base_pim2":{} }}', "[{}]"])
def test_update(wrapper: str, happi_cfg: str, runner: CliRunner):
    new = """{
        "_id": "tst_base_pim2",
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
    }"""

    payload = wrapper.format(new)

    result = runner.invoke(happi_cli, ["--path", happi_cfg, "update", payload])
    assert result.exit_code == 0
    client = happi.client.Client.from_config(cfg=happi_cfg)
    item = client.find_item(name="tst_base_pim2")
    assert item["from_update"]


@pytest.mark.parametrize("wrapper", ['{{ "tst_base_pim2":{} }}', "[{}]"])
def test_update_stdin(wrapper: str, happi_cfg: str, runner: CliRunner):
    new = """{
        "_id": "tst_base_pim2",
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
    }"""

    payload = wrapper.format(new)

    result = runner.invoke(happi_cli, ["--path", happi_cfg, "update", "-"],
                           input=payload)
    assert result.exit_code == 0
    client = happi.client.Client.from_config(cfg=happi_cfg)
    item = client.find_item(name="tst_base_pim2")
    assert item["from_update"]


@pytest.mark.parametrize("from_user, expected_output", [
    pytest.param('\n'.join(['n', 'n', 'n', 'n', 'N', 'n', 'n', 'n', 'y']), [
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
        '|       y       |       -       |',
        '|       z       |       -       |',
        '+---------------+---------------+', '',
        '----------Prepare Entries-----------',
        'Include entry from tst_base_pim: beamline = "TST"? [Y/n]: n',
        'Include entry from tst_base_pim: macros = "None"? [Y/n]: n',
        'Include entry from tst_base_pim: parent = "None"? [Y/n]: n',
        'Include entry from tst_base_pim: screen = "None"? [Y/n]: n',
        'Include entry from tst_base_pim: stand = "BAS"? [Y/n]: N',
        'Include entry from tst_base_pim: system = "diagnostic"? [Y/n]: n',
        'Include entry from tst_base_pim: y = "40.0"? [Y/n]: n',
        'Include entry from tst_base_pim: z = "3.0"? [Y/n]: n', '',
        '----------Amend Entries-----------', 'Save final item? [y/N]: y',
        ' - INFO -  Attempting to remove OphydItem (name=tst_base_pim) from the collection ...',
        ' - INFO -  Storing item OphydItem (name=tst_base_pim) ...',
        ' - INFO -  Adding / Modifying information for tst_base_pim ...',
        ' - INFO -  HappiItem OphydItem (name=tst_base_pim) has been succesfully added to the database',
        ''], id="transfer_succeeding",
    )])
def test_transfer_cli(
    from_user: str,
    expected_output: list[str],
    happi_cfg: str,
    runner: CliRunner
):
    results = runner.invoke(happi_cli, ['--path', happi_cfg, 'transfer',
                            'tst_base_pim', 'OphydItem'], input=from_user)
    assert_match_expected(results, expected_output)
    client = happi.client.Client.from_config(cfg=happi_cfg)
    item = client.find_item(name="tst_base_pim")
    assert item["type"] == 'OphydItem'
    assert getattr(item, 'parent', 'DNE') == 'DNE'


@pytest.mark.parametrize("from_user, expected_output", [
    pytest.param('\n'.join(['MY:PREFIX', 'y']), [
        'Attempting to transfer tst_minimal to OphydItem...',
        '+---------------+---------------+',
        '|  tst_minimal  |   OphydItem   |',
        '+---------------+---------------+',
        '|     active    |     active    |',
        '|      args     |      args     |',
        '|  device_class |  device_class |',
        '| documentation | documentation |',
        '|     kwargs    |     kwargs    |',
        '|      name     |      name     |',
        '|       -       |     prefix    |',
        '+---------------+---------------+',
        '',
        '----------Prepare Entries-----------',
        'Enter value for prefix, enforce=str: MY:PREFIX',
        '',
        '----------Amend Entries-----------',
        'Save final item? [y/N]: y',
        ' - INFO -  Attempting to remove OphydItem (name=tst_minimal) from the collection ...',
        ' - INFO -  Storing item OphydItem (name=tst_minimal) ...',
        ' - INFO -  Adding / Modifying information for tst_minimal ...',
        ' - INFO -  HappiItem OphydItem (name=tst_minimal) has been succesfully added to the database',
        ''], id="transfer_succeeding",
    )])
def test_transfer_cli_more(
    from_user: str,
    expected_output: list[str],
    happi_cfg: str,
    runner: CliRunner
):
    results = runner.invoke(happi_cli, ['--path', happi_cfg, 'transfer',
                            'tst_minimal', 'OphydItem'], input=from_user)
    assert_match_expected(results, expected_output)
    client = happi.client.Client.from_config(cfg=happi_cfg)
    item = client.find_item(name="tst_minimal")
    assert item["type"] == 'OphydItem'
    assert item["prefix"] == 'MY:PREFIX'


def arg_variants(variants: tuple[tuple[tuple[str]]]):
    """
    Collapse argument variants into all possible combinations.
    """
    for idx, arg_set in enumerate(itertools.product(*variants), 1):
        item = functools.reduce(
            lambda x, y: x + y,
            arg_set,
        )
        summary = f"args{idx}_" + ",".join(item)
        yield pytest.param(item, id=summary)


benchmark_arg_variants = (
    (('--duration', '0.1'), ('--iterations', '5')),
    (('--wait-connected',), ()),
    (('--tracebacks',), ()),
    (('--sort-key', 'name'), ()),
    (('--glob', '*pim'), ('--regex', '.*pim'), ()),
)


@pytest.mark.parametrize(
    "args", tuple(arg_variants(benchmark_arg_variants))
)
def test_benchmark_cli(runner: CliRunner, happi_cfg: str, args: tuple[str]):
    # Make sure the benchmark can complete in some form with valid inputs
    if "--iterations" not in args:
        # Keep the number of overall iterations reasonable
        args = (*args, "--iterations", "100")

    result = runner.invoke(
        happi_cli,
        ['--path', happi_cfg, 'benchmark'] + list(args),
    )
    assert_in_expected(
        result,
        'Benchmark completed successfully'
    )


profile_arg_variants = (
    (('--database',), ('--import',), ('--object', ),
     ('--all', ), ('--import', '--object')),
    (('--profiler', 'pcdsutils'), ('--profiler', 'cprofile'), ()),
    (('--glob', '*pim'), ('--regex', '.*pim'), ()),
)


@pytest.mark.parametrize(
    "args", tuple(arg_variants(profile_arg_variants))
)
def test_profile_cli(runner: CliRunner, happi_cfg: str, args: tuple[str]):
    # Make sure the profile can complete in some form with valid inputs
    if "pcdsutils" in args:
        if not test_line_prof:
            pytest.skip("Missing pcdsutils or line_profiler.")

    if test_line_prof:
        print("Resetting the line profiler...")
        pcdsutils.profile.reset_profiler()

    result = runner.invoke(
        happi_cli,
        ['--path', happi_cfg, 'profile'] + list(args),
    )

    assert_in_expected(
        result,
        'Profile completed successfully'
    )
