# test_cli.py

import pytest
import happi
from happi.cli import happi_cli


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


def test_search(happi_cfg):
    client = happi.client.Client.from_config(cfg=happi_cfg)
    res = client.search(beamline="TST")
    res_cli = happi.cli.happi_cli(['--verbose', '--path', happi_cfg, 'search',
                                   'beamline=TST'])
    assert [r.device for r in res] == [r.device for r in res_cli]


def test_search_z(happi_cfg):
    client = happi.client.Client.from_config(cfg=happi_cfg)
    res = client.search(z=6.0)
    res_cli = happi.cli.happi_cli(['--verbose', '--path', happi_cfg, 'search',
                                   'z=6.0'])
    assert [r.device for r in res] == [r.device for r in res_cli]
