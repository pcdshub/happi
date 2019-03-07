"""
This module defines the ``happi`` command line utility
"""
# cli.py

import argparse
import sys
import happi
import logging
import coloredlogs
from .errors import EntryError

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
                                   dest='cmd')
parser_search = subparsers.add_parser('search', help='Search the happi '
                                      'database')
parser_search.add_argument('search_criteria', nargs=argparse.REMAINDER,
                           help='search criteria: FIELD VALUE')


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
    logger.debug('Happi command: %r' % args.cmd)

    if args.cmd == 'search':
        logger.debug("We're in the search block")

        # Ensure we have an even number of search elements
        # Should always have key:value pairs
        if len(args.search_criteria) % 2 is not 0:
            raise EntryError('Search criteria should be given as key '
                             'value pair\ni.e:\n'
                             'happi search beamline MFX stand DG1')

        # Convert any numbers from strings to floats
        for i in range(len(args.search_criteria)):
            if args.search_criteria[i].replace('.', '').isnumeric():
                args.search_criteria[i] = float(args.search_criteria[i])

        # Get search criteria into dictionary for use by client
        client_args = {}
        for i in range(0, len(args.search_criteria), 2):
            client_args[args.search_criteria[i]] = args.search_criteria[i+1]

        devices = client.search(**client_args)
        if devices:
            for dev in devices:
                dev.show_info()
            return devices
        else:
            print('No devices found')


def main():
    """Execute the ``happi_cli`` with command line arguments"""
    happi_cli(sys.argv[1:])
