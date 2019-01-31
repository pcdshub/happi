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

parser.add_argument('--path', type=str,
                    help='path to happi configuration file')
parser.add_argument('--search', nargs=argparse.REMAINDER,
                    help='search criteria: [--search] field value')
parser.add_argument('--verbose', '-v', action='store_true',
                    help='Show the degub logging stream')
parser.add_argument('--version', '-V', action='store_true',
                    help='Current version and location '
                    'of Happi installation.')

# TODO: Implement add and edit options
# parser.add_argument('--add', action='store_true', # needs work
#                    help='add a device')
# parser.add_argument('--edit', action='store_true',
#                    help='edit a device')


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

    if args.search:
        # Ensure we have an even number of search elements
        # Should always have key:value pairs
        if len(args.search) % 2 is not 0:
            raise EntryError('Search criteria should be given as key '
                             'value pair\ni.e:\n'
                             'happi --search beamline MFX stand DG1')
        # Change any numbers from strings to floats
        for i in range(len(args.search)):
            if args.search[i].replace('.', '').isnumeric():
                args.search[i] = float(args.search[i])

        # Get search criteria into dictionary for use by client
        search_args = {}
        for i in range(0, len(args.search), 2):
            search_args[args.search[i]] = args.search[i + 1]
        logger.debug('Search arguments: %r' % search_args)

        devices = client.search(**search_args)
        for dev in devices:
            dev.show_info()
        return devices


def main():
    """Execute the ``happi_cli`` with command line arguments"""
    happi_cli(sys.argv[1:])
