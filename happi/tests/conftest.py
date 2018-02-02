import logging
from unittest.mock import patch

import pytest
import simplejson

from happi import Client, Device
from happi.backends.json_db import JSONBackend
from happi.backends.mongo_db import MongoBackend

logger = logging.getLogger(__name__)


# Conditional import of mongomock
try:
    from mongomock import MongoClient
    has_mongomock = True
except ImportError as exc:
    logger.warning('Error importing mongomock : -> %s', exc)
    has_mongomock = False


requires_mongomock = pytest.mark.skipif(not has_mongomock,
                                        reason='Missing mongomock')

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


@pytest.fixture(scope='function')
def device_info():
    return {'name': 'alias',
            'z': 400,
            '_id': 'BASE:PV',
            'prefix': 'BASE:PV',
            'beamline': 'LCLS',
            'type': 'Device'}


@pytest.fixture(scope='function')
def device():
    t = Device(**device_info())
    return t


@pytest.fixture(scope='function')
def valve_info():
    return {'name': 'name',
            'z': 300,
            'prefix': 'BASE:VGC:PV',
            '_id': 'BASE:VGC:PV',
            'beamline': 'LCLS',
            'mps': 'MPS:VGC:PV'}


@pytest.fixture(scope='function')
def valve():
    t = Device(**valve_info())
    return t


@pytest.fixture(scope='function')
def mockjsonclient():
    # Write underlying database
    with open('testing.json', 'w+') as handle:
        simplejson.dump({device_info()['prefix']: device_info()},
                        handle)
    # Return handle name
    db = JSONBackend('testing.json')
    return Client(database=db)


@pytest.fixture(scope='function')
def mockmongoclient(*args):
    with patch('happi.backends.mongo_db.MongoClient') as mock_mongo:
        mc = MongoClient()
        mc['test_db'].create_collection('test_collect')
        mock_mongo.return_value = mc
        # Client
        backend = MongoBackend(db='test_db',
                               collection='test_collect')
        client = Client(database=backend)
        # Insert a single device
        client.backend._collection.insert_one(device_info())
        return client


@pytest.fixture(scope='module')
def mockqsbackend():
    # Create a very basic mock class
    class MockQuestionnaireClient(QuestionnaireClient):

        def getProposalsListForRun(self, run):
            return {'X534': {'Instrument': 'TST', 'proposal_id': 'X534'},
                    'LR32': {'Instrument': 'TST', 'proposal_id': 'LR32'}}

        def getProposalDetailsForRun(self, run_no, proposal):
            return {
                'pcdssetup-motors-enc-1-desc': '',
                'pcdssetup-motors-enc-2-desc': '',
                'pcdssetup-motors-enc-3-desc': '',
                'pcdssetup-motors-enc-4-desc': '',
                'pcdssetup-motors-setup-1-location': 'Hutch-main experimental',
                'pcdssetup-motors-setup-1-name': 'sam_x',
                'pcdssetup-motors-setup-1-purpose': 'sample x motion',
                'pcdssetup-motors-setup-1-pvbase': 'TST:USR:MMS:01',
                'pcdssetup-motors-setup-1-stageidentity': 'IMS MD23',
                'pcdssetup-motors-setup-2-location': 'Hutch-main experimental',
                'pcdssetup-motors-setup-2-name': 'sam_z',
                'pcdssetup-motors-setup-2-purpose': 'sample z motion',
                'pcdssetup-motors-setup-2-pvbase': 'TST:USR:MMS:02',
                'pcdssetup-motors-setup-2-stageidentity': 'IMS MD23',
                'pcdssetup-motors-setup-3-location': 'Hutch-main experimental',
                'pcdssetup-motors-setup-3-name': 'sam_y',
                'pcdssetup-motors-setup-3-purpose': 'sample y motion',
                'pcdssetup-motors-setup-3-pvbase': 'TST:USR:MMS:03',
                'pcdssetup-motors-setup-3-stageidentity': 'IMS MD32',
                'pcdssetup-motors-setup-4-location': 'Hutch-main experimental',
                'pcdssetup-motors-setup-4-name': 'sam_r',
                'pcdssetup-motors-setup-4-purpose': 'sample rotation',
                'pcdssetup-motors-setup-4-pvbase': 'TST:USR:MMS:04',
                'pcdssetup-motors-setup-4-stageidentity': 'IMS MD23',
                'pcdssetup-motors-setup-5-location': 'Hutch-main experimental',
                'pcdssetup-motors-setup-5-name': 'sam_az',
                'pcdssetup-motors-setup-5-purpose': 'sample azimuth',
                'pcdssetup-motors-setup-5-pvbase': 'TST:USR:MMS:05',
                'pcdssetup-motors-setup-5-stageidentity': 'IMS MD23',
                'pcdssetup-motors-setup-6-location': 'Hutch-main experimental',
                'pcdssetup-motors-setup-6-name': 'sam_flip',
                'pcdssetup-motors-setup-6-purpose': 'sample flip',
                'pcdssetup-motors-setup-6-pvbase': 'TST:USR:MMS:06',
                'pcdssetup-motors-setup-6-stageidentity': 'IMS MD23'}

    with patch('happi.backends.qs_db.QuestionnaireClient') as qs_cli:
        # Replace QuestionnaireClient with our test version
        mock_qs = MockQuestionnaireClient()
        qs_cli.return_value = mock_qs
        # Instantiate a fake device
        backend = QSBackend(15, 'LR32')
        return backend
