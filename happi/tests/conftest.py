import logging
import sys
import tempfile
from typing import Any
from unittest.mock import patch

import pytest
import simplejson
from click.testing import CliRunner

import happi.cli
from happi import Client, EntryInfo, HappiItem, OphydItem
from happi.backends.json_db import JSONBackend

logger = logging.getLogger(__name__)

# Conditional import of pymongo, mongomock
try:
    from mongomock import MongoClient

    from happi.backends.mongo_db import MongoBackend
    supported_backends = ['json', 'mongo']
except ImportError as exc:
    logger.warning('Error importing mongomock : -> %s', exc)
    supported_backends = ['json']

requires_mongo = pytest.mark.skipif('mongo' not in supported_backends,
                                    reason='Missing mongo')

# Conditional import of psdm_qs_cli
try:
    from psdm_qs_cli import QuestionnaireClient

    from happi.backends.qs_db import QSBackend
    has_qs_cli = True
except ImportError as exc:
    logger.warning('Error importing psdm_qs_cli : -> %s', exc)
    has_qs_cli = False


requires_questionnaire = pytest.mark.skipif(not has_qs_cli,
                                            reason='Missing psdm_qs_cli')


try:
    import pcdsdevices  # noqa
    has_pcdsdevices = True
except ImportError as exc:
    logger.warning('error importing pcdsdevices : -> %s', exc)
    has_pcdsdevices = False


requires_pcdsdevices = pytest.mark.skipif(not has_pcdsdevices,
                                          reason='Missing pcdsdevices')


requires_py39 = pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason='Optional dependency needs at least py39',
)


@pytest.fixture(scope='function')
def item_info() -> dict[str, Any]:
    return {'name': 'alias',
            'z': 400,
            '_id': 'alias',
            'prefix': 'BASE:PV',
            'beamline': 'LCLS',
            'type': 'OphydItem',
            'device_class': 'types.SimpleNamespace',
            'args': list(),
            'kwargs': {'hi': 'oh hello'},
            'location_group': 'LOC',
            'functional_group': 'FUNC',
            }


@pytest.fixture(scope='function')
def item(item_info: dict[str, Any]) -> OphydItem:
    return OphydItem(**item_info)


class JinjaItem(OphydItem):
    blank_list = EntryInfo('a list', enforce=list, default=[1, 2, 3])
    blank_str = EntryInfo('a string', enforce=str, default='blank')
    blank_bool = EntryInfo('a bool', enforce=bool, default=True)
    blank_exclude = EntryInfo('omitted if default',
                              default='default',
                              include_default_as_kwarg=False)
    blank_none = EntryInfo('default is None')


@pytest.fixture(scope='function')
def item_info_jinja() -> dict[str, Any]:
    return {'name': 'alias',
            'z': 400,
            '_id': 'alias',
            'prefix': 'BASE:PV',
            'beamline': 'LCLS',
            'type': 'OphydItem',
            'device_class': 'types.SimpleNamespace',
            'args': list(),
            'kwargs': {
                'hi': 'oh hello',
                'loc': '{{location_group}}',
                'blank_list': '{{blank_list}}',
                'blank_str': '{{blank_str}}',
                'blank_bool': '{{blank_bool}}',
                'blank_none': '{{blank_none}}',
                'blank_exclude': '{{blank_exclude}}',
                'blank': '{{blank}}'
            },
            'location_group': 'LOC',
            'functional_group': 'FUNC',
            'blank_list': [1, 2, 3],
            'blank_str': 'blank',
            'blank_bool': True,
            'blank_none': None,
            'blank_exclude': 'default',
            'blank': None
            }


@pytest.fixture(scope='function')
def item_jinja(item_info_jinja: dict[str, Any]) -> OphydItem:
    return JinjaItem(**item_info_jinja)


@pytest.fixture(scope='function')
def valve_info() -> dict[str, Any]:
    return {'name': 'name',
            'z': 300,
            'prefix': 'BASE:VGC:PV',
            '_id': 'name',
            'beamline': 'LCLS',
            'mps': 'MPS:VGC:PV',
            'location_group': 'LOC',
            'functional_group': 'FUNC',
            }


@pytest.fixture(scope='function')
def valve(valve_info: dict[str, Any]) -> OphydItem:
    return OphydItem(**valve_info)


@pytest.fixture(scope='function')
def Item1():
    class Item1(HappiItem):
        dupe = EntryInfo('duplicate', enforce=int, default=1)
        one = EntryInfo('two', enforce=['one', 'zero'])
        prefix = EntryInfo('z', enforce=bool)
        # cannot be cast into Item2.bad_dupe1
        bad_dupe1 = EntryInfo('bad enforce', enforce=str)
        bad_dupe2 = EntryInfo('bad enforce', enforce=int)
        excl1_1 = EntryInfo('exclusive to Item1 #1', default='e1_1',
                            enforce=str)
        excl1_2 = EntryInfo('exclusive to Item1 #2', enforce=str)

    return Item1


@pytest.fixture(scope='function')
def item1_dev(Item1):
    return Item1(name='i1', documentation='Created as Item1',
                 one='one', bad_dupe1='hello', bad_dupe2=33)


@pytest.fixture(scope='function')
def Item2():
    class Item2(HappiItem):
        dupe = EntryInfo('duplicate', enforce=int, default=1)
        two = EntryInfo('two', enforce=['zero', 'two'], optional=False)
        bad_dupe1 = EntryInfo('bad enforce', enforce=bool)
        # cannot be cast into Item1.bad_dupe2
        bad_dupe2 = EntryInfo('bad enforce', enforce=str)
        excl2_1 = EntryInfo('exclusive to Item2 #1', default=21, enforce=int)
        excl2_2 = EntryInfo('exclusive to Item2 #2', enforce=int)

    return Item2


@pytest.fixture(scope='function')
def item2_dev(Item2):
    return Item2(name='i2', documentaiton='Created as Item2',
                 two='two', bad_dupe1=False, bad_dupe2='hallo')


@pytest.fixture(scope='function')
def mockjsonclient(item_info: dict[str, Any]):
    # Write underlying database
    with tempfile.NamedTemporaryFile(mode='w') as handle:
        simplejson.dump({item_info['name']: item_info},
                        handle)
        handle.flush()  # flush buffer to write file
        # Return handle name
        db = JSONBackend(handle.name)
        yield Client(database=db)
        # tempfile will be deleted once context manager is resolved


@pytest.fixture(scope='function')
@requires_mongo
def mockmongoclient(item_info: dict[str, Any]):
    with patch('happi.backends.mongo_db.MongoClient') as mock_mongo:
        mc = MongoClient()
        mc['test_db'].create_collection('test_collect')
        mock_mongo.return_value = mc
        # Client
        backend = MongoBackend(db='test_db', pw='test_pw', user='user', host='host',
                               collection='test_collect')
        client = Client(database=backend)
        # Insert a single device
        client.backend._collection.insert_one(item_info)
        return client


if 'mongo' in supported_backends:
    @pytest.fixture(scope='function', params=supported_backends)
    def happi_client(request, mockmongoclient, mockjsonclient):
        if request.param == 'json':
            return mockjsonclient
        if request.param == 'mongo':
            return mockmongoclient
else:
    @pytest.fixture(scope='function', params=supported_backends)
    def happi_client(request, mockjsonclient):
        return mockjsonclient


@pytest.fixture(scope='module')
def mockqsbackend():
    # Create a very basic mock class
    class MockQuestionnaireClient(QuestionnaireClient):

        def getProposalsListForRun(self, run):
            return {
                'X534': {'Instrument': 'TST', 'proposal_id': 'X534'},
                'LR32': {'Instrument': 'TST', 'proposal_id': 'LR32'},
                'LU34': {'Instrument': 'MFX', 'proposal_id': 'LU34'},
            }

        def getProposalDetailsForRun(self, run_no, proposal):
            return {
                'pcdssetup-motors-1-location': 'Hutch-main experimental',
                'pcdssetup-motors-1-name': 'sam_x',
                'pcdssetup-motors-1-purpose': 'sample x motion',
                'pcdssetup-motors-1-pvbase': 'TST:USR:MMS:01',
                'pcdssetup-motors-1-stageidentity': 'IMS MD23',
                'pcdssetup-motors-2-location': 'Hutch-main experimental',
                'pcdssetup-motors-2-name': 'sam_z',
                'pcdssetup-motors-2-purpose': 'sample z motion',
                'pcdssetup-motors-2-pvbase': 'TST:USR:MMS:02',
                'pcdssetup-motors-2-stageidentity': 'IMS MD23',
                'pcdssetup-motors-3-location': 'Hutch-main experimental',
                'pcdssetup-motors-3-name': 'sam_y',
                'pcdssetup-motors-3-purpose': 'sample y motion',
                'pcdssetup-motors-3-pvbase': 'TST:USR:MMS:03',
                'pcdssetup-motors-3-stageidentity': 'IMS MD32',
                'pcdssetup-motors-4-location': 'Hutch-main experimental',
                'pcdssetup-motors-4-name': 'sam_r',
                'pcdssetup-motors-4-purpose': 'sample rotation',
                'pcdssetup-motors-4-pvbase': 'TST:USR:MMS:04',
                'pcdssetup-motors-4-stageidentity': 'IMS MD23',
                'pcdssetup-motors-5-location': 'Hutch-main experimental',
                'pcdssetup-motors-5-name': 'sam_az',
                'pcdssetup-motors-5-purpose': 'sample azimuth',
                'pcdssetup-motors-5-pvbase': 'TST:USR:MMS:05',
                'pcdssetup-motors-5-stageidentity': 'IMS MD23',
                'pcdssetup-motors-6-location': 'Hutch-main experimental',
                'pcdssetup-motors-6-name': 'sam_flip',
                'pcdssetup-motors-6-purpose': 'sample flip',
                'pcdssetup-motors-6-pvbase': 'TST:USR:MMS:06',
                'pcdssetup-motors-6-stageidentity': 'IMS MD23',
                'pcdssetup-trig-1-delay': '0.00089',
                'pcdssetup-trig-1-eventcode': '198',
                'pcdssetup-trig-1-name': 'Overview_trig',
                'pcdssetup-trig-1-polarity': 'positive',
                'pcdssetup-trig-1-purpose': 'Overview',
                'pcdssetup-trig-1-pvbase': 'MFX:REC:EVR:02:TRIG1',
                'pcdssetup-trig-1-width': '0.00075',
                'pcdssetup-trig-2-delay': '0.000894348',
                'pcdssetup-trig-2-eventcode': '198',
                'pcdssetup-trig-2-name': 'Meniscus_trig',
                'pcdssetup-trig-2-polarity': 'positive',
                'pcdssetup-trig-2-purpose': 'Meniscus',
                'pcdssetup-trig-2-pvbase': 'MFX:REC:EVR:02:TRIG3',
                'pcdssetup-trig-2-width': '0.0005',
                'pcdssetup-ao-1-device': 'Acromag IP231 16-bit',
                'pcdssetup-ao-1-name': 'irLed',
                'pcdssetup-ao-1-purpose': 'IR LED',
                'pcdssetup-ao-2-channel': '6',
                'pcdssetup-ao-2-device': 'Acromag IP231 16-bit',
                'pcdssetup-ao-2-name': 'laser_shutter_opo',
                'pcdssetup-ao-2-purpose': 'OPO Shutter',
                'pcdssetup-ao-3-channel': '7',
                'pcdssetup-ao-3-device': 'Acromag IP231 16-bit',
                'pcdssetup-ao-3-name': 'laser_shutter_evo1',
                'pcdssetup-ao-3-purpose': 'EVO Shutter1',
                'pcdssetup-ao-4-channel': '2',
                'pcdssetup-ao-4-device': 'Acromag IP231 16-bit',
                'pcdssetup-ao-4-name': 'laser_shutter_evo2',
                'pcdssetup-ao-4-purpose': 'EVO Shutter2',
                'pcdssetup-ao-5-channel': '3',
                'pcdssetup-ao-5-device': 'Acromag IP231 16-bit',
                'pcdssetup-ao-5-name': 'laser_shutter_evo3',
                'pcdssetup-ao-5-purpose': 'EVO Shutter3',
                'pcdssetup-ao-1-pvbase': 'MFX:USR:ao1',
                'pcdssetup-ao-2-pvbase': 'MFX:USR:ao1',
                'pcdssetup-ao-3-pvbase': 'MFX:USR:ao1',
                'pcdssetup-ao-4-pvbase': 'MFX:USR:ao1',
                'pcdssetup-ao-5-pvbase': 'MFX:USR:ao1',
                'pcdssetup-ai-1-device': 'Acromag IP231 16-bit',
                'pcdssetup-ai-1-name': 'irLed',
                'pcdssetup-ai-1-purpose': 'IR LED',
                'pcdssetup-ai-1-pvbase': 'MFX:USR:ai1',
                'pcdssetup-ai-1-channel': '7',
                'pcdssetup-motors-11-purpose': 'Von Hamos vertical',
                'pcdssetup-motors-11-stageidentity': 'Beckhoff',
                'pcdssetup-motors-11-location': 'XPP goniometer',
                'pcdssetup-motors-11-pvbase': 'HXX:VON_HAMOS:MMS:01',
                'pcdssetup-motors-11-name': 'vh_y',
            }

        def getExpName2URAWIProposalIDs(self):
            return {
                'tstx53416': 'X534',
                'tstlr3216': 'LR32',
                'mfxlu3417': 'LU34',
            }

    with patch('happi.backends.qs_db.QuestionnaireClient') as qs_cli:
        # Replace QuestionnaireClient with our test version
        mock_qs = MockQuestionnaireClient(use_kerberos=False,
                                          user='user', pw='pw')
        qs_cli.return_value = mock_qs
        # Instantiate a fake device
        backend = QSBackend('tstlr3216')
        return backend


@pytest.fixture(scope='function')
def three_valves():
    valve1 = {'name': 'valve1',
              'z': 300,
              'prefix': 'BASE:VGC1:PV',
              '_id': 'VALVE1',
              'beamline': 'LCLS',
              'mps': 'MPS:VGC:PV',
              'type': 'OphydItem',
              'location_group': 'LOC',
              'functional_group': 'FUNC',
              'device_class': 'types.SimpleNamespace',
              'args': list(),
              'kwargs': {'hi': 'oh hello'},
              }

    valve2 = {'name': 'valve2',
              'z': 301,
              'prefix': 'BASE:VGC2:PV',
              '_id': 'VALVE2',
              'beamline': 'LCLS',
              'mps': 'MPS:VGC:PV',
              'type': 'OphydItem',
              'location_group': 'LOC',
              'functional_group': 'FUNC',
              'device_class': 'types.SimpleNamespace',
              'args': list(),
              'kwargs': {'hi': 'oh hello'},
              }

    valve3 = {'name': 'valve3',
              'z': 301,
              'prefix': 'BASE:VGC3:PV',
              '_id': 'VALVE3',
              'beamline': 'LCLS',
              'mps': 'MPS:VGC:PV',
              'location_group': 'LOC',
              'functional_group': 'FUNC',
              'type': 'OphydItem',
              'device_class': 'types.SimpleNamespace',
              'args': list(),
              'kwargs': {'hi': 'oh hello'},
              }

    valves = dict(
        VALVE1=valve1,
        VALVE2=valve2,
        VALVE3=valve3,
    )

    return valves


@pytest.fixture(scope='function')
def client_with_three_valves(happi_client, three_valves):
    for dev in happi_client.all_items:
        happi_client.backend.delete(dev['_id'])

    for name, valve in three_valves.items():
        happi_client.backend.save(name, valve, insert=True)
    return happi_client


@pytest.fixture(scope='function')
def db(tmp_path):
    json_path = tmp_path / 'db.json'
    json_path.write_text("""\
{
    "tst_base_pim": {
        "_id": "tst_base_pim",
        "active": true,
        "beamline": "TST",
        "creation": "Tue Jan 29 09:46:00 2019",
        "device_class": "types.SimpleNamespace",
        "last_edit": "Thu Apr 12 14:40:08 2018",
        "macros": null,
        "name": "tst_base_pim",
        "parent": null,
        "prefix": "TST:BASE:PIM",
        "screen": null,
        "stand": "BAS",
        "system": "diagnostic",
        "type": "HappiItem",
        "z": 3.0,
        "y": 40.0
    },
    "tst_base_pim2": {
        "_id": "tst_base_pim2",
        "active": true,
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
        "type": "HappiItem",
        "z": 6.0,
        "y": 10.0
    },
    "tst_minimal": {
        "_id": "tst_minimal",
        "creation": "Tue Jan 29 09:46:00 2019",
        "device_class": "types.SimpleNamespace",
        "last_edit": "Thu Sep 14 14:40:08 2018",
        "name": "tst_minimal",
        "type": "HappiItem"
    }
}
""")
    return str(json_path.absolute())


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
def bad_db(tmp_path):
    json_path = tmp_path / 'db.json'
    json_path.write_text("""\
{
    "tst_id": {
        "_id": "tst_id",
        "active": true,
        "creation": "Tue Jan 29 09:46:00 2019",
        "device_class": "types.SimpleNamespace",
        "last_edit": "Thu Apr 12 14:40:08 2018",
        "name": "tst_name",
        "type": "HappiItem"
    },
    "tst_inst": {
        "_id": "tst_inst",
        "active": true,
        "creation": "Tue Jan 29 09:46:00 2019",
        "device_class": "invalidclassname",
        "last_edit": "Thu Apr 12 14:40:08 2018",
        "name": "tst_inst",
        "type": "HappiItem"
    },
    "tst_extra_info": {
        "_id": "tst_extra_info",
        "active": true,
        "creation": "Tue Jan 29 09:46:00 2019",
        "device_class": "types.SimpleNamespace",
        "extra_info": "extra_info_here",
        "last_edit": "Thu Apr 12 14:40:08 2018",
        "name": "tst_extra_info",
        "type": "HappiItem"
    },
    "tst_arg_mismatch": {
        "_id": "tst_arg_mismatch",
        "args": ["{{active}}"],
        "creation": "Tue Jan 29 09:46:00 2019",
        "device_class": "types.SimpleNamespace",
        "last_edit": "Thu Apr 12 14:40:08 2018",
        "name": "tst_arg_mismatch",
        "type": "HappiItem"
    },
    "tst_kwarg_mismatch": {
        "_id": "tst_kwarg_mismatch",
        "active": true,
        "args": ["{{active}}"],
        "device_class": "types.SimpleNamespace",
        "kwargs": {"creation": "{{creation}}"},
        "name": "tst_kwarg_mismatch",
        "last_edit": "Thu Apr 12 14:40:08 2018",
        "type": "HappiItem"
    },
    "tst_missing_mandatory": {
        "_id": "tst_missing_mandatory",
        "active": true,
        "args": ["{{active}}"],
        "creation": "Tue Jan 29 09:46:00 2019",
        "device_class": "types.SimpleNamespace",
        "kwargs": {"creation": "{{creation}}"},
        "name": "tst_missing_mandatory",
        "last_edit": "Thu Apr 12 14:40:08 2018",
        "type": "OphydItem"
    }
}
""")
    return str(json_path.absolute())


@pytest.fixture(scope='function')
def bad_happi_cfg(tmp_path, bad_db):
    happi_cfg_path = tmp_path / 'happi.cfg'
    happi_cfg_path.write_text(f"""\
[DEFAULT]'
backend=json
path={bad_db}
""")
    return str(happi_cfg_path.absolute())


@pytest.fixture(scope='function')
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def skip_cleanup(monkeypatch):
    """ Monkeypatch happi_cli to skip ophyd cleanup """
    def no_op(*args, **kwargs):
        return

    monkeypatch.setattr(happi.cli, 'ophyd_cleanup', no_op)
    monkeypatch.setattr(happi.cli, 'pyepics_cleanup', no_op)
