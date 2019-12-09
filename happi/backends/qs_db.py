"""
Backend implementation for parsing the Questionnaire
"""
import re
import logging

from psdm_qs_cli import QuestionnaireClient

from .json_db import JSONBackend
from ..errors import DatabaseError

logger = logging.getLogger(__name__)


class QSBackend(JSONBackend):
    """
    Questionniare Backend

    This backend connects to the LCLS questionnaire and looks at devices with
    the key pattern pcds-{}-setup-{}-{}. These fields are then combined and
    turned into proper happi devices. The translation of table name to
    ``happi.HappiItem`` is determined by the :attr:`.device_translations`
    dictionary. The beamline is determined by looking where the proposal was
    submitted.

    Unlike the other backends, this one is read-only. All changes to the device
    information should be done via the web interface. Finally, in order to
    avoid duplicating any code needed to search the device database, the
    QSBackend inherits directly from JSONBackend. Many of the functions are
    unmodified with exception being that this backend merely searchs through an
    in memory dictionary while the JSONBackend reads from the file before
    searches.

    Parameters
    ----------
    expname : str
        The experiment name from the elog, e.g. xcslp1915
    """
    device_translations = {'motors': 'Motor', 'trig': 'Trigger',
                           'ao': 'Acromag', 'ai': 'Acromag'}

    def __init__(self, expname, **kwargs):
        # Create our client and gather the raw information from the client
        self.qs = QuestionnaireClient(**kwargs)

        # Ensure that our user entered a valid expname
        exp_dict = self.qs.getExpName2URAWIProposalIDs()
        try:
            proposal = exp_dict[expname]
        except KeyError:
            err = '{} is not a valid experiment name.'
            raise ValueError(err.format(expname))
        run_no = 'run{}'.format(expname[-2:])
        try:
            logger.debug("Requesting list of proposals in %s", run_no)
            prop_ids = self.qs.getProposalsListForRun(run_no)
            beamline = prop_ids[proposal]['Instrument']
        # Invalid proposal id for this run
        except KeyError as exc:
            raise DatabaseError('Unable to find proposal {}'.format(proposal))\
                  from exc
        # Find if our exception gave an HTTP status code and interpret it
        except Exception as exc:
            if len(exc.args) > 1:
                status_code = exc.args[1]
            else:
                status_code = ''
            # No information found from run
            if status_code == 500:
                reason = 'No run id found for {}'.format(run_no)
            # Invalid credentials
            elif status_code == 401:
                reason = 'Invalid credentials'
            # Unrecognized error
            else:
                reason = 'Unable to find run information'
            raise DatabaseError(reason) from exc

        # Interpret the raw information into a happi structured dictionary
        self.db = dict()
        logger.debug("Requesting proposal information for %s", proposal)
        raw = self.qs.getProposalDetailsForRun(run_no, proposal)
        for table, _class in self.device_translations.items():
            # Create a regex pattern to find all the appropriate pattern match
            pattern = re.compile(r'pcdssetup-{}'
                                 r'-(\d+)-(\w+)'.format(table))
            # Search for all keys that match the device and store in a
            # temporary dictionary
            devices = dict()
            for field in raw.keys():
                match = pattern.match(field)
                if match:
                    dev_no = match.group(1)
                    # Create an empty dictionary for the specific device
                    # information
                    if dev_no not in devices:
                        devices[dev_no] = dict()
                    # Add the key information to the specific device dictionary
                    devices[dev_no][match.group(2)] = raw[field]
            # Store the devices as happi items
            if not devices:
                logger.info("No device information found under '%s'", table)
            else:
                logger.debug("Found %s devices under %s table",
                             len(devices), table)
                for num, dev_info in devices.items():
                    try:
                        post = {'name': dev_info.pop('name'),
                                'prefix': dev_info['pvbase'],
                                'beamline': beamline,
                                'type': _class,
                                # TODO: We should not assume that we are using
                                # the prefix as _id. Other backends do not make
                                # this assumption. This will require moving the
                                # _id configuration from Client to Backend
                                '_id': dev_info.pop('pvbase')}
                        # Add extraneous metadata
                        post.update(dev_info)
                        # Check that the we haven't received empty strings from
                        # the Questionnaire
                        for key in ['prefix', 'name']:
                            if not post.get(key):
                                raise Exception("Unable to create a device "
                                                " without %s".format(key))
                    except Exception:
                        logger.warning("Unable to create an object from "
                                       "Questionnaire table %s row %s",
                                       table, num)
                    else:
                        self.db[post['_id']] = post

    def initialize(self):
        """
        Can not initialize a new Questionnaire entry from API
        """
        raise NotImplementedError("The Questionnaire backend is read-only")

    def load(self):
        """
        Return the structured dictionary of information
        """
        return self.db

    def store(self, *args, **kwargs):
        """
        The current implementation of this backend is read-only
        """
        raise NotImplementedError("The Questionnaire backend is read-only")

    def save(self, *args, **kwargs):
        """
        The current implementation of this backend is read-only
        """
        raise NotImplementedError("The Questionnaire backend is read-only")

    def delete(self, _id):
        """
        The current implementation of this backend is read-only
        """
        raise NotImplementedError("The Questionnaire backend is read-only")
