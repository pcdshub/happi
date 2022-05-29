"""
This module defines the ``happi`` command line interface.
"""
import ast
import fnmatch
import json
import logging
import os
# on import allows arrow key navigation in prompt
import readline  # noqa
import sys

import click
import coloredlogs
import prettytable

import happi

from .prompt import prompt_for_entry, transfer_container
from .utils import is_a_range, is_valid_identifier_not_keyword

logger = logging.getLogger(__name__)

version_msg = f'Happi: Version {happi.__version__} from {happi.__file__}'
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(
    help=('commands available: search, add, edit, load, update, '
          'container-registry, transfer'),
    context_settings=CONTEXT_SETTINGS
)
@click.option('--path', type=click.Path(exists=True),
              help='Provide the path to happi configuration file.')
@click.option('--verbose', '-v', is_flag=True,
              help='Show the debug logging stream.')
@click.version_option(None, '--version', '-V', message=version_msg)
@click.pass_context
def happi_cli(ctx, path, verbose):
    """Happi command line tool"""
    # Logging Level handling
    if verbose:
        shown_logger = logging.getLogger()
        level = "DEBUG"
    else:
        shown_logger = logging.getLogger('happi')
        level = "INFO"
    coloredlogs.install(level=level, logger=shown_logger,
                        fmt='[%(asctime)s] - %(levelname)s -  %(message)s')
    logger.debug("Set logging level of %r to %r", shown_logger.name, level)

    # gather client
    client = happi.client.Client.from_config(cfg=path)
    logger.debug("Happi client: %r" % client)

    # insert items into context to be passed to subcommands
    # User objects must be assigned to ctx.obj, which will be passed
    # through to new context objects
    ctx.obj = client


@happi_cli.command()
@click.option('--show_json', '-j', is_flag=True,
              help='Show results in JSON format.')
@click.option('--names', is_flag=True,
              help='Return results as whitespace-separated names.')
@click.option('--glob/--regex', 'use_glob', default=True,
              help='use glob style (default) or regex style search terms. '
              'Regex requires backslashes to be escaped (eg. at\\\\d.\\\\d)')
@click.argument('search_criteria', nargs=-1)
@click.pass_context
def search(ctx, show_json, names, use_glob, search_criteria):
    """
    Search the happi database.  SEARCH_CRITERIA take the form: field=value.
    If 'field=' is omitted, it will assumed to be 'name'.
    You may include as many search criteria as you like; these will
    be combined with ANDs.
    """
    logger.debug("We're in the search block")
    # Retrieve client
    client = ctx.obj

    # Get search criteria into dictionary for use by client
    client_args = {}
    range_list = []
    regex_list = []
    is_range = False
    for user_arg in search_criteria:
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
        if value.replace('.', '', 1).isdigit():
            logger.debug('Changed %s to float', value)
            value = str(float(value))

        if is_a_range(value):
            start, stop = value.split(',')
            start = float(start)
            stop = float(stop)
            is_range = True
            if start < stop:
                range_list += client.search_range(criteria, start, stop)
            else:
                logger.error('Invalid range, make sure start < stop')

            continue

        if use_glob:
            client_args[criteria] = fnmatch.translate(value)
        else:  # already using regex
            client_args[criteria] = value

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

    if show_json:
        json.dump([dict(res.item) for res in final_results], indent=2,
                  fp=sys.stdout)
    elif names:
        out = " ".join([res.item.name for res in final_results])
        click.echo(out)
    else:
        for res in final_results:
            res.item.show_info()

    if not final_results:
        logger.error('No devices found')
    return final_results


@happi_cli.command()
@click.option('--clone', default='',
              help='Copy the fields from an existing container. '
              'Provide the name of the item to clone.')
@click.pass_context
def add(ctx, clone):
    """Add new entries interactively."""
    logger.debug(f'Starting interactive add, {clone}')
    # retrieve client
    client = ctx.obj

    registry = happi.containers.registry
    if clone:
        clone_source = client.find_device(name=clone)
        # Must use the same container if cloning
        response = registry.entry_for_class(clone_source.__class__)
    else:
        clone_source = None
        # Keep Device at registry for backwards compatibility but filter
        # it out of new devices options
        options = os.linesep.join(
            [k for k, _ in registry.items() if k != "Device"]
        )
        ctnr_prompt = (
            'Please select a container, or press enter for generic '
            f'Ophyd Device container: {os.linesep}{options}'
            f'{os.linesep}{os.linesep}Selection'
        )
        logger.debug(ctnr_prompt)
        response = click.prompt(ctnr_prompt, default='OphydItem')
        if response and response not in registry:
            logger.info(f'Invalid device container {response}')
            return

    container = registry[response]
    logger.debug(f'Contaner selected: {container.__name__}')

    # Collect values for each field
    kwargs = {}
    for info in container.entry_info:
        item_value = prompt_for_entry(info, clone_source=clone_source)
        click.echo(f'Selecting value: {item_value}')

        try:
            info.enforce_value(item_value)
            kwargs[info.key] = item_value
        except Exception:
            logger.info(f'Invalid value {item_value}')

    device = client.create_device(container, **kwargs)
    device.show_info()
    if click.confirm('Please confirm the device info is correct'):
        logger.info('Adding device')
        device.save()
    else:
        logger.info('Aborting')


@happi_cli.command()
@click.argument('name')
@click.argument('edits', nargs=-1, type=str)
@click.pass_context
def edit(ctx, name, edits):
    """
    Change an existing entry by applying EDITS of the form: field=value
    to the item of name NAME.
    """
    # retrieve client
    client = ctx.obj

    logger.debug('Starting edit block')
    device = client.find_device(name=name)
    if len(edits) < 1:
        click.echo('No edits provided, aborting')
        raise click.Abort()

    for edit in edits:
        field, value = edit.split('=', 1)
        # validate field
        try:
            field = is_valid_identifier_not_keyword(field)
        except ValueError:
            logger.error(f'field ({field}) is not a valid keyword')
            raise click.Abort()

        # validate field depending on enforce type
        if device._info_attrs[field].enforce in (dict, list):
            # try interpreting with ast
            try:
                value = ast.literal_eval(value)
            except (ValueError, SyntaxError) as e:
                logger.error(f'Could not interpret edit ({edit}), {e}\n'
                             'Remember to escape your quotes '
                             '(e.g. {\\"key\\":\\"value\\"})')
                raise click.Abort()
        else:
            try:
                value = device._info_attrs[field].enforce_value(value)
            except ValueError:
                logger.error(f'Error enforcing type for value: {value}')
                raise click.Abort()

        # set field
        try:
            getattr(device, field)
            logger.info(f'Setting {name}.{field}: {value}')
            setattr(device, field, value)
        except Exception as e:
            logger.error(f'Could not edit {name}.{field}: {e}')
            raise click.Abort()

    device.show_info()
    if click.confirm('Please confirm the device info is correct'):
        logger.info('Editing device')
        device.save()
    else:
        logger.info('Aborting')


@happi_cli.command()
@click.argument('device_names', nargs=-1)
@click.pass_context
def load(ctx, device_names):
    """Open IPython terminal with DEVICE_NAMES loaded"""

    logger.debug('Starting load block')
    # retrieve client
    client = ctx.obj

    logger.info(f'Creating shell with devices {device_names}')
    devices = {}
    names = " ".join(device_names)
    names = names.split()
    if len(names) < 1:
        raise click.Abort()

    for name in names:
        devices[name] = client.load_device(name=name)

    from IPython import start_ipython  # noqa
    start_ipython(argv=['--quick'], user_ns=devices)


# TODO: FIgure out how to deal with json and click.  list of args doesn't
# translate exactly
@happi_cli.command()
@click.argument("json_data", nargs=-1)
@click.pass_context
def update(ctx, json_data):
    """Update happi db with JSON_DATA payload"""
    # retrieve client
    print(json_data)
    client = ctx.obj
    if len(json_data) < 1:
        raise click.Abort()

    # parse input
    input_ = " ".join(json_data).strip()
    print(json_data)
    if input_ == "-":
        items_input = json.load(sys.stdin)
    else:
        items_input = json.loads(input_)
    # insert
    for item in items_input:
        item = client.create_device(device_cls=item["type"], **item)
        exists = item["_id"] in [c["_id"] for c in client.all_items]
        client._store(item, insert=not exists)


@happi_cli.command(name='container-registry')
def container_registry():
    """Print container registry"""
    pt = prettytable.PrettyTable()
    pt.field_names = ["Container Name", "Container Class", "Object Class"]
    pt.align = "l"
    for type_, class_, in happi.containers.registry._registry.items():
        pt.add_row([type_,
                    f'{class_.__module__}.{class_.__name__}',
                    class_.device_class.default])
    click.echo(pt)


@happi_cli.command()
@click.pass_context
@click.argument("name", type=str, nargs=1)
@click.argument("target", type=str, nargs=1)
def transfer(ctx, name, target):
    """Change the container of an item (NAME) to a new container (TARGET)"""
    logger.debug('Starting transfer block')
    # retrive client
    client = ctx.obj
    # verify name and target both exist and are valid
    item = client.find_device(name=name)
    registry = happi.containers.registry
    # This is slow if dictionary is large
    target_match = [k for k, _ in registry.items() if target in k]
    if len(target_match) > 1 and name in target_match:
        target_match = [name]
    elif len(target_match) != 1:
        print(f'Target container name ({target}) not specific enough')
        raise click.Abort()

    target = happi.containers.registry._registry[target_match[0]]
    # transfer item and prompt for fixes
    transfer_container(client, item, target)


def main():
    """Execute the ``happi_cli`` with command line arguments"""
    happi_cli()
