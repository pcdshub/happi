"""
This module defines the ``happi`` command line utility
"""
# cli.py

import argparse
import sys
import logging

from IPython import start_ipython
import coloredlogs

import happi

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
parser_search.add_argument('search_criteria', nargs='+',
                           help='search criteria: FIELD=VALUE')
parser_add = subparsers.add_parser('add', help='Add new entries')
parser_add.add_argument('--clone', default='',
                        help='Name of device to use for default parameters')
parser_edit = subparsers.add_parser('edit', help='Change existing entry')
parser_edit.add_argument('name', help='Device to edit')
parser_edit.add_argument('edits', nargs='+',
                         help='Edits of the form field=value')
parser_load = subparsers.add_parser('load',
                                    help='Open IPython terminal with '
                                         'device loaded')
parser_load.add_argument('device_names', nargs='+',
                         help='Devices to load')


def happi_cli(args):
    args = parser.parse_args(args)

    # Logging Level handling
    if args.verbose:
        shown_logger = logging.getLogger()
        level = "DEBUG"
    else:
        shown_logger = logging.getLogger('happi')
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

        # Get search criteria into dictionary for use by client
        client_args = {}
        for user_arg in args.search_criteria:
            criteria, value = user_arg.split('=', 1)
            if value.replace('.', '').isnumeric():
                logger.debug('Changed %s to float', value)
                value = float(value)
            client_args[criteria] = value

        devices = client.search(**client_args)
        if devices:
            for dev in devices:
                dev.show_info()
            return devices
        else:
            logger.error('No devices found')
    elif args.cmd == 'add':
        logger.debug('Starting interactive add')
        if args.clone:
            clone_source = client.find_device(name=args.clone)
            # Must use the same container if cloning
            response = clone_source.__class__.__name__
        else:
            logger.info('Please select a container, or press enter for generic '
                        f'Device container: {list(client.device_types.keys())}\n')
            response = input()
            if response and response not in client.device_types:
                logger.info('Invalid device container f{response}')
                return
            elif not response:
                response = 'Device'

        container = client.device_types[response]
        kwargs = {}
        for info in container.entry_info:
            valid_value = False
            while not valid_value:
                if args.clone:
                    default = getattr(clone_source, info.key)
                else:
                    default = info.default
                logger.info(f'Enter value for {info.key}, default={default}, '
                            f'enforce={info.enforce}')
                item_value = input()
                if not item_value:
                    if info.optional or args.clone:
                        logger.info(f'Selecting default value {default}')
                        item_value = default
                    else:
                        logger.info('Not an optional field!')
                        continue
                try:
                    info.enforce_value(item_value)
                    valid_value = True
                    kwargs[info.key] = item_value
                except Exception:
                    logger.info(f'Invalid value {item_value}')

        device = client.create_device(container, **kwargs)
        logger.info('Please confirm the following info is correct:')
        device.show_info()
        ok = input('y/N\n')
        if 'y' in ok:
            logger.info('Adding device')
            device.save()
        else:
            logger.info('Aborting')
    elif args.cmd == 'edit':
        logger.debug('Starting edit block')
        device = client.find_device(name=args.name)
        for edit in args.edits:
            field, value = edit.split('=', 1)
            logger.info(f'Setting {args.name}.{field} = {value}')
            setattr(device, field, value)
        device.save()
        device.show_info()
    elif args.cmd == 'load':
        logger.debug('Starting load block')
        logger.info(f'Creating shell with devices {args.device_names}')
        devices = {}
        for name in args.device_names:
            devices[name] = client.load_device(name=name)
        start_ipython(argv=['--quick'], user_ns=devices)


def main():
    """Execute the ``happi_cli`` with command line arguments"""
    happi_cli(sys.argv[1:])
