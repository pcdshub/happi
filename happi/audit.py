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

# For back-compat to <py3.7
try:
    from re import Pattern
except ImportError:
    from re import _pattern_type as Pattern


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
            logger.info('Using database file at %s ', args.file)
            if self.validate_file(args.file):
                self.parse_database(args.file)
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

    # TODO this is probably not needed, it assumes only json database...
    # but keep it here for reference for now
    # def parse_database(self, database_path):
    #     """
    #     Goes through an entire database and parses
    #     all the entries

    #     Parameters
    #     -----------
    #     database_path: str
    #         Path to the database to be validated
    #     """
    #     # check for an empty database???
    #     # check for an invalid file
    #     # we are assuming
    #     registry = happi.containers.registry
    #     with open(database_path) as f:
    #         data = json.loads(f.read())
    #         for key, value in data.items():
    #             # here i have to also check if the type is
    #             # correct, and if it has a type???
    #             try:
    #                 container = registry[value.get('type')]
    #                 logger.info('Container %s', container)
    #             except Exception as ex:
    #                 logger.exception('Something went wrong with '
    #                                  'getting the type of the item: %s', ex)
    #             self.validate_item(database_path, container, value)

    def validate_mandatory_info(self, item):
        for info in item.entry_info:
            # if it is not optional, it should probably never be None
            if not info.optional and item.get(info.key) is None:
                logger.info('Entry %s must not have None for '
                            'a mandatory entry: %s', item, info)

    def validate_enforce(self, item):
        for info in item.entry_info:
            value = item.get(info.key)
            if isinstance(info.enforce, type):
                if info.enforce == str:
                    # check the values that are enforced to be strings
                    # TODO - not working for all items, if i have a number
                    # inserted into an attribute where it should be string
                    # this will still consider it as string.... not what i want
                    if (not isinstance(value, str) and (value is not None) and
                       info.default is not None):
                        logger.info('The %s did not match the enforced type '
                                    '%s for the entry: %s. Current value: %s',
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

            # check the values that are enforced with regex
            elif isinstance(info.enforce, Pattern):
                if not info.enforce.match(str(value)):
                    logger.info('The %s did not match the enforced pattern '
                                '%s for the entry: %s. Current value: %s',
                                info, info.enforce, item, value)

    def parse_database(self, database_path):
        """
        Validates if an entry is a valid entry in the database

        Parameters
        ----------
        database_path: str
            Path to the database to be validated

        """
        it = None
        client = Client(path=database_path)
        for item in client.backend.all_devices:
            items = client.find_document(**item)
            try:
                # try to instantiate so you can have access to entry_info
                it = client.create_device(items['type'], **items)
                self.validate_mandatory_info(it)
                self.validate_enforce(it)
            except Exception:
                # TODO handle these guys differently...
                logger.info('Could not create a device.....')

        # TODO if using the all_items I run
        # into exceptions and can't look at all the devices
        # items = client.all_items
        # for item in items:
        #   self.validate_mandatory_info(item)
        #   self.validate_enforce(item)
