"""
This module defines the ``happi`` command line interface.
"""
from __future__ import annotations

import ast
import dataclasses
import fnmatch
import json
import logging
import os
# on import allows arrow key navigation in prompt
import readline  # noqa
import sys
import time
from contextlib import contextmanager
from cProfile import Profile
from typing import List

import click
import coloredlogs
import prettytable

import happi

from .prompt import prompt_for_entry, transfer_container
from .utils import is_a_range, is_number, is_valid_identifier_not_keyword

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

    # Cleanup tasks related to loaded devices
    @ctx.call_on_close
    def device_cleanup():
        pyepics_cleanup()
        ophyd_cleanup()


@happi_cli.command()
@click.option('--show_json', '-j', is_flag=True,
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
    search_criteria: List[str]
):
    """
    Search the happi database.  SEARCH_CRITERIA take the form: field=value.
    If 'field=' is omitted, it will assumed to be 'name'.
    You may include as many search criteria as you like; these will
    be combined with ANDs.
    """
    logger.debug("We're in the search block")

    final_results = search_parser(
        client=ctx.obj,
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
    search_criteria: List[str],
) -> List[happi.SearchResult]:
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
    """
    # Get search criteria into dictionary for use by client
    client_args = {}
    range_list = []
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
                logger.error(
                    'Received duplicate search criteria %s=%r (was %r)',
                    criteria, value, client_args[criteria]
                )
                raise click.Abort()

            if is_a_range(value):
                start, stop = value.split(',')
                start = float(start)
                stop = float(stop)
                if start < stop:
                    new_range_list = client.search_range(criteria, start, stop)
                else:
                    logger.error('Invalid range, make sure start < stop')
                    raise click.Abort()

                if not range_found:
                    # if first range, just replace
                    range_found = True
                    range_list = new_range_list
                else:
                    # subsequent ranges, only take intersection
                    range_list = set(new_range_list) & set(range_list)

                if not range_list:
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
    if regex_list and not range_list:
        # only matched with one search_regex()
        final_results = regex_list
    elif range_list and not regex_list:
        # only matched with search_range()
        final_results = range_list
    elif range_list and regex_list:
        # find the intersection between regex_list and range_list
        final_results = set(range_list) & set(regex_list)
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
    """Add new entries interactively."""
    logger.debug(f'Starting interactive add, {clone}')
    # retrieve client
    client = ctx.obj

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
            logger.info(f'Invalid item container {response}')
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

    item = client.create_item(container, **kwargs)
    item.show_info()
    if click.confirm('Please confirm the item info is correct'):
        logger.info('Adding item')
        item.save()
    else:
        logger.info('Aborting')


@happi_cli.command()
@click.argument('name')
@click.argument('edits', nargs=-1, type=str)
@click.pass_context
def edit(ctx, name: str, edits: List[str]):
    """
    Change an existing entry by applying EDITS of the form: field=value
    to the item of name NAME.
    """
    # retrieve client
    client = ctx.obj

    logger.debug('Starting edit block')
    item = client.find_item(name=name)
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
        if item._info_attrs[field].enforce in (dict, list):
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
                value = item._info_attrs[field].enforce_value(value)
            except ValueError:
                logger.error(f'Error enforcing type for value: {value}')
                raise click.Abort()

        # set field
        try:
            getattr(item, field)
            logger.info(f'Setting {name}.{field}: {value}')
            setattr(item, field, value)
        except Exception as e:
            logger.error(f'Could not edit {name}.{field}: {e}')
            raise click.Abort()

    item.show_info()
    if click.confirm('Please confirm the item info is correct'):
        logger.info('Editing item')
        item.save()
    else:
        logger.info('Aborting')


@happi_cli.command()
@click.argument('item_names', nargs=-1)
@click.pass_context
def load(ctx, item_names: List[str]):
    """Open IPython terminal with ITEM_NAMES loaded"""

    logger.debug('Starting load block')
    # retrieve client
    client = ctx.obj

    logger.info(f'Creating shell with devices {item_names}')
    devices = {}
    names = " ".join(item_names)
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
def update(ctx, json_data: str):
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
    """Change the container of an item (NAME) to a new container (TARGET)"""
    logger.debug('Starting transfer block')
    # retrive client
    client = ctx.obj
    # verify name and target both exist and are valid
    item = client.find_item(name=name)
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
              help=(
                "Sort the output table. Valid options are "
                f"{', '.join(benchmark_sort_keys)}"
              ))
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
    search_criteria: List[str],
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
    client: happi.Client = ctx.obj
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
        raw_stats: List[float] = []
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
    search_criteria: List[str],
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
    client: happi.Client = ctx.obj
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
    module_names = set(('happi',))
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


def main():
    """Execute the ``happi_cli`` with command line arguments"""
    happi_cli()
