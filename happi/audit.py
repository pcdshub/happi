"""
This module defines the ``happi audit`` command line utility
"""
from abc import ABC, abstractmethod
import logging
import os
import sys
from happi.client import Client
from happi.loader import import_class, create_arg
from happi.containers import registry
from enum import Enum, auto

logger = logging.getLogger(__name__)


def print_report_message(message):
    logger.info('='*50)
    logger.info(message.center(50, '-'))
    logger.info('='*50)


class ReportCode(Enum):
    """
    Class to define report codes
    """
    SUCCESS = auto()
    INVALID = auto()
    MISSING = auto()
    EXTRAS = auto()
    NO_CODE = auto()

    def __repr__(self):
        return '<%s.%s>' % (self.__class__.__name__, self.name)


class Command(ABC):
    """
    Blueprint for the command class
    This will be useful if all the commands are inheriting from it
    """
    @abstractmethod
    def add_args(self, parser):
        """
        Adds arguments to a parser

        Parameters
        -----------
        parser: ArgumentParser
            Parser to add arguments to
        """
        raise NotImplementedError

    @abstractmethod
    def run(self, args):
        """
        Parses the arguments given to the command.
        And handles the logic for this command

        Parameters
        -----------
            args: Namespace
        """
        raise NotImplementedError


class Audit(Command):
    """
    Audits the database for valid entries.
    """
    def __init__(self):
        self.name = 'audit'
        self.help = "Inspect a database's entries"
        self.report_code = ReportCode.NO_CODE
        self._extras = False
        self._database_path = None

    def add_args(self, cmd_parser):
        cmd_parser.add_argument(
            "--file",
            help='Path to the json file (database) to be audited. '
                 'If this option is not provided it will use the '
                 'Happi Configuration file instead.'
        )
        cmd_parser.add_argument(
            "--extras", action='store_true', default=False,
            help='Check specifically for extra attributes'
        )

    def run(self, args):
        """
        Parses the cli arguments
        """
        self._extras = args.extras

        if args.file is not None:
            self.process_database(database_path=args.file, extras=self._extras)
        else:
            """
            Validate the database defined in happi.cfg file
            """
            path_to_config = Client.find_config()

            if path_to_config:
                logger.info('Using Client cfg path %s ', path_to_config)
                db_kwargs = Client.parse_config_file(path_to_config)
                self._database_path = db_kwargs.get('path')
                if self._database_path:
                    self.process_database(database_path=self._database_path,
                                          extras=self._extras)
                else:
                    logger.error('Could not get the database path '
                                 'from the configuration file')
                    return
            else:
                logger.error('Could not find the Happi Configuration file')
                sys.exit(1)

    def process_database(self, database_path=None, extras=False):
        """
        Checks to see if a valid path to database was provided.
        If extras is True, it will check for extra attributes only, otherwise
        it will just proceed with parsing and validating the database call.
        """
        if self.validate_file(database_path):
            logger.info('Using database file at %s ', database_path)
            if extras:
                self.check_extra_attributes(database_path)
            else:
                self.parse_database(database_path)
        else:
            logger.error('The database %s file path '
                         'could not be validated', database_path)
            sys.exit(1)

    def validate_file(self, file_path):
        """
        Tests whether a path is a regular file

        Parameters
        -----------
        file_path: str
            File path to be validate

        Returns
        -------
        bool
            To indicate whether the file is a valid regular file
        """
        return os.path.isfile(file_path)

    def validate_container(self, item):
        """
        Validates container definition

        Parameters
        ----------
        item: dict
            An entry in the database
        """
        container = item.get('type')
        device = item.get('name')
        if container and container not in registry:
            logger.error('Invalid device container: %s for device %s',
                         container, device)
            return self.report_code.INVALID
        elif not container:
            logger.error('No container provided for %s', device)
            return self.report_code.MISSING

        # seems like the container has been validated
        return self.report_code.SUCCESS

    def validate_args(self, item):
        """
        Validates the args of an item
        """
        return [create_arg(item, arg) for arg in item.args]

    def validate_kwargs(self, item):
        """
        Validates the kwargs of an item
        """
        return dict((key, create_arg(item, val))
                    for key, val in item.kwargs.items())

    def validate_import_class(self, item=None):
        """
        Validate the device_class of an item

        Parameters
        ----------
        item: dict
            An entry in the database
        """
        device_class = item.get('device_class')
        device = item.get('name')

        if not device_class:
            logger.warning('Detected a None value for %s. '
                           'The device_class cannot be None', device)
            return self.report_code.MISSING
        if '.' not in device_class:
            logger.warning('Device class invalid %s for item %s',
                           device_class, item)
            return self.report_code.INVALID

        try:
            import_class(device_class)
            return self.report_code.SUCCESS
        except Exception as e:
            logger.warning('For device: %s, %s. Either %s is '
                           'misspelled or %s is not part of the '
                           'python environment', device, e,
                           device_class, device_class)
            return (self.report_code.INVALID)

    def validate_enforce(self, item):
        """
        Validates using enforce_value() from EntryInfo class
        If the attributes are malformed the entry = container(**item)
        will fail, thus the enforce_value() will only apply to the
        ones that were successfully initialized

        Parameters
        ----------
        item: dict
            An entry in the database
        """
        container = registry[item.get('type')]
        name = item.get('name')
        if container:
            for info in container.entry_info:
                try:
                    info.enforce_value(dict(item)[info.key])
                    return self.report_code.SUCCESS
                except Exception as e:
                    logger.info('Invalid value %s, %s', info, e)
                    return self.report_code.INVALID
        else:
            logger.warning('Item %s is missing the container', name)
            return self.report_code.MISSING

    def check_extra_attributes(self, database_path):
        """
        Checks the entries that have extra attributes

        Parameters
        ----------
        database_path: str
            Path to the database to be validated

        """
        client = Client(path=database_path)
        items = client.all_items

        print_report_message('EXTRA ATTRIBUTES')
        for item in items:
            self.validate_extra_attributes(item)

    def validate_extra_attributes(self, item):
        """
        Validate items that have extra attributes

        Parameters
        ----------
        item: dict
            An entry in the database
        """
        attr_list = []
        extr_list = ['creation', 'last_edit', '_id', 'type']

        for (key, value), s in zip(item.items(), item.entry_info):
            attr_list.append(s.key)

        key_list = [key for key, value in item.items()]
        diff = set(key_list) - set(attr_list) - set(extr_list)
        if diff:
            logger.warning('Device %s has extra attributes %s',
                           item.name, diff)
            return self.report_code.EXTRAS

        return self.report_code.SUCCESS

    def parse_database(self, database_path):
        """
        Validates if an entry is a valid entry in the database

        Parameters
        ----------
        database_path: str
            Path to the database to be validated

        """
        client = Client(path=database_path)
        items = client.all_items

        print_report_message('VALIDATING ENTRIES')
        # this will fail to validate because the missing list will have
        # the defaults match...... which is not good.....
        # for example: if Default for class_devices: pcdsdevices.pimm.Vacuum
        # and the default is used, then this will not work fine....
        # we might want to do something like this maybe in _validate_device:
        # missing = [info.key for info in device.entry_info
        #   if not info.optional and
        #   info.default == getattr(device, info.key) and info.default == None]
        client.validate()

        if items:
            print_report_message('VALIDATING ARGS & KWARGS')
            for item in items:
                args = self.validate_args(item)
                kwargs = self.validate_kwargs(item)
                try:
                    cls = import_class(item.device_class)
                    cls(*args, **kwargs)
                except Exception as e:
                    logger.warning('When validating args and kwargs, '
                                   'the item %s errored with: %s', item, e)

        else:
            logger.error('Cannot run a set of tests becase the '
                         'items could not be loaded.')

        print_report_message('VALIDATING ENFORCE VALUES')
        for item in client.backend.all_devices:
            it = client.find_document(**item)
            self.validate_enforce(it)

        # validate import_class
        print_report_message('VALIDATING DEVICE CLASS')
        for item in items:
            self.validate_import_class(item)

        print_report_message('VALIDATING CONTAINER')
        for item in client.backend.all_devices:
            it = client.find_document(**item)
            self.validate_container(it)
