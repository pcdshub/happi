"""
This module defines the ``happi`` command line utility
"""
# cli.py

import argparse
import sys
import happi
import logging
import coloredlogs

logger = logging.getLogger(__name__)

# Argument Parser Setup
parser = argparse.ArgumentParser(description='happi command line tool')

# Optional args general to all happi operations
parser.add_argument('--path', type=str,
                    help='path to happi configuration file')
parser.add_argument('--verbose', '-v', action='store_true',
                    help='Show the degub logging stream')
parser.add_argument('--version', '-V', action='store_true',
                    help='Current version and location '
                    'of Happi installation.')
# Subparser to trigger search arguments
subparsers = parser.add_subparsers(help='Subparsers to search, add, edit',
                                   dest='command')
parser_search = subparsers.add_parser('search', help='Search the happi '
                                      'database')
HAPPI_FIELDS = ["_id", "active", "args", "beamline", "creation",
                "device_class", "kwargs", "last_edit", "macros",
                "name", "parent", "prefix", "screen", "stand",
                "system", "type", "z"]
for field in HAPPI_FIELDS:
    parser_search.add_argument('--' + field, type=str,
                               help='%s to search for' % field)


def happi_cli(args):
    args = parser.parse_args(args)

    # Logging Level handling
    if args.verbose:
        level = "DEBUG"
        shown_logger = logging.getLogger('happi')
    else:
        shown_logger = logging.getLogger()
        level = "INFO"
    coloredlogs.install(level=level, logger=shown_logger,
                        fmt='[%(asctime)s] - %(levelname)s -  %(message)s')
    logger.debug("Set logging level of %r to %r", shown_logger.name, level)

    # Version endpoint
    if args.version:
        print(f'Happi: Version {happi.__version__} from {happi.__file__}')
        return
    logger.debug('Command line arguments: %r' % args)

    client = happi.client.Client.from_config(cfg=args.path)
    logger.debug("Happi client: %r" % client)
    logger.debug('Happi command: %r' % args.command)

    if args.command == 'search':
        logger.debug("We're in the search block")

        # Get search criteria into dictionary for use by client
        args_dict = vars(args)
        logger.debug("CL args as dictionary: %r" % args_dict)

        # Filter arg_dict to just search params
        search_args = dict_filt(args_dict, HAPPI_FIELDS)
        # Remove keys in search_args whose values are 'None'
        search_args_filt = {key: value for key, value in search_args.items()
                            if value is not None}
        for key in search_args_filt.keys():
            if search_args_filt[key].replace('.', '').isnumeric():
                search_args_filt[key] = float(search_args_filt[key])

        logger.debug('Search arguments: %r' % search_args_filt)

        devices = client.search(**search_args_filt)
        if devices:
            for dev in devices:
                dev.show_info()
            return devices
        else:
            print('No devices found')


def dict_filt(start_dict, desired_keys):
    return dict([(i, start_dict[i]) for i in start_dict if i in
                set(desired_keys)])


def main():
    """Execute the ``happi_cli`` with command line arguments"""
    happi_cli(sys.argv[1:])
