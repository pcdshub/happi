"""
This module defines the ``happi audit`` command line utility

If the --file option is not provided, then it will take the path from
Happpi configuration file using the Client.find_config method,
otherwiwe it will use the path specified after --file
"""
from configparser import ConfigParser
import json
import logging
import os
import sys

import happi

from happi.client import Client


logger = logging.getLogger(__name__)


class Command(object):
    """
    Bluprint for the command class
    This will be useful if all the commands are inhering from it
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
        """
        return os.path.isfile(file_path)

    def parse_database(self, database_path):
        """
        Goes through an entire database and validates
        all the entries there
        """
        registry = happi.containers.registry
        with open(database_path) as f:
            data = json.loads(f.read())
            for key, value in data.items():
                # here i have to also check if the type is
                # correct, and if it has a type???
                container = registry[value.get('type')]
                logger.debug('Container %s ', container)

    def validate_item(self, container, item_list):
        try:
            #  to validate
            pass
        except Exception as e:
            logger.error(e)
