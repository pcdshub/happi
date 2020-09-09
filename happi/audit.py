"""
This module defines the ``happi audit`` command line utility

If the --file option is not provided, then it will take the path from
Happpi configuration file using the Client.find_config method,
otherwiwe it will use the path specified after --file
"""
from abc import ABCMeta, abstractmethod
from configparser import ConfigParser
import logging
import os
import sys
import subprocess
import re
from happi.client import Client
from happi.loader import import_class, fill_template
from happi.containers import registry
from happi.item import EntryInfo

logger = logging.getLogger(__name__)


class Command(object, metaclass=ABCMeta):
    """
    Bluprint for the command class
    This will be useful if all the commands are inheriting from it
    """
    def __init__(self, name, summary):
        self.name = name
        self.summary = summary

    @abstractmethod
    def add_args(self, args):
        raise NotImplementedError
        return

    @abstractmethod
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
        self._all_devices = set()
        self._all_items = []

    def add_args(self, cmd_parser):
        cmd_parser.add_argument(
            "--file", help='Path to the json file (database) to be audited'
        )
        cmd_parser.add_argument(
            "--extras", action='store_true', default=False,
            help='Check specifically for extra attributes'
        )

    def run(self, args):
        """
        Validate the database passed in with --file option
        """
        if args.file is not None:
            if self.validate_file(args.file):
                logger.info('Using database file at %s ', args.file)
                if args.extras:
                    self.check_extra_attributes(args.file)
                else:
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
                    if args.extras:
                        self.check_extra_attributes(database_path)
                    else:
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

    def get_device_class(self, item):
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
                packages = device_class.rsplit('.')
                package = packages[0]
                self._all_devices.add(package)
                self._all_items.append(item)

    def validate_import_class(self):
        """
        Validate the device_class of an item
        """
        for item in self._all_items:
            device_class = item.get('device_class')
            dev_cls = device_class.rsplit('.')[0]
            device = item.get('name')

            if dev_cls in self._all_devices:
                # has been tested agains PyPi and was found there
                try:
                    import_class(device_class)
                except ImportError as e:
                    logger.warning('For device: %s, %s. Either %s is '
                                   'misspelled or %s is not part of the '
                                   'python environment', device, e,
                                   device_class, dev_cls)
            elif dev_cls and dev_cls not in self._all_devices:
                logger.warning('Provided wrong device/module name: %s. '
                               'This module does not exist in PyPi', dev_cls)

    def validate_extra_attributes(self, item):
        """
        Validate items that have extra attributes
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

    def search_pip_package(self, package):
        """
        Checks to see if the package is on pypi

        Parameters
        -----------
        package: str
            Name of the package to check

        Returns
        --------
            bool
                To indicate if the package was found or not
        """
        process = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, encoding='utf-8')
        try:
            arguments = ['pip', 'search', package]
            command = ' '.join(arguments)

            out, err = process.communicate(command)

            # the output of 'pip search' will give all the fuzzy searches
            # we only care if the exact package name is there
            the_match = re.compile(package)
            if re.match(the_match, out):
                return True
            else:
                return False
        except Exception as e:
            logger.warning(e)
            if process:
                process.kill()

    def validate_enforce(self, item):
        """
        Validates using enforce_value() from EntryInfo class
        If the attributes are malformed the entry = contaienr(**item)
        will fail, thous the enforce_value() will only apply to the
        ones that were successfully initialized
        """
        container = registry[item.get('type')]
        item_name = item.get('name')
        try:
            entry = container(**item)
        except Exception as e:
            logger.warning('For device %s, %s', item_name, e)
        else:
            for info in entry.entry_info:
                try:
                    info.enforce_value(entry.get(info.key))
                except Exception as e:
                    logger.warning(e)

    def print_report_message(self, message):
        logger.info('')
        logger.info('--------- %s ---------', message)
        logger.info('')

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

        self.print_report_message('EXTRA ATTRIBUTES')
        for item in items:
            self.validate_extra_attributes(item)

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
            self.print_report_message('VALIDATING ARGS & KWARGS')
            for item in items:
                self.validate_args(item)
                self.validate_kwargs(item)
        else:
            logger.error('Cannot run a set of tests becase the '
                         'items could not be loaded.')

        for item in client.backend.all_devices:
            it = client.find_document(**item)
            self.validate_enforce(it)
            self.get_device_class(it)

        self.print_report_message('VALIDATE DEVICE MODULE EXISTS IN PYPI')
        if self._all_devices:
            temp_set = self._all_devices.copy()
            for package in self._all_devices:
                is_package_found = self.search_pip_package(package)
                if is_package_found:
                    logger.info('%s was found in PyPi', package)
                else:
                    # maybe a wrong device name was provided because
                    # it does not exit
                    logger.info('%s does not exit in PyPi', package)
                    temp_set.remove(package)
            self._all_devices = temp_set
            # validate import_class
            self.print_report_message('VALIDATING DEVICE CLASS')
            self.validate_import_class()

        self.print_report_message('VALIDATING CONTAINER')
        for item in client.backend.all_devices:
            it = client.find_document(**item)
            self.validate_container(it)
