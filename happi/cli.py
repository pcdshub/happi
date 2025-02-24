"""
This module defines the ``happi`` command line interface.
"""
from __future__ import annotations

import ast
import dataclasses
import fnmatch
import importlib
import inspect
import json
import logging
import os
# on import allows arrow key navigation in prompt
import readline  # noqa
import subprocess
import sys
import time
from contextlib import contextmanager
from cProfile import Profile
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import click
import coloredlogs
import platformdirs
import prettytable

import happi
from happi.errors import SearchError

from .audit import audit as run_audit
from .audit import (checks, find_unfilled_mandatory_info,
                    find_unfilled_optional_info)
from .prompt import prompt_for_entry, transfer_container
from .utils import is_a_range, is_number, is_valid_identifier_not_keyword

logger = logging.getLogger(__name__)

version_msg = f'Happi: Version {happi.__version__} from {happi.__file__}'
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def get_happi_client_from_config(path):
    # gather client
    try:
        client = happi.client.Client.from_config(path)
        logger.debug("Happi client: %r" % client)
        # insert items into context to be passed to subcommands
        # User objects must be assigned to ctx.obj, which will be passed
        # through to new context objects
        return client
    except OSError:
        logger.debug("Happi configuration not found.")


@click.group(
    help=('The happi command-line interface, used to view and manipulate '
          'device databases'),
    context_settings=CONTEXT_SETTINGS
)
@click.option('--path', type=click.Path(exists=True),
              help='Provide the path to happi configuration file. '
                   'Will default to the file stored in the HAPPI_CFG '
                   'environment variable.')
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

    ctx.obj = path

    # Cleanup tasks related to loaded devices
    @ctx.call_on_close
    def device_cleanup():
        pyepics_cleanup()
        ophyd_cleanup()


@happi_cli.command()
@click.option('--show_json', '--json', '-j', is_flag=True,
              help='Show results in JSON format.')
@click.option('--names', is_flag=True,
              help='Return results as whitespace-separated names.')
@click.option('--glob/--regex', 'use_glob', default=True,
              help='use glob style (default) or regex style search terms. '
              r'Regex requires backslashes to be escaped (eg. at\\d.\\d)')
@click.argument('search_criteria', nargs=-1)
@click.pass_context
def search(
    ctx: click.Context,
    show_json: bool,
    names: bool,
    use_glob: bool,
    search_criteria: tuple[str]
):
    """
    Search the happi database.  SEARCH_CRITERIA take the form: field=value.
    If 'field=' is omitted, it will assumed to be 'name'.
    You may include as many search criteria as you like; these will
    be combined with ANDs.
    """
    logger.debug("We're in the search block")

    final_results = search_parser(
        client=get_happi_client_from_config(ctx.obj),
        use_glob=use_glob,
        search_criteria=search_criteria,
    )
    if not final_results:
        return []

    # Final processing for output
    if show_json:
        json.dump([dict(res.item) for res in final_results], indent=2,
                  fp=sys.stdout)
    elif names:
        out = " ".join([res.item.name for res in final_results])
        click.echo(out)
    else:
        for res in final_results:
            res.item.show_info()

    return final_results


def search_parser(
    client: happi.Client,
    use_glob: bool,
    search_criteria: Iterable[str],
) -> list[happi.SearchResult]:
    """
    Parse the user's search criteria and return the search results.

    ``search_criteria`` must be a list of key=value strings.
    If key is omitted, it will be assumed to be "name".

    Parameters
    ----------
    client : Client
        The happi client that we'll be doing searches in.
    use_glob : bool
        True if we're using glob matching, False if we're using
        regex matching.
    search_criteria : list of str
        The user's search selection from the command line.

    Raises
    ------
    click.ClickException
        Thrown if search criteria are invalid.
    """
    # Get search criteria into dictionary for use by client
    client_args: Dict[str, Any] = {}
    range_set = set()
    regex_list = []
    range_found = False

    with client.retain_cache_context():
        for user_arg in search_criteria:
            if '=' in user_arg:
                criteria, value = user_arg.split('=', 1)
            else:
                criteria = 'name'
                value = user_arg
            if criteria in client_args:
                raise click.ClickException(
                    f"Received duplicate search criteria {criteria}={value!r} "
                    f"(was {client_args[criteria]!r})"
                )

            if is_a_range(value):
                start_str, stop_str = value.split(',')
                start = float(start_str)
                stop = float(stop_str)
                if start < stop:
                    new_range_list = client.search_range(criteria, start, stop)
                else:
                    raise click.ClickException('Invalid range, make sure start < stop')

                if not range_found:
                    # if first range, just replace
                    range_found = True
                    range_set = set(new_range_list)
                else:
                    # subsequent ranges, only take intersection
                    range_set = set(new_range_list) & set(range_set)

                if not range_set:
                    # we have searched via a range query.  At this point
                    # no matches, or intesection is empty. abort early
                    logger.error("No items found")
                    return []

                continue

            elif is_number(value):
                if float(value) == int(float(value)):
                    # value is an int, allow the float version (optional .0)
                    logger.debug(f'looking for int value: {value}')
                    value = f'^{int(float(value))}(\\.0+$)?$'

                    # don't translate from glob
                    client_args[criteria] = value
                    continue
                else:
                    value = str(float(value))
            else:
                logger.debug('Value %s interpreted as string', value)

            if use_glob:
                client_args[criteria] = fnmatch.translate(value)
            else:  # already using regex
                client_args[criteria] = value

        regex_list = client.search_regex(**client_args)

    # Gather final results
    final_results = []
    if regex_list and not range_set:
        # only matched with one search_regex()
        final_results = regex_list
    elif range_set and not regex_list:
        # only matched with search_range()
        final_results = list(range_set)
    elif range_set and regex_list:
        # find the intersection between regex_list and range_list
        final_results = list(range_set & set(regex_list))
    else:
        logger.debug('No regex or range items found')

    if not final_results:
        logger.error('No items found')
    return final_results


@happi_cli.command()
@click.option('--clone', default='',
              help='Copy the fields from an existing container. '
              'Provide the name of the item to clone.')
@click.pass_context
def add(ctx, clone: str):
    """Add new entries or copy existing entries."""
    logger.debug(f'Starting interactive add, {clone}')
    # retrieve client
    client = get_happi_client_from_config(ctx.obj)

    registry = happi.containers.registry
    if clone:
        clone_source = client.find_item(name=clone)
        # Must use the same container if cloning
        response = registry.entry_for_class(clone_source.__class__)
    else:
        clone_source = None
        # Keep Device at registry for backwards compatibility but filter
        # it out of new item options
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
            raise click.ClickException(f'Invalid item container {response}')

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

    item = client.create_item(container, **kwargs)
    item.show_info()
    if click.confirm('Please confirm the item info is correct'):
        logger.info('Adding item')
        item.save()
    else:
        logger.info('Aborting')


@happi_cli.command()
@click.argument('name', type=str)
@click.pass_context
def copy(ctx, name):
    """
    Copy the item NAME.

    Simply wraps ``happi add --clone``
    """
    ctx.invoke(add, clone=name)


@happi_cli.command()
@click.argument('name', type=str)
@click.pass_context
def delete(ctx, name: str):
    """
    Delete an existing entry.  Only accepts exact names
    """
    client = get_happi_client_from_config(ctx.obj)
    try:
        item = client.find_item(name=name)
    except SearchError as e:
        raise click.ClickException(f'Could not find item ({name}): {e}')

    item.show_info()
    if click.confirm('Are you sure you want to delete this entry? \n'
                     'Remember you can mark an entry as inactive with \n'
                     '"happi edit my_device_name active=false"'):
        logger.info('Deleting item')
        client.remove_item(item)
        click.echo(f'Entry {name} removed')
    else:
        logger.info('Aborting')


@happi_cli.command()
@click.argument('name')
@click.argument('edits', nargs=-1, type=str)
@click.pass_context
def edit(ctx, name: str, edits: list[str]):
    """
    Change an existing entry.

    Applies EDITS of the form: field=value to the item of name NAME.
    """
    # retrieve client
    client = get_happi_client_from_config(ctx.obj)

    logger.debug('Starting edit block')
    try:
        item = client.find_item(name=name)
    except SearchError as e:
        raise click.ClickException(f'Could not find item {name!r}: {e}')

    if len(edits) < 1:
        raise click.ClickException('No edits provided')

    for edit in edits:
        field, value = edit.split('=', 1)
        # validate field
        try:
            field = is_valid_identifier_not_keyword(field)
        except ValueError:
            raise click.ClickException(f'field {field!r} is not a valid identifier')

        # validate field depending on enforce type
        if item._info_attrs[field].enforce in (dict, list):
            # try interpreting with ast
            try:
                value = ast.literal_eval(value)
            except (ValueError, SyntaxError) as e:
                raise click.ClickException(f'Could not interpret edit ({edit}), {e}\n'
                                           'Remember to escape your quotes '
                                           '(e.g. {\\"key\\":\\"value\\"})')
        else:
            try:
                value = item._info_attrs[field].enforce_value(value)
            except ValueError:
                raise click.ClickException(f'Error enforcing type in field {field!r} for value: {value!r}')

        # set field
        try:
            getattr(item, field)
            logger.info(f'Setting {name}.{field}: {value}')
            setattr(item, field, value)
        except Exception as e:
            raise click.ClickException(f'Could not set {name}.{field} to {value!r}: {e}')

    item.show_info()
    if click.confirm('Please confirm the item info is correct'):
        logger.info('Editing item')
        item.save()
    else:
        logger.info('Aborting')


@happi_cli.command()
@click.option('--glob/--regex', 'use_glob', default=True,
              help='use glob style (default) or regex style search terms. '
              r'Regex requires backslashes to be escaped (eg. at\\d.\\d)')
@click.argument('search_criteria', nargs=-1)
@click.pass_context
def load(
    ctx: click.Context,
    use_glob: bool,
    search_criteria: list[str]
):
    results = set()

    for item in search_criteria:
        final_results = search_parser(
            client=get_happi_client_from_config(ctx.obj),
            use_glob=use_glob,
            search_criteria=[item],
        )
        if not final_results:
            print('%s was not found.' % item)
        else:
            for res in final_results:
                results.add(res['name'])

    # Open IPython terminal with RESULTS loaded

    logger.debug('Starting load block')
    # retrieve client
    client = get_happi_client_from_config(ctx.obj)

    devices = {}
    names = [res.strip() for res in results]

    if len(names) < 1:
        raise click.BadArgumentUsage('No item names given')
    logger.info(f'Creating shell with devices {results}')

    for name in names:
        try:
            devices[name] = client.load_device(name=name)
        except SearchError as e:
            raise click.ClickException(f'Could not load device {name!r}: {e}')

    try:
        from IPython import start_ipython  # noqa
        start_ipython(argv=['--quick'], user_ns=devices)
    except ImportError:
        # Fall back to normal Python REPL if IPython is not available
        import code
        vars = globals().copy()
        vars.update(devices)
        shell = code.InteractiveConsole(vars)
        shell.interact()


# TODO: Figure out how to deal with json and click.  list of args doesn't
# translate exactly
@happi_cli.command()
@click.argument("json_data", nargs=-1)
@click.pass_context
def update(ctx, json_data: str):
    """
    Update happi db with JSON_DATA payload.

    To use, either use command substitution:

        $ happi update $(cat my.json)

    Or pipe the JSON payload with `-` as an argument:

        $ cat my.json | happi update -

    JSON payloads should be a list of items (dictionaries), with at least the
    "_id" and "type" keys.  eg:

    \b
        [{
            "_id": "my_device",
            <...>
            "type": "mydevicelibrary.MyDevice"
        }]

    Or a valid happi json database.  eg:

    \b
        {
            "my_device": {
                "_id": "my_device",
                <...>
                "type": "mydevicelibrary.MyDevice"
            }
        }
    """
    # retrieve client
    client = get_happi_client_from_config(ctx.obj)
    if len(json_data) < 1:
        raise click.BadArgumentUsage('No json data given')

    # parse input
    input_ = " ".join(json_data).strip()
    if input_ == "-":
        items_input = json.load(sys.stdin)
    else:
        items_input = json.loads(input_)

    # insert
    if isinstance(items_input, dict):
        items_input = items_input.values()

    for item in items_input:
        item = client.create_item(item["type"], **item)
        exists = item["_id"] in [c["_id"] for c in client.all_items]
        client._store(item, insert=not exists)


@happi_cli.command(name='container-registry')
def container_registry():
    """Print container registry"""
    pt = prettytable.PrettyTable()
    pt.field_names = ["Container Name", "Container Class", "Object Class"]
    pt.align = "l"
    for type_, class_, in happi.containers.registry.items():
        pt.add_row([type_,
                    f'{class_.__module__}.{class_.__name__}',
                    class_.device_class.default])
    click.echo(pt)


@happi_cli.command()
@click.pass_context
@click.argument("name", type=str, nargs=1)
@click.argument("target", type=str, nargs=1)
def transfer(ctx, name: str, target: str):
    """
    Change the container of an item.

    Transfers item (NAME) to a new container (TARGET)
    """
    logger.debug('Starting transfer block')
    # retrive client
    client = get_happi_client_from_config(ctx.obj)
    # verify name and target both exist and are valid
    try:
        item = client.find_item(name=name)
    except SearchError as e:
        raise click.ClickException(str(e))
    registry = happi.containers.registry
    # This is slow if dictionary is large
    target_match = [k for k, _ in registry.items() if target in k]
    if len(target_match) > 1 and name in target_match:
        target_match = [name]
    elif len(target_match) != 1:
        raise click.ClickException(f'Target container name ({target}) not specific enough. Possible matches: {target_match}')

    target_container = happi.containers.registry[target_match[0]]
    # transfer item and prompt for fixes
    transfer_container(client, item, target_container)


benchmark_sort_keys = [
    'name',
    'avg_time',
    'iterations',
    'tot_time',
    'max_time',
    'import_time',
]


@happi_cli.command()
@click.pass_context
@click.option("-d", "--duration", type=float, default=0,
              help="Specify how long in seconds to spend per device.")
@click.option("-i", "--iterations", type=int, default=1,
              help="Specify the number of times to instantiate each device.")
@click.option("-w", "--wait-connected", is_flag=True,
              help="Wait for the devices to be connected.")
@click.option("-t", "--tracebacks", is_flag=True,
              help="Show tracebacks from failing device loads.")
@click.option("-s", "--sort-key", type=str, default="avg_time",
              help=("Sort the output table. Valid options are "
                    f"{', '.join(benchmark_sort_keys)}"))
@click.option('--glob/--regex', 'use_glob', default=True,
              help='Use glob style (default) or regex style search terms. '
              r'Regex requires backslashes to be escaped (eg. at\\d.\\d)')
@click.argument('search_criteria', nargs=-1)
def benchmark(
    ctx,
    duration: float,
    iterations: int,
    wait_connected: bool,
    tracebacks: bool,
    sort_key: str,
    use_glob: bool,
    search_criteria: list[str],
):
    """
    Compare happi device startup times.

    This will generate a table that shows you how long each device took
    to instantiate.

    Repeats for at least the (-d, --duration) arg (default = 0 seconds)
    and for at least the number of the (-i, --iterations) arg (default = 1
    iteration), showing stats and averages.

    By default we time only the duration of __init__, but you can also
    (wait_connected) to see the full time until the device is fully ready
    to go, presuming the device has a wait_for_connection method.

    Search terms are standard as in the same search terms as the search
    cli function. A blank search term means to load all the devices.
    """
    logger.debug('Starting benchmark block')
    client: happi.Client = get_happi_client_from_config(ctx.obj)
    full_stats = []
    logger.info('Collecting happi items...')
    start = time.monotonic()
    if search_criteria:
        items = search_parser(
            client=client,
            use_glob=use_glob,
            search_criteria=search_criteria,
        )
    else:
        # All the items
        items = client.search()
    logger.info(f'Done, took {time.monotonic() - start} s')
    for result in items:
        logger.info(f'Running benchmark on {result["name"]}')
        try:
            stats = Stats.from_search_result(
                result=result,
                duration=duration,
                iterations=iterations,
                wait_connected=wait_connected,
            )
        except Exception:
            logger.error(
                f'Error running benchmark on {result["name"]}',
                exc_info=tracebacks,
            )
        else:
            full_stats.append(stats)
    table = prettytable.PrettyTable()
    table.field_names = benchmark_sort_keys
    if sort_key not in table.field_names:
        logger.warning(f'Sort key {sort_key} invalid, reverting to avg_time')
        sort_key = 'avg_time'
    for stats in sorted(
        full_stats,
        key=lambda x: getattr(x, sort_key),
        reverse=True,
    ):
        table.add_row([getattr(stats, key) for key in benchmark_sort_keys])
    print('Benchmark output:')
    print(table)
    print('Benchmark completed successfully')


@dataclasses.dataclass
class Stats:
    """
    Collect and hold results from benchmark runs.
    """
    name: str
    avg_time: float
    iterations: int
    tot_time: float
    max_time: float
    import_time: float

    @classmethod
    def from_search_result(
        cls,
        result: happi.SearchResult,
        duration: float,
        iterations: int,
        wait_connected: bool,
    ) -> Stats:
        """
        Create an object using a search result and store benchmarking info.
        """
        logger.debug(f'Checking stats for {result["name"]}')
        if not duration and not iterations:
            return Stats(
                name=result["name"],
                avg_time=0,
                iterations=0,
                tot_time=0,
                max_time=0,
                import_time=0,
            )
        raw_stats: list[float] = []
        import_time = cls.import_benchmark(result)
        counter = 0
        start = time.monotonic()
        while counter < iterations or time.monotonic() - start < duration:
            raw_stats.append(
                cls.run_one_benchmark(
                    result=result,
                    wait_connected=wait_connected
                )
            )
            counter += 1
        return Stats(
            name=result["name"],
            avg_time=sum(raw_stats) / len(raw_stats),
            iterations=len(raw_stats),
            tot_time=sum(raw_stats),
            max_time=max(raw_stats),
            import_time=import_time,
        )

    @staticmethod
    def import_benchmark(result: happi.SearchResult) -> float:
        """
        Check only the module import in isolation.
        """
        start = time.monotonic()
        happi.loader.import_class(result.item.device_class)
        return time.monotonic() - start

    @staticmethod
    def run_one_benchmark(
        result: happi.SearchResult,
        wait_connected: bool,
    ) -> float:
        """
        Create one object and time it.
        """
        start = time.monotonic()
        device = result.get(use_cache=False)
        if wait_connected:
            try:
                device.wait_for_connection(timeout=10.0)
            except AttributeError:
                logger.warning(
                    f'{result["name"]} does not have wait_for_connection.'
                )
            except TimeoutError:
                logger.warning(
                    'Timeout after 10s while waiting for connection of '
                    f'{result["name"]}',
                )
            except Exception:
                logger.warning(
                    'Unknown exception while waiting for connection of '
                    f'{result["name"]}',
                )
        return time.monotonic() - start


@happi_cli.command()
@click.pass_context
@click.option('-d', '--database', 'profile_database', is_flag=True,
              help='Profile the database loading.')
@click.option('-i', '--import', 'profile_import', is_flag=True,
              help='Profile the module importing.')
@click.option('-o', '--object', 'profile_object', is_flag=True,
              help='Profile the object instantiation.')
@click.option('-a', '--all', 'profile_all', is_flag=True,
              help='Shortcut for enabling all profile stages.')
@click.option('-p', '--profiler', default='auto',
              help='Select which profiler to use.')
@click.option('--glob/--regex', 'use_glob', default=True,
              help='Use glob style (default) or regex style search terms. '
              r'Regex requires backslashes to be escaped (eg. at\\d.\\d)')
@click.argument('search_criteria', nargs=-1)
def profile(
    ctx,
    profile_database: bool,
    profile_import: bool,
    profile_object: bool,
    profile_all: bool,
    profiler: str,
    use_glob: bool,
    search_criteria: list[str],
):
    """
    Per-function startup speed diagnostic.

    This will go through the happi loading process and show
    information about the execution time of all the
    functions called during the process.

    Contains options for picking which devices to check and which
    part of the loading process to profile. You can choose to
    profile the happi database loading (-d, --database), the
    class imports (-i, --import), the object instantiation
    (-o, --object), or all of the above (-a, --all).

    By default this will use whichever profiler you have installed,
    but this can also be overriden with the (-p, --profiler) option.
    The priority order is, first, the pcdsutils line_profiler wrapper
    (--profiler pcdsutils), and second, the built-in cProfile module
    (--profiler cprofile). More options may be added later.

    Search terms are standard as in the same search terms as the search
    cli function. A blank search term means to load all the devices.
    """
    logger.debug('Starting profile block')
    if profiler not in ('auto', 'pcdsutils', 'cprofile'):
        raise RuntimeError(f'Invalid profiler selection {profiler}')

    client: happi.Client = get_happi_client_from_config(ctx.obj)
    if profile_all:
        profile_database = True
        profile_import = True
        profile_object = True
    if not any((profile_database, profile_import, profile_object)):
        raise RuntimeError('No profile options selected!')
    if profiler == 'auto':
        try:
            import pcdsutils.profile
            if pcdsutils.profile.has_line_profiler:
                profiler = 'pcdsutils'
            else:
                profiler = 'cprofile'
        except ImportError:
            profiler = 'cprofile'
    if profiler == 'pcdsutils':
        from pcdsutils.profile import profiler_context
        context_profiler = None
    elif profiler == 'cprofile':
        context_profiler = Profile()

        @contextmanager
        def profiler_context(*args, **kwargs):
            context_profiler.enable()
            yield
            context_profiler.disable()

    @contextmanager
    def null_context(*args, **kwargs):
        yield

    def output_profile():
        # Call at the end: let's output results to stdout
        if profiler == 'pcdsutils':
            from pcdsutils.profile import print_results
            print_results()
        elif profiler == 'cprofile':
            context_profiler.print_stats(sort='cumulative')
        print('Profile completed successfully')

    # Profile stage 1: searching the happi database
    logger.info('Searching the happi database')
    if profile_database:
        db_context = profiler_context
    else:
        db_context = null_context
    start = time.monotonic()
    with db_context(
        module_names=['happi'],
        use_global_profiler=True,
        output_now=False,
    ):
        if search_criteria:
            items = search_parser(
                client=client,
                use_glob=use_glob,
                search_criteria=search_criteria,
            )
        else:
            # All the items
            items = client.search()
    logger.info(
        f'Searched the happi database in {time.monotonic() - start} s'
    )

    if not any((profile_import, profile_object)):
        return output_profile()

    # Profile stage 2: import the device classes
    logger.info('Importing the device classes')
    if profile_import:
        import_context = profiler_context
    else:
        import_context = null_context

    classes = set()
    start = time.monotonic()
    with import_context(
        module_names=['happi'],
        use_global_profiler=True,
        output_now=False,
    ):
        for search_result in items:
            try:
                cls = happi.loader.import_class(
                    search_result.item.device_class,
                )
                classes.add(cls)
            except ImportError:
                logger.warning(
                    f'Failed to import {search_result.item.device_class}'
                )
    logger.info(
        f'Imported the device classes in {time.monotonic() - start} s'
    )

    if not profile_object:
        return output_profile()

    # Check which modules to focus on for line profiler
    module_names = {'happi'}
    for instance_class in classes:
        try:
            parents = instance_class.mro()
        except AttributeError:
            # E.g. we have a function
            parents = [instance_class]
        for parent_class in parents:
            module = parent_class.__module__
            module_names.add(module.split('.')[0])
    # Add imported ophyd control layers
    for cl in ('epics', 'caproto'):
        if cl in sys.modules:
            module_names.add(cl)

    # Profile stage 3: create the device classes
    logger.info('Creating the device classes')
    if profile_object:
        object_context = profiler_context
    else:
        object_context = null_context
    start = time.monotonic()
    with object_context(
        module_names=module_names,
        use_global_profiler=True,
        output_now=False,
    ):
        for search_result in items:
            try:
                search_result.get(use_cache=False)
            except Exception:
                logger.warning(
                    f'Failed to create {search_result["name"]}'
                )
    logger.info(
        f'Created the device classes in {time.monotonic() - start} s'
    )
    return output_profile()


def ophyd_cleanup():
    """
    Clean up ophyd - avoid teardown errors by stopping callbacks.

    If this is not run, ophyd callbacks continue to run and can cause
    terminal spam and segfaults.
    """
    if 'ophyd' in sys.modules:
        import ophyd
        dispatcher = ophyd.cl.get_dispatcher()
        if dispatcher is not None:
            dispatcher.stop()


def pyepics_cleanup():
    """
    Clean up pyepics - avoid teardown errors by stopping callbacks.

    If this is not run, pyepics callbacks continue to run and if they throw
    exceptions they will create terminal spam.

    Run this before ophyd_cleanup to prevent race conditions where pyepics
    is trying to call ophyd things that have been torn down.
    """
    if 'epics' in sys.modules:
        from epics import ca

        # Prevent new callbacks from being set up
        def no_create_channel(*args, **kwargs):
            ...

        ca.create_channel = no_create_channel

        # Remove references to existing callbacks
        for context_cache in ca._cache.values():
            for cache_item in context_cache.values():
                try:
                    cache_item.callbacks.clear()
                    cache_item.access_event_callback.clear()
                except AttributeError:
                    print(cache_item)


@happi_cli.command()
@click.pass_context
@click.option('-f', '--file', 'ext_file',
              type=click.Path(exists=True, dir_okay=False, resolve_path=True),
              help='File to import additional checks from.')
@click.option('-l', '--list', 'list_checks', is_flag=True,
              help='List the available validation checks')
@click.option('-c', '--check', 'check_choices', multiple=True, default=[],
              help='Name of the check to include.  '
                   'Can also provide a substring')
@click.option('-d', '--details', 'details',
              help='Show the details of the specified audit function(s)')
@click.option('--glob/--regex', 'use_glob', default=True,
              help='Use glob style (default) or regex style search terms. '
              r'Regex requires backslashes to be escaped (eg. at\\d.\\d)')
@click.option('--names', '-n', 'names_only', is_flag=True,
              help='Only display names of failed entries')
@click.option('--json', '-j', 'show_json', is_flag=True,
              help='output results in json format')
@click.argument('search_criteria', nargs=-1)
def audit(
    ctx,
    list_checks: bool,
    ext_file: str | None,
    check_choices: list[str],
    details: str,
    use_glob: bool,
    names_only: bool,
    show_json: bool,
    search_criteria: tuple[str, ...]
):
    """
    Audit the current happi database.

    Runs checks on the devices matching the provided SEARCH_CRITERIA.
    Checks are simple functions that raise exceptions on failure,
    whether naturally or via assert calls.  These functions take a single
    happi.SearchResult as an positional argument and returns None if
    successful.

    To import additional checks, provide a file with your check function
    and a list named ``checks`` containing the desired functions.
    """
    logger.debug('Starting audit block')

    # if a file is provided, make its functions available
    if ext_file:
        fp = Path(ext_file)
        sys.path.insert(1, str(fp.parent))
        ext_module = importlib.import_module(fp.stem)
        ext_checks = getattr(ext_module, 'checks')
        checks.extend(ext_checks)

    # List checks subcommand
    if list_checks:
        check_pt = prettytable.PrettyTable(field_names=['name',
                                                        'description'])
        check_pt.hrules = prettytable.ALL
        check_pt.align['description'] = 'l'
        for chk in checks:
            check_pt.add_row([chk.__name__,
                              inspect.cleandoc(chk.__doc__ or '(No description)')])
        click.echo(check_pt)
        return

    if details:
        check_fns = [fn for fn in checks if details in fn.__name__]
        for fn in check_fns:
            click.echo(inspect.getsource(fn))

        return

    # gather selected checks
    if check_choices:
        check_list = []
        for check_name in check_choices:
            # check if provided check name is a substring of any checks
            matches = [fn for fn in checks if check_name in fn.__name__]
            if len(matches) != 1:
                raise click.BadParameter(
                    f'provided check name ({check_name}) must match only'
                    f'one check.  Matches: ({[ch.__name__ for ch in matches]})'
                )
            check_list.append(matches[0])
    else:
        # take all checks
        check_list = checks

    client: Optional[happi.Client] = get_happi_client_from_config(ctx.obj)
    if client is None:
        raise click.ClickException("Failed to create happi client")

    results = search_parser(client, use_glob, list(search_criteria))
    logger.info(f'found {len(results)} items to verify')
    logger.info(f'running checks: {[f.__name__ for f in check_list]}')

    final_dict = run_audit(
        results,
        redirect=True,
        verbose=not (names_only or show_json),
        check_list=check_list,
    )
    test_results = final_dict["test_results"]

    # print outs
    if names_only:
        click.echo(' '.join(final_dict["failed_names"]))
    elif show_json:
        json.dump(final_dict, indent=2, fp=sys.stdout)
    else:
        pt = prettytable.PrettyTable(field_names=['name', 'check', 'error'])
        pt.align['error'] = 'l'
        last_name = ''
        for name, success, check, msg in zip(test_results['name'],
                                             test_results['success'],
                                             test_results['check'],
                                             test_results['msg']):
            if not success:
                if name != last_name:
                    if last_name != '':  # initial condition
                        pt.add_row(['', '', ''], divider=True)
                    pt.add_row([name, check, msg])
                else:
                    pt.add_row(['', check, msg])
                last_name = name

        try:
            term_width = os.get_terminal_size()[0]
            pt._max_width = {'error': max(60, term_width - 40)}
        except OSError:
            # non-interactive mode (piping results). default max width
            pt._max_width = {'error': 100}
            pass

        if len(pt.rows) > 0:
            click.echo(pt)

        num_failures = final_dict["failures"]
        click.echo(f'# devices failed: {num_failures} / {len(results)}')


@happi_cli.command()
@click.pass_context
@click.option('--fix-optional/--ignore-optional', 'fix_optional', default=False,
              help='Also prompt for user input on optional information')
@click.option('--glob/--regex', 'use_glob', default=True,
              help='Use glob (default) or regex style search terms. '
              'Only relevant if search_criteria are provided.')
@click.argument('search_criteria', nargs=-1)
def repair(
    ctx,
    fix_optional: bool,
    use_glob: bool,
    search_criteria: tuple[str, ...],
):
    """
    Repair the database.

    Repairs all entries matching SEARCH_CRITERIA, repairs entire database otherwise.

    Entries that don't get any fields changed will not get saved
    (i.e. their last-edit times will not change).
    """
    logger.debug('starting repair block')

    client: happi.Client = get_happi_client_from_config(ctx.obj)
    if search_criteria:
        results = search_parser(client, use_glob, search_criteria)
    else:
        # run repair on all items
        results = search_parser(client, True, '*')

    for res in results:
        # don't save if changes not made
        changes_made = False

        # fix mandatory info with missing defaults
        req_info = find_unfilled_mandatory_info(res)

        if fix_optional:
            req_info.extend(find_unfilled_optional_info(res))

        res_id = res['_id']

        # fix each mandatory field
        logger.info(f'repairing ({res_id})...')
        for req_field in req_info:
            info = res.item._info_attrs[req_field]
            req_value = prompt_for_entry(info)
            curr_value = getattr(res.item, req_field)

            if curr_value != req_value:
                info.enforce_value(req_value)
                setattr(res.item, req_field, req_value)
                changes_made = True

        # check name and id parity
        if res['name'] != res_id:
            # set name to match id
            res.item.name = res_id
            changes_made = True

        if not changes_made:
            logger.info(f'no actual changes made during repair of {res_id}, not saving...')
            continue

        # re-save after creating container
        try:
            # will save optional data with defaults
            # optional data without defaults saved as null
            res.item.save()
        except KeyboardInterrupt:
            # Finish the current save if interrupted
            logger.warning('caught keyboard interrupt, finishing')
            res.item.save()
            break


@click.group(help="Commands related to the happi config file.")
def config():
    pass


@config.command(name="edit")
def edit_config():
    """Open happi configuration file for editing."""
    config_filepath = happi.client.Client.find_config()
    if sys.platform.startswith("win32"):
        import shutil
        editor = shutil.which(os.environ.get("EDITOR", "notepad.exe"))
        subprocess.run([editor, config_filepath])
    else:
        subprocess.run([os.environ.get("EDITOR", "vi"), config_filepath])


@config.command()
@click.option("--overwrite/--no-overwrite", "overwrite", default=False,
              help="Overwrite existing config.")
@click.option("--backend", type=click.Choice(["json"], case_sensitive=False), default="json")
def init(overwrite, backend):
    """Create configuration file with default options."""

    # find config_filepath
    try:
        config_filepath = Path(happi.client.Client.find_config())
    except OSError:
        config_filepath = Path(platformdirs.user_config_dir("happi")) / "happi.cfg"
    else:
        if not overwrite:
            click.echo("Found existing config file at:")
            click.echo(f"  {config_filepath}")
            click.echo("Stopping! Use --overwrite to destroy this config file.")
            return
    click.echo("Creating new config file at:")
    click.echo(f"  {config_filepath}")

    # find database_filepath
    database_filepath = Path(platformdirs.user_data_dir("happi")) / "db.json"
    if database_filepath.exists():
        click.echo("Using existing database file at:")
    else:
        click.echo("Creating new database file at:")

    click.echo(f"  {database_filepath}")

    # create config file
    config_filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(config_filepath, "w") as f:
        f.write("[DEFAULT]\n")
        f.write(f"path={database_filepath}\n")

    # create database file
    database_filepath.parent.mkdir(parents=True, exist_ok=True)
    database_filepath.touch(exist_ok=True)

    click.echo("Done!")


@config.command()
def show():
    """Show configuration file in current state."""
    config_filepath = Path(happi.client.Client.find_config())
    click.echo(f"File: {config_filepath}")

    def draw_line():
        try:
            click.echo("-"*os.get_terminal_size()[0])
        except OSError:
            # non-interactive mode (piping results). No max width
            click.echo("-"*79)

    draw_line()
    with open(config_filepath, "r") as f:
        for line in f:
            click.echo(line.strip())
    draw_line()


def main():
    """Execute the ``happi_cli`` with command line arguments"""
    happi_cli.add_command(config)
    happi_cli()
