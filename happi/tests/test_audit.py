from abc import ABCMeta
import argparse
from unittest.mock import patch, call
import happi
import json
from happi.audit import Audit, ReportCode
from unittest import TestCase
import pytest
import logging

from .conftest import requires_pcdsdevices

logger = logging.getLogger(__name__)
audit = Audit()
# 9 - NO_CODE
report_code = ReportCode(9)

ITEMS = json.loads("""{
    "XRT:M3H": {
        "_id": "XRT:M3H",
        "active": true,
        "args": [
            "{{prefix}}"
        ],
        "beamline": "PBT",
        "creation": "Tue Feb 27 16:12:10 2018",
        "device_class": "pcdsdevices.device_types.OffsetMirror",
        "kwargs": {
            "name": "{{name}}"
        },
        "last_edit": "Tue Feb 27 16:12:10 2018",
        "macros": null,
        "name": "xrt_m3h",
        "parent": null,
        "prefix": "XRT:M3H",
        "prefix_xy": null,
        "screen": null,
        "stand": null,
        "system": "beam control",
        "type": "something_else",
        "xgantry_prefix": null,
        "z": 927.919
    },
    "XCS:SB2:PIM": {
        "_id": "XCS:SB2:PIM",
        "active": true,
        "args": [
            "{{prefix}}"
        ],
        "beamline": "XCS",
        "creation": "Tue Feb 27 11:15:19 2018",
        "detailed_screen": null,
        "device_class": "pcdsdevices.pim.PIMWithLED",
        "documentation": null,
        "embedded_screen": null,
        "engineering_screen": null,
        "kwargs": {
            "name": "{{name}}",
            "prefix_det": "{{prefix_det}}"
        },
        "last_edit": "Fri May 17 11:44:12 2019",
        "lightpath": false,
        "macros": null,
        "name": "xcs_sb2_pim",
        "parent": null,
        "prefix": "XCS:SB2:PIM",
        "prefix_det": "XCS:GIGE:04:",
        "screen": null,
        "stand": null,
        "system": null,
        "type": null,
        "z": 1005.72
    },
     "MFX:DG2:IPM": {
        "_id": "MFX:DG2:IPM",
        "active": true,
        "args": [
            "{{prefix}}"
        ],
        "beamline": "MFX",
        "creation": "Wed Mar 27 09:53:48 2019",
        "data": null,
        "detailed_screen": null,
        "device_class": "pcdsdevices.device_types.IPM",
        "documentation": null,
        "embedded_screen": null,
        "engineering_screen": null,
        "kwargs": {
            "name": "{{name}}"
        },
        "last_edit": "Wed Mar 27 09:53:48 2019",
        "lightpath": false,
        "macros": null,
        "name": "mfx_dg2_ipm",
        "parent": null,
        "prefix": "MFX:DG2:IPM",
        "stand": "DG2",
        "system": "diagnostic",
        "type": "pcdsdevices.happi.containers.IPM",
        "z": -1.0
    },
        "dummy_item": {
        "_id": "dummy_item",
        "active": true,
        "args": [
            "{{prefix}}"
        ],
        "creation": "Thu Sep 10 11:59:23 2020",
        "device_class": "types.SimpleNamespace",
        "documentation": null,
        "kwargs": {
            "name": "{{name}}"
        },
        "last_edit": "Thu Sep 10 11:59:23 2020",
        "name": "dummy_item",
        "prefix": "PREFIX",
        "type": "OphydItem"
    },
        "alias2": {
        "_id": "alias2",
        "active": true,
        "args": [],
        "beamline": "LCLS",
        "creation": "Fri Sep  4 11:31:26 2020",
        "device_class": "types.SimpleNamespace",
        "documentation": null,
        "functional_group": "FUNC",
        "kwargs": {
            "hi": "oh hello"
        },
        "last_edit": "Fri Sep  4 11:31:26 2020",
        "location_group": "LOC",
        "name": "alias2",
        "prefix": "BASE:PV",
        "type": "OphydItem",
        "z": "400"
    }
    }
    """)


@pytest.fixture(scope='class')
def happi_config(tmp_path_factory, json_db):
    tmp_dir = tmp_path_factory.mktemp('happi.cfg')
    happi_cfg_path = tmp_dir / 'happi.cfg'
    happi_cfg_path.write_text(f"""\
[DEFAULT]'
backend=json
path={json_db}
""")
    return str(happi_cfg_path.absolute())


@pytest.fixture(scope='class')
def json_db(tmp_path_factory):
    dir_path = tmp_path_factory.mktemp("db_dir")
    json_path = dir_path / 'db.json'
    json_path.write_text(json.dumps(ITEMS))
    return str(json_path.absolute())


class TestCommandClass:
    """
    Test that the Command class has been initialized propertly
    And that the abstract classes have raise an error if not implemented
    """
    happi.audit.Command.__abstractmethods__ = set()

    class Dummy(happi.audit.Command):
        pass

    d = Dummy('dummy', 'description')

    with pytest.raises(NotImplementedError):
        d.add_args('a_parser')
    with pytest.raises(NotImplementedError):
        d.run('some_arg')

    assert isinstance(happi.audit.Command, ABCMeta)

    def test_constructor_fail(self):
        with pytest.raises(TypeError):
            happi.audit.Command()

    def test_constructor_partial_fail(self):
        with pytest.raises(TypeError):
            happi.audit.Command("my_name")

    def test_constructor_success(self):
        self.cmd = happi.audit.Command('a_name', 'a_description')
        expected_dict = {'name': 'a_name', 'summary': 'a_description'}
        assert self.cmd.__dict__ == expected_dict


class TestValidateRun:
    args = argparse.Namespace(cmd='audit', extras=True, file='db.json',
                              path=None, verbose=False, version=False)
    args2 = argparse.Namespace(cmd='audit', extras=False, file='db.json',
                               path=None, verbose=False, version=False)
    args3 = argparse.Namespace(cmd='audit', extras=False, file=None,
                               path=None, verbose=False, version=False)
    args4 = argparse.Namespace(cmd='audit', extras=True, file=None,
                               path=None, verbose=False, version=False)

    def test_validate_file_called(self):
        with patch('happi.audit.Audit.validate_file',
                   return_value=True) as mock:
            audit.run(self.args)
            assert mock.called

    def test_validate_file_called_with_false(self):
        with patch('happi.audit.Audit.validate_file', return_value=False):
            res = audit.run(self.args)
            assert res is None

    @patch('happi.audit.Audit.validate_file', return_value=True)
    def test_check_extra_attributes_called(self, mock_valid_file):
        with patch('happi.audit.Audit.check_extra_attributes') as mock:
            audit.run(self.args)
            mock.assert_called_once()

    @patch('happi.audit.Audit.validate_file', return_value=True)
    def test_check_extra_attributes_not_called(self, mock_valid_file):
        with patch('happi.audit.Audit.parse_database') as mock:
            audit.run(self.args2)
            mock.assert_called_once()

    def test_find_config_called(self):
        with patch('happi.client.Client.find_config',
                   return_value='happi.cfg') as mock:
            audit.run(self.args3)
            mock.assert_called_once()

    def test_find_config_called_exit(self):
        with patch('happi.client.Client.find_config',
                   return_value=None):
            with pytest.raises(SystemExit) as sys_e:
                audit.run(self.args3)
                assert sys_e.e.type == SystemExit
                assert sys_e.value.code == 1

    @patch('happi.client.Client.find_config', return_value='happi.cfg')
    def test_config_parser_with_return_none(self, mock_find_config):
        with patch('configparser.ConfigParser.get', return_value=None):
            with pytest.raises(Exception):
                res = audit.run(self.args3)
                assert res is None

    @patch('happi.client.Client.find_config', return_value='happi.cfg')
    @patch('configparser.ConfigParser.get', return_value='db.json')
    @patch('happi.audit.Audit.validate_file', return_value=True)
    def test_validate_file_called_with_true(self, mock_validate, mock_parser,
                                            mock_config):
        audit.run(self.args3)
        mock_validate.assert_called_once()

    @patch('happi.audit.Audit.validate_file', return_value=True)
    @patch('happi.client.Client.find_config', return_value='happi.cfg')
    @patch('configparser.ConfigParser.get', return_value='db.json')
    @patch('happi.audit.Audit.parse_database')
    def test_config_with_parse_database(self, mock_parse_db,
                                        mock_parser, mock_cfgm,
                                        mock_valid_file):
        audit.run(self.args3)
        mock_parser.assert_called_once()

    @patch('happi.audit.Audit.validate_file', return_value=True)
    @patch('happi.client.Client.find_config', return_value='happi.cfg')
    @patch('configparser.ConfigParser.get', return_value='db.json')
    @patch('happi.audit.Audit.check_extra_attributes')
    def test_config_with_extras(self, mock_extras, mock_parser,
                                mock_config, mock_valid_file):
        audit.run(self.args4)
        mock_extras.assert_called_once()

    @patch('happi.client.Client.find_config', return_value='happi.cfg')
    @patch('configparser.ConfigParser.get', return_value='db.json')
    def test_config_parser_with_return_not_none(self, mock_parser, mock_cfg):
        with patch('happi.audit.Audit.validate_file', return_value=False):
            with pytest.raises(SystemExit) as sys_e:
                audit.run(self.args3)
                assert sys_e.type == SystemExit
                assert sys_e.value.code == 1


class TestValidateFileTests:
    """
    Test validate_file
    """
    @patch('os.path.isfile', return_value=True)
    def test_validate_is_file(self, mock_file_name):
        """
        Mocking os.path.isfile and using the return value True
        """
        assert audit.validate_file("bla") is True

    @patch('os.path.isfile', return_value=False)
    def test_validate_is_not_file(self, mock_file_name):
        """
        Mocking os.path.isfile and using the return value False
        """
        assert audit.validate_file('sfsdfsf') is False


@requires_pcdsdevices
# need this here unless i change the
# devices to only be OphydItem and HappiItems....
class TestValidateContaienr(TestCase):
    """
    Test the validate_container
    """
    def test_validate_container_invalid(self):
        with patch('happi.containers.registry', return_value=True):
            first_key = list(ITEMS.keys())[0]
            item = ITEMS.get(first_key)
            res = audit.validate_container(item)
            print('Testing validate_container with INVALID container, '
                  f'expected result {report_code.INVALID}, got: {res}')
            assert res == report_code.INVALID

    def test_validate_container_missing(self):
        with patch('happi.containers.registry', return_value=True):
            second_key = list(ITEMS.keys())[1]
            item = ITEMS.get(second_key)
            res = audit.validate_container(item)
            print('Testing validate_container with MISSING container, '
                  f'expected result: {report_code.MISSING}, got: {res}')
            assert res == report_code.MISSING

    def test_validate_container_success(self):
        with patch('happi.containers.registry', return_value=False):
            second_key = list(ITEMS.keys())[2]
            item = ITEMS.get(second_key)
            res = audit.validate_container(item)
            print('Testing validate_container with MISSING container, '
                  f'expected result {report_code.SUCCESS}, got: {res}')
            assert res == report_code.SUCCESS


@pytest.mark.usefixtures('happi_config')
@pytest.mark.usefixtures('json_db')
class TestExtraAttributes:
    """
    Test the validate_extra_attributes
    """
    @pytest.fixture(scope='function')
    def item_list(self, happi_config, request):
        client = happi.client.Client.from_config(cfg=happi_config)
        return client.all_items

    def test_check_extra_attributes(self, json_db, item_list):
        calls = []
        for i in item_list:
            calls.append(call(i))
        with patch('happi.audit.Audit.validate_extra_attributes') as m:
            audit.check_extra_attributes(json_db)
            m.assert_has_calls(calls, any_order=True)

    def test_validate_extra_attributes(self, item_list):
        for i in item_list:
            # this item does not have extra items
            if i.name == 'dummy_item':
                res = audit.validate_extra_attributes(i)
                assert res == report_code.SUCCESS
            # this item has extra items
            elif i.name == 'alias2':
                res = audit.validate_extra_attributes(i)
                assert res == report_code.EXTRAS
