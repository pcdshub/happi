# test_cli.py

import functools
import itertools
import logging
import re
from typing import Any, Iterable, List, Tuple
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
        "z": 3.0,
        "y": 40.0
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
        "z": 6.0,
        "y": 10.0
    }
}
""")
    return str(json_path.absolute())


@pytest.fixture(scope='function')
def client(happi_cfg: str):
    return happi.client.Client.from_config(cfg=happi_cfg)


def trim_split_output(strings: str, delim: str = '\n'):
    """
    Trim output of timestamped messages and registry lists.
    Split on delimiter (newline by default)
    """
    date_pattern = r"\[(\d{4})[-](0[1-9]|1[012])[-].*\]"

    bad_substrs = [r"^pcdsdevices"]

    # remove registry items
    new_out = [
        st for st in strings.split(delim)
        if not any([re.search(substr, st) for substr in bad_substrs])
    ]

    # string date-time from logging messages
    new_out = [re.sub(date_pattern, '', st) for st in new_out]
    return new_out


def assert_match_expected(
    result: click.testing.Result,
    expected_output: Iterable[str]
):
    """standard checks for a cli result, confirms output matches expected"""
    logger.debug(result.output)
    assert result.exit_code == 0
    assert not result.exception

    trimmed_output = trim_split_output(result.output)
    for message, expected in zip(trimmed_output, expected_output):
        assert message == expected


def assert_in_expected(
    result: click.testing.Result,
    expected_inclusion: str
):
    """standard checks for a cli result, confirms output includes expected"""
    logger.debug(result.output)
    assert result.exit_code == 0
    assert not result.exception
    assert expected_inclusion in result.output


def test_cli_no_argument(runner: CliRunner):
    result = runner.invoke(happi_cli)
    assert result.exit_code == 0
    assert result.exception is None
    assert 'Usage:' in result.output
    assert 'Options:' in result.output
    assert 'Commands:' in result.output


def test_search(client: happi.client.Client):
    res = client.search_regex(beamline="TST")

    with search.make_context('search', ['beamline=TST'], obj=client) as ctx:
        res_cli = search.invoke(ctx)

    assert [r.item for r in res] == [r.item for r in res_cli]


def test_search_with_name(
    client: happi.client.Client,
    runner: CliRunner,
    happi_cfg: str
):
    res = client.search_regex(name='TST_BASE_PIM2')

    with search.make_context('search', ['TST_BASE_PIM2'], obj=client) as ctx:
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


def test_search_z(client: happi.client.Client):
    res = client.search_regex(z="6.0")
    with search.make_context('search', ['z=6.0'], obj=client) as ctx:
        res_cli = search.invoke(ctx)

    assert [r.item for r in res] == [r.item for r in res_cli]


def test_search_z_range(
    client: happi.client.Client,
    runner: CliRunner,
    happi_cfg: str
):
    res = client.search_range('z', 3.0, 6.0)

    with search.make_context('search', ['z=3.0,6.0'], obj=client) as ctx:
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


def test_both_range_and_regex_search(client: happi.client.Client):
    # we're only interested in getting this entry (TST_BASE_PIM2)
    res = client.search_regex(z='6.0')
    # we're going to search for z=3,7 name=TST_BASE_PIM2
    # we should only get in return one entry, even though the z value found 2
    with search.make_context('search', ['name=TST_BASE_PIM2', 'z=3.0,7.0'],
                             obj=client) as ctx:
        res_cli = search.invoke(ctx)

    assert [r.item for r in res] == [r.item for r in res_cli]


def test_search_json(runner: CliRunner, happi_cfg: str):
    expected_output = '''[
  {
    "name": "tst_base_pim2",
    "device_class": "types.SimpleNamespace",
    "args": [
      "{{prefix}}"
    ],
    "kwargs": {
      "name": "{{name}}"
    },
    "active": true,
    "documentation": null,
    "prefix": "TST:BASE:PIM2",
    "_id": "TST_BASE_PIM2",
    "beamline": "TST",
    "creation": "Wed Jan 30 09:46:00 2019",
    "last_edit": "Fri Apr 13 14:40:08 2018",
    "macros": null,
    "parent": null,
    "screen": null,
    "stand": "BAS",
    "system": "diagnostic",
    "type": "OphydItem",
    "z": 6.0,
    "y": 10.0
  }
]'''

    result = runner.invoke(
        happi_cli, ['--path', happi_cfg, 'search', '-j', 'TST_BASE_PIM2']
    )

    assert result.exit_code == 0
    assert_match_expected(result, expected_output.split('\n'))


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
        'Please confirm the item info is correct [y/N]: y',
        ' - INFO -  Adding item',
        ' - INFO -  Storing item HappiItem (name=happi_nname) ...',
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
        'Please confirm the item info is correct [y/N]: N',
        ' - INFO -  Aborting'),
    ),
    # Test add item - invalid container
    pytest.param('HappiInvalidItem', (
        'Please select a container, or press enter for generic '
        'Ophyd Device container: ', 'OphydItem', 'HappiItem', '',
        'Selection [OphydItem]: HappiInvalidItem',
        ' - INFO -  Invalid item container HappiInvalidItem'),
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
        'succesfully added to the database'
         ),
    ),
    ], ids=["add_succeeding", "add_aborting",
            "add_invalid_container", "add_not_optional_field"])
def test_add_cli(
    from_user: str,
    expected_output: Tuple[str, ...],
    happi_cfg: str,
    runner: CliRunner
):
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
        'Selecting value: docs', 'Please confirm the item info is '
        'correct [y/N]: y', ' - INFO -  Adding item',
        ' - INFO -  Storing item HappiItem (name=happi_new_name) ...',
        ' - INFO -  Adding / Modifying information for happi_new_name ...',
        ' - INFO -  HappiItem HappiItem (name=happi_new_name) has been '
        'succesfully added to the database', ''], id="clone_succeeding",
    )])
def test_add_clone(
    from_user: str,
    expected_output: Tuple[str, ...],
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
    ]
)
def test_edit(
    from_user: List[str],
    fields: List[str],
    values: List[Any],
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
def test_bad_edit(edit_args: List[str], happi_cfg: str, runner: CliRunner):
    # Test invalid field, note the name is changed to new_name
    bad_edit_result = runner.invoke(
        happi_cli,
        ['--path', happi_cfg, 'edit', 'TST_BASE_PIM', *edit_args]
    )
    assert bad_edit_result.exit_code == 1


def test_load(
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


def test_update(happi_cfg: str, runner: CliRunner):
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
    result = runner.invoke(happi_cli, ["--path", happi_cfg, "update", new])
    assert result.exit_code == 0
    client = happi.client.Client.from_config(cfg=happi_cfg)
    item = client.find_item(name="tst_base_pim2")
    assert item["from_update"]


@pytest.mark.parametrize("from_user, expected_output", [
    pytest.param('\n'.join(['n', 'n', 'n', 'n', 'N', 'n', 'n', 'n', '']), [
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
        '----------Amend Entries-----------', 'Save final item? [y/N]: ',
        ''], id="transfer_succeeding",
    )])
def test_transfer_cli(
    from_user: str,
    expected_output: List[str],
    happi_cfg: str,
    runner: CliRunner
):
    results = runner.invoke(happi_cli, ['--path', happi_cfg, 'transfer',
                            'tst_base_pim', 'OphydItem'], input=from_user)
    assert_match_expected(results, expected_output)


def arg_variants(variants: Tuple[Tuple[Tuple[str]]]):
    """
    Collapse argument variants into all possible combinations.
    """
    for arg_set in itertools.product(*variants):
        yield functools.reduce(
            lambda x, y: x+y,
            arg_set,
            )


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
def test_benchmark_cli(runner: CliRunner, happi_cfg: str, args: Tuple[str]):
    # Make sure the benchmark can complete in some form with valid inputs
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
def test_profile_cli(runner: CliRunner, happi_cfg: str, args: Tuple[str]):
    # Make sure the profile can complete in some form with valid inputs
    if 'pcdsutils' in args and not test_line_prof:
        pytest.skip('Missing pcdsutils or line_profiler.')
    result = runner.invoke(
        happi_cli,
        ['--path', happi_cfg, 'profile'] + list(args),
    )
    assert_in_expected(
        result,
        'Profile completed successfully'
    )
