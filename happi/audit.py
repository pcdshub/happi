"""
This module defines the ``happi audit`` command line utility

If the --file option is not provided, then it will take the path from
Happpi configuration file using the Client.find_config method,
otherwiwe it will use the path specified after --file
"""
from configparser import ConfigParser
import logging
import os
import sys
from happi.client import Client
from happi.loader import import_class, fill_template
from happi.containers import registry

logger = logging.getLogger(__name__)


class Command(object):
    """
    Bluprint for the command class
    This will be useful if all the commands are inheriting from it
    """
    def __init__(self, name, summary):
        self.name = name
        self.summary = summary

    def add_args(self, args):
        raise NotImplementedError
        return

    def run(self, **kwargs):
        raise NotImplementedError
        return


class Audit(Command):
    """
    Audits the database for valid entries.
    """
    def __init__(self):
        self.name = 'audit'
        self.help = "Inspect a database's entries"

    def add_args(self, cmd_parser):
        cmd_parser.add_argument(
            "--file", help='Path to the json file (database) to be audited'
        )

    def run(self, args):
        """
        Validate the database passed in with --file option
        """
        if args.file is not None:
            if self.validate_file(args.file):
                logger.info('Using database file at %s ', args.file)
                self.parse_database(args.file)
            else:
                logger.error('Probably provided a wrong path or filename')
        else:
            """
            Validate the database defined in happi.cfg file
            """
            path_to_config = Client.find_config()
            if path_to_config:
                logger.info('Using Client cfg path %s ', path_to_config)
                config = ConfigParser()
                config.read(path_to_config)
                try:
                    database_path = config.get('DEFAULT', 'path')
                except Exception as e:
                    logger.error('Error when trying '
                                 'to get database path %s', e)
                    return
                if self.validate_file(database_path):
                    logger.info('Using database file at %s ', database_path)
                    self.parse_database(database_path)
                else:
                    logger.error('The database %s file path '
                                 'could not be validated', database_path)
                    sys.exit(1)
            else:
                logger.error('Could not find the Happi Configuration file')
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
        """
        container = item.get('type')
        device = item.get('name')
        if container and container not in registry:
            logger.warning('Invalid device container: %s for device %s',
                           container, device)
        elif not container:
            logger.warning('No container provided for %s', device)

    def validate_args(self, item):
        """
        Validates the args of an item
        """
        [self.create_arg(item, arg) for arg in item.args]

    def validate_kwargs(self, item):
        """
        Validates the kwargs of an item
        """
        dict((key, self.create_arg(item, val))
             for key, val in item.kwargs.items())

    def create_arg(self, item, arg):
        """
        Function borrowed from loader to create
        correctly typed arguments from happi information
        """
        if not isinstance(arg, str):
            return arg
        try:
            return fill_template(arg, item, enforce_type=True)
        except Exception as e:
            logger.warning('Probably provided invalid argument: %s for %s, %s',
                           arg, item.name, e)

    def validate_device_class(self, item):
        """
        Validates device_class field
        """
        device_class = item.get('device_class')
        device = item.get('name')
        if not device_class:
            logger.warning('Detected a None vlaue for %s. '
                           'The device_class cannot be None', device)
        else:
            try:
                mod, cls = device_class.rsplit('.', 1)
            except (Exception, ValueError) as e:
                logger.warning('Wrong device name format: %s for %s, %s',
                               device_class, device, e)
            else:
                try:
                    import_class(device_class)
                except ImportError as ex:
                    logger.warning(ex)

    def validate_enforce(self, entry, item):
        for (key, value), info in zip(item.items(), entry.entry_info):
            # print(f'item_______ {value}')
            # print(type(value))
            # print(info.enforce)
            pass

        for info in entry.entry_info:
            value = entry.get(info.key)

            if (value is None and info.default is None) or info.enforce:
                return
            elif isinstance(info.enforce, type):
                if info.enforce == str:
                    # check the values that are enforced to be strings
                    # TODO - not working for all items, if i have a number
                    # inserted into an attribute where it should be string
                    # this will still consider it as string.... not what i want
                    if (not isinstance(value, str) and (value is not None) and
                       info.default is not None):
                        logger.warning('The %s did not match the enforced type'
                                       ' %s for the entry: %s. Provided: %s',
                                       info, info.enforce, item, value)
                if info.enforce == float:
                    # check the values that are enforced to be floats
                    # TODO - this is not going to work here, because
                    # even if i have something like '343.43' for z value
                    # where it has quotes and inserted as string basically
                    # this will still work and not consider it a bad entry
                    print(f'The ones that are floats: {value}')
                    if (not isinstance(value, float)):
                        logger.info('The %s did not match the enforced type '
                                    '%s for the entry: %s. Current value: %s',
                                    info, info.enforce, item, value)
                if info.enforce == list:
                    # check the values that are enforced to be lists
                    pass
                if info.enforce == dict:
                    pass
                    # check the values that are enforced to be dictionaries
                if info.enforce == bool:
                    pass
                    # check the values that are enforced to be boolean

    def print_report_message(self, message):
        logger.info('')
        logger.info('--------- %s ---------', message)
        logger.info('')

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

        self.print_report_message('VALIDATING ENTRIES')
        client.validate()

        self.print_report_message('VALIDATING ARGS AND KWARGS')
        for item in items:
            self.validate_args(item)
            self.validate_kwargs(item)
            pass

        # TODO: what to do here???....
        # for entr, item in zip(items, client.backend.all_devices):
        #     #self.validate_enforce(entr, item)
        #     pass

        self.print_report_message('VALIDATING DEVICE CLASS')
        for item in client.backend.all_devices:
            it = client.find_document(**item)
            self.validate_device_class(it)

        self.print_report_message('VALIDATING CONTAINER')
        for item in client.backend.all_devices:
            it = client.find_document(**item)
            self.validate_container(it)
