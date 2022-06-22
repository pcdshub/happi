import ast
import logging
from typing import Optional

import click
import prettytable

from happi.errors import EnforceError, TransferError
from happi.utils import (OptionalDefault, is_valid_identifier_not_keyword,
                         optional_enforce)

logger = logging.getLogger(__name__)

hopefully_unique_keyword = 'verylonghopefullyuniquekeywordthatdoesnotconflict'


def read_user_dict(prompt, default: Optional[dict] = None):
    """
    Prompt for a dictionary, prompting for keys and values separately
    """
    user_dict = {}
    click.echo(prompt + '\nKey must be a string.  ' +
               'Enter a blank key to complete dict entry.')
    while True:
        key = click.prompt('  key',
                           default=hopefully_unique_keyword,
                           show_default=False,
                           value_proc=is_valid_identifier_not_keyword)
        if key is hopefully_unique_keyword:
            break

        value = click.prompt('  value')
        try:
            value = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            logger.debug(f'Taking {value} as a string')

        user_dict.update({key: value})

    if not user_dict:
        return default

    return user_dict


def enforce_list(value):
    """
    Special handling for list inputs.
    Accept python lists, and attempts to intepret any strings as lists

    Raises
    ------
    EnforceError
        if value cannot be interpreted as a list
    """
    if isinstance(value, list):
        return value

    # if not a list, try to interpret as a list
    try:
        value = ast.literal_eval(value)
    except (ValueError, SyntaxError) as e:
        raise EnforceError(e)

    if not isinstance(value, list):
        raise EnforceError(f'Provided value ({value}) is not a list')
    return value


def prompt_for_entry(entry_info, clone_source=None):
    """Prompt for an entry based on the entry_info provided"""
    if clone_source:
        default = getattr(clone_source, entry_info.key)
    else:
        default = entry_info.default

    if entry_info.optional and (default is None):
        # Prompt will continue to prompt if default is None
        # Provide a dummy value to allow prompt to exit
        default = OptionalDefault()
        enforce_fn = optional_enforce(entry_info.enforce_value)
    else:
        enforce_fn = entry_info.enforce_value

    enforce_str = getattr(entry_info.enforce, '__name__',
                          str(entry_info.enforce))
    val_prompt = (f'Enter value for {entry_info.key}, '
                  f'enforce={enforce_str}')

    # prompt differently depending on the enforce type
    if entry_info.enforce is list:
        logger.debug('prompting for list')
        # special handling for an optional list
        if isinstance(default, OptionalDefault):
            list_enforce = optional_enforce(enforce_list)
        else:
            list_enforce = enforce_list

        value = click.prompt(val_prompt, default=default,
                             value_proc=list_enforce)
    elif entry_info.enforce is dict:
        logger.debug('prompting for dict')
        value = read_user_dict(val_prompt, default=default)
    elif entry_info.enforce is bool:
        logger.debug('prompting for bool')
        # coerces into y or n, preventing random strings (eg. 'f') from
        # evaluating as True
        value = click.confirm(val_prompt, default=default)
    else:
        # everything else is a callable
        value = click.prompt(val_prompt, default=default,
                             value_proc=enforce_fn)

    if isinstance(value, OptionalDefault):
        # Default was None, return None
        value = None

    return value


def transfer_container(client, item, target):
    """
    Interactively step through transferring an item into a new container
    Works by catching exceptions raised by client.change_container
    and prompting for updates.

    Steps:
    - Display information for item and its target container
    - Prepare Entries: prompt to include extra entries and fill missin
                       entries
    - Amend Entries: Attempt to coerce ``item`` into ``target``.  If
                     there is an error, prompt for a fix.
    - Create new item and prompt for confirmation to save.

    Parameters
    ----------
    client : happi.client.Client
        Happi client connected to database and container registry

    item : happi.HappiItem
        Loaded item to transfer

    target : Type[happi.HappiItem]
        Target container for ``item``.  Container constructor
    """
    target_name = target.__name__
    print(f'Attempting to transfer {item.name} to {target_name}...')
    # compare keys in item to target
    item_info = item.post()
    ignore_names = ['type', 'creation', 'last_edit']
    item_public_keys = sorted([key for key in item_info.keys()
                               if not key.startswith('_')])
    matching_keys = [n for n in item_public_keys
                     if n in target.info_names]
    item_exclusive = [n for n in item_public_keys
                      if n not in target.info_names + ignore_names]
    target_exclusive = [n for n in target.info_names
                        if n not in item_public_keys]

    pt = prettytable.PrettyTable()
    pt.field_names = [f'{item.name}', f'{target_name}']
    for n in matching_keys:
        pt.add_row([n, n])
    for ni in item_exclusive:
        pt.add_row([ni, '-'])
    for nt in target_exclusive:
        pt.add_row(['-', nt])

    click.echo(pt)

    edits = {}
    click.echo('\n----------Prepare Entries-----------')
    # Deal with extra keys in item
    for n in item_exclusive:
        extra_prompt = (f'Include entry from {item.name}: '
                        f'{n} = "{item_info.get(n)}"?')
        if click.confirm(extra_prompt, default=True):
            edits.update({n: item_info.get(n)})

    # Deal with missing keys in target, deal with validation later
    for nt in target_exclusive:
        missing_prompt = (f'{target_name} expects information for '
                          f'entry "{nt}"')
        d = getattr(getattr(target, nt), 'default')
        val = click.prompt(missing_prompt, default=f'take default: {d}')
        if val != 'take default':
            edits.update({nt: val})

    # Actually apply changes and cast item into new container
    # Enforce conditions are dealt with here
    click.echo('\n----------Amend Entries-----------')
    success = False
    new_kwargs = None
    while not success:
        try:
            new_kwargs = client.change_container(item, target, edits=edits)
            success = True
        except TransferError as e:
            print(e)
            fix_prompt = f'New value for "{e.key}"'
            new_val = click.prompt(fix_prompt)
            edits.update({e.key: new_val})

    if not new_kwargs:
        logger.debug('transfer_container failed, no kwargs returned')
        return

    item = client.create_item(target, **new_kwargs)
    item.show_info()

    if click.confirm('Save final item?'):
        logger.debug('deleting original object and replacing')
        client.remove_item(item)
        item.save()
