# test_cli.py

import pytest
import os
import happi
from happi.cli import happi_cli
from happi.errors import SearchError


@pytest.fixture(scope='function')
def happi_cfg():
    fname = os.path.join(os.getcwd(), 'happi.cfg')
    with open(fname, 'w+') as handle:
        handle.write("""\
[DEFAULT]'
backend=json
path=db.json
""")
    yield fname
    os.remove(fname)


@pytest.fixture(scope='function')
def db():
    fname = os.path.join(os.getcwd(), 'db.json')
    with open(fname, 'w+') as handle:
        handle.write("""\
{
    "TST:BASE:PIM": {
        "_id": "TST:BASE:PIM",
        "active": true,
        "args": [
            "{{prefix}}"
        ],
        "beamline": "TST",
        "creation": "Tue Jan 29 09:46:00 2019",
        "device_class": "pcdsdevices.device_types.PIM",
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
        "type": "PIM",
        "z": 3.0
    },
    "TST:BASE:PIM2": {
        "_id": "TST:BASE:PIM2",
        "active": true,
        "args": [
            "{{prefix}}"
        ],
        "beamline": "TST",
        "creation": "Wed Jan 30 09:46:00 2019",
        "device_class": "pcdsdevices.device_types.PIM",
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
        "type": "PIM",
        "z": 6.0
    }
}
""")
    yield fname
    os.remove(fname)


def test_cli_version(capsys):
    happi_cli(['--version'])
    readout = capsys.readouterr()
    assert happi.__version__ in readout.out
    assert happi.__file__ in readout.out


def test_search(happi_cfg, db):
    config_name = os.path.join(os.getcwd(), 'happi.cfg')
    client = happi.client.Client.from_config(cfg=config_name)
    devices = client.search(beamline="TST")
    devices_cli = happi.cli.happi_cli(['--verbose', '--path', config_name,
                                       'search', 'beamline', 'TST'])
    assert devices == devices_cli


def test_search_z(happi_cfg, db):
    config_name = os.path.join(os.getcwd(), 'happi.cfg')
    client = happi.client.Client.from_config(cfg=config_name)
    devices = client.search(z=6.0)
    devices_cli = happi.cli.happi_cli(['--verbose', '--path', config_name,
                                       'search', 'z', '6.0'])
    assert devices == devices_cli


def test_odd_criteria(happi_cfg, db):
    config_name = os.path.join(os.getcwd(), 'happi.cfg')
    with pytest.raises(SearchError):
        happi.cli.happi_cli(['--path', config_name, 'search', 'beamline'])
