"""
Backend implementation for parsing the Questionnaire
"""
import re
import logging

from psdm_qs_cli import QuestionnaireClient

from .json_db import JSONBackend
from ..errors import DatabaseError

logger = logging.getLogger(__name__)


# Declare our motor types
motor_types = {'MMS': 'pcdsdevices.epics_motor.IMS',
               'MMN': 'pcdsdevices.epics_motor.Newport',
               'MZM': 'pcdsdevices.epics_motor.PMC100'}


def guess_motor_class(prefix):
    """
    Guess the corresponding pcdsdevices.epics_motor class based on prefix

    Parameters
    ----------
    prefix : str

    Returns
    -------
    device_class : str
        Type of EpicsMotor. If not, we assume can use pcdsd
    """
    for _typ in motor_types:
        if _typ in prefix:
            return motor_types[_typ]
    return 'pcdsdevices.epics_motor.PCDSMotorBase'


class QSBackend(JSONBackend):
    """
    Questionniare Backend

    This backend connects to the LCLS questionnaire and looks at devices with
    the key pattern pcds-*-setup-*-*. These fields are then combined and turned
    into proper happi devices. The translation of table name to pcdsdevices
    class is determined by the :attr:`.device_translations` dictionary. The
    beamline is determined by looking where the proposal was submitted.

    Unlike the other backends, this one is read-only. All changes to the device
    information should be done via the web interface. Finally, in order to
    avoid duplicating any code needed to search the device database, the
    QSBackend inherits directly from JSONBackend. Many of the functions are
    unmodified with exception being that this backend merely searchs through an
    in memory dictionary while the JSONBackend reads from the file before
    searches.

    Parameters
    ----------
    run_no : int
        Desired run number i.e 16

    proposal: str
        Proposal identifier i.e "LR32"
    """
    device_translations = {'motors': 'pcdsdevices.epics_motor.EpicsMotor'}

    def __init__(self, run_no, proposal, **kwargs):
        # Create our client and gather the raw information from the client
        self.qs = QuestionnaireClient(**kwargs)

        # Ensure that our user entered a valid run number and proposal
        # identification
        run_no = 'run{}'.format(run_no)
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
        for field, _class in self.device_translations.items():
            # Create a regex pattern to find all the appropriate pattern match
            pattern = re.compile('pcdssetup-{}-'
                                 'setup-(\d+)-(\w+)'.format(field))
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
                logger.info("No device information found under '%s'", field)
            else:
                logger.debug("Found %s devices under %s table",
                             len(devices), field)
                for num, dev_info in devices.items():
                    try:
                        post = {'name': dev_info.pop('name'),
                                'prefix': dev_info['pvbase'],
                                'beamline': beamline,
                                'device_class': _class,
                                'type': 'Device',
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
                    except Exception as exc:
                        logger.warning("Unable to create a %s from "
                                       "Questionnaire row %s",
                                       _class, num)
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
