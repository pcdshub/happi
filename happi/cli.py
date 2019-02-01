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
parser_search.add_argument('--_id', type=str,
                           help='_id (prefix) to search for')
parser_search.add_argument('--active', type=str,
                           help='true or false')
parser_search.add_argument('--args', type=list,
                           help='args to search for')
parser_search.add_argument('--beamline', type=str,
                           help='beamline to search for')
# NOTE: Below may not work - multiple words
parser_search.add_argument('--creation', type=str,
                           help="creation date - Ex: "
                           "'Tue Feb 27 10:41:25 2018'")
parser_search.add_argument('--device_class', type=str,
                           help="device_class to search for - Ex: "
                           "'pcdsdevices.device_types.Slits'")
parser_search.add_argument('--kwargs', type=dict,
                           help='kwargs to search for')
# NOTE: Also may not work - see '--creation'
parser_search.add_argument('--last_edit', type=str,
                           help='Date of last edit - '
                           'same format as creation')
parser_search.add_argument('--macros', type=str,
                           help='macros to search for')
parser_search.add_argument('--name', type=str,
                           help='name to search for')
parser_search.add_argument('--parent', type=str,
                           help='parent to search for')
parser_search.add_argument('--prefix', type=str,
                           help='prefix to search for')
parser_search.add_argument('--screen', type=str,
                           help='screen to search for')
parser_search.add_argument('--stand', type=str,
                           help='stand to search for')
parser_search.add_argument('--system', type=str,
                           help='system to search for')
parser_search.add_argument('--type', type=str,
                           help='type to search for')
parser_search.add_argument('--z', type=float,
                           help='z to search for')


def happi_cli(args):
    args = parser.parse_args(args)
    # NOTE: Below likely not all fields, gotta get catch 'em all
    HAPPI_FIELDS = ["_id", "active", "args", "beamline", "creation",
                    "device_class", "kwargs", "last_edit", "macros",
                    "name", "parent", "prefix", "screen", "stand",
                    "system", "type", "z"]

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

        logger.debug('Search arguments: %r' % search_args_filt)

        devices = client.search(**search_args_filt)
        for dev in devices:
            dev.show_info()
        return devices


def dict_filt(start_dict, desired_keys):
    return dict([(i, start_dict[i]) for i in start_dict if i in
                set(desired_keys)])


def main():
    """Execute the ``happi_cli`` with command line arguments"""
    happi_cli(sys.argv[1:])
