"""
This module defines the ``happi`` command line interface.
"""
import argparse
import fnmatch
import json
import logging
import os
import sys

import coloredlogs

import happi

from .utils import is_a_range

logger = logging.getLogger(__name__)


def get_parser():
    """Defines HAPPI shell commands."""
    # Argument Parser Setup
    parser = argparse.ArgumentParser(description='Happi command line tool')

    # Optional args general to all happi operations
    parser.add_argument('--path', type=str,
                        help='Provide the path to happi configuration file.')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show the debug logging stream.')
    parser.add_argument('--version', '-V', action='store_true',
                        help='Show the current version and location of Happi '
                             'installation.')
    # Subparser to trigger search arguments
    subparsers = parser.add_subparsers(help='Subcommands used to search, add, '
                                       'edit, or load entries', dest='cmd')
    parser_search = subparsers.add_parser('search', help='Search the happi '
                                          'database.')
    parser_search.add_argument('--json', action='store_true',
                               help='Show results in JSON format.')
    parser_search.add_argument('search_criteria', nargs='+',
                               help='Search criteria of the form: '
                               'field=value. If "field=" is omitted, it will '
                               'be assumed to be "name". You may include as '
                               'many search criteria as you like; these will '
                               'be combined swith ANDs.')
    parser_add = subparsers.add_parser('add',
                                       help='Add new entries interactively.')
    parser_add.add_argument('--clone', default='',
                            help='Copy the fields from an existing container. '
                                 'Provide the name of the item to clone.')
    parser_edit = subparsers.add_parser('edit',
                                        help='Change an existing entry.')
    parser_edit.add_argument('name', help='Name of the item to edit')
    parser_edit.add_argument('edits', nargs='+',
                             help='Edits of the form: field=value')
    parser_load = subparsers.add_parser('load',
                                        help='Open IPython terminal with a '
                                        'given device loaded.')
    parser_load.add_argument('device_names', nargs='+',
                             help='The names of one or more devices to load')
    parser_update = subparsers.add_parser("update",
                                          help="Update happi db "
                                          "with JSON payload.")
    parser_update.add_argument("json", help="JSON payload.",
                               default="-", nargs="*")
    return parser


def happi_cli(args):
    parser = get_parser()
    # print happi usage if no arguments are provided
    if not args:
        parser.print_usage()
        return
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
        range_list = []
        regex_list = []
        is_range = False
        for user_arg in args.search_criteria:
            is_range = False
            if '=' in user_arg:
                criteria, value = user_arg.split('=', 1)
            else:
                criteria = 'name'
                value = user_arg
            if criteria in client_args:
                logger.error(
                    'Received duplicate search criteria %s=%r (was %r)',
                    criteria, value, client_args[criteria]
                )
                return
            if value.replace('.', '').isnumeric():
                logger.debug('Changed %s to float', value)
                value = str(float(value))

            if is_a_range(value):
                start, stop = value.split(',')
                start = float(start)
                stop = float(stop)
                is_range = True
                if start < stop:
                    range_list = client.search_range(criteria, start, stop)
                else:
                    logger.error('Invalid range, make sure start < stop')

            # skip the criteria for range values
            # it won't be a valid criteria for search_regex()
            if is_range:
                pass
            else:
                client_args[criteria] = fnmatch.translate(value)

        regex_list = client.search_regex(**client_args)
        results = regex_list + range_list

        # find the repeated items
        res_size = len(results)
        repeated = []
        for i in range(res_size):
            k = i + 1
            for j in range(k, res_size):
                if results[i] == results[j] and results[i] not in repeated:
                    repeated.append(results[i])

        # we only want to return the ones that have been repeated when
        # they have been matched with both search_regex() & search_range()
        if repeated:
            final_results = repeated
        elif regex_list and not is_range:
            # only matched with search_regex()
            final_results = regex_list
        elif range_list and is_range:
            # only matched with search_range()
            final_results = range_list
        else:
            final_results = []

        if args.json:
            json.dump([dict(res.item) for res in final_results], indent=2,
                      fp=sys.stdout)
        else:
            for res in final_results:
                res.item.show_info()

        if not final_results:
            logger.error('No devices found')
        return final_results
    elif args.cmd == 'add':
        logger.debug('Starting interactive add')
        registry = happi.containers.registry
        if args.clone:
            clone_source = client.find_device(name=args.clone)
            # Must use the same container if cloning
            response = registry.entry_for_class(clone_source.__class__)
        else:
            # Keep Device at registry for backwards compatibility but filter
            # it out of new devices options
            options = os.linesep.join(
                [k for k, _ in registry.items() if k != "Device"]
            )
            logger.info(
                'Please select a container, or press enter for generic '
                'Ophyd Device container: %s%s', os.linesep, options
            )
            response = input()
            if response and response not in registry:
                logger.info('Invalid device container f{response}')
                return
            elif not response:
                response = 'OphydItem'

        container = registry[response]
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
        is_invalid_field = False
        for edit in args.edits:
            field, value = edit.split('=', 1)
            try:
                getattr(device, field)
                logger.info('Setting %s.%s = %s', args.name, field, value)
                setattr(device, field, value)
            except Exception as e:
                is_invalid_field = True
                logger.error('Could not edit %s.%s: %s', args.name, field, e)
        if is_invalid_field:
            sys.exit(1)
        device.save()
        device.show_info()
    elif args.cmd == 'load':
        logger.debug('Starting load block')
        logger.info(f'Creating shell with devices {args.device_names}')
        devices = {}
        for name in args.device_names:
            devices[name] = client.load_device(name=name)

        from IPython import start_ipython  # noqa
        start_ipython(argv=['--quick'], user_ns=devices)
    elif args.cmd == "update":
        # parse input
        input_ = " ".join(args.json).strip()
        if input_ == "-":
            items_input = json.load(sys.stdin)
        else:
            items_input = json.loads(input_)
        # insert
        for item in items_input:
            item = client.create_device(device_cls=item["type"], **item)
            exists = item["_id"] in [c["_id"] for c in client.all_items]
            client._store(item, insert=not exists)


def main():
    """Execute the ``happi_cli`` with command line arguments"""
    happi_cli(sys.argv[1:])
