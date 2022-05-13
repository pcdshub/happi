import click
import prettytable

from .loader import change_container


def transfer_container(item, target):
    """
    Interactively step through transferring an item into a new container
    Works by catching exceptions and prompting for updates

    Control flow:
    - print keys of both (show_info)
        - prompt for how to join
        - prompt entry for any missing key
            - check enforce, prompt to fix
        - prompt for how to handle extra keys
        -
    - attempt to convert
        - while errors still exist (what errors will be here?)
            - prompt to fix enforce errors?
            - prompt to fix
    - show final result for verification

    Must:
    - deal with enforcement failures
        - replace (and suggest default)
        - change enforcement?
    - deal with missing keys?
    - set up input loop
    - show finalized container for
    - prompt for any patch fixes?
    - deal with types of fields (mandatory, extraneous, etc)
    """
    target_name = target.__name__
    print(f'Attempting to transfer {item.name} to {target_name}...')
    # compare keys in item to target
    matching_keys = [n for n in item.info_names
                     if n in target.info_names]
    item_exclusive = [n for n in item.info_names
                      if n not in target.info_names]
    target_exclusive = [n for n in target.info_names
                        if n not in item.info_names]

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
                        f'{n} = "{getattr(item, n)}"?')
        if click.confirm(extra_prompt, default=True):
            edits.update({n: getattr(item, n)})

    # Deal with missing keys in target, deal with validation later
    for nt in target_exclusive:
        missing_prompt = (f'{target_name} expects information for '
                          f'entry "{nt}"')
        val = click.prompt(missing_prompt, default='take default')
        if val != 'take default':
            edits.update({nt: val})

    # Actually apply changes and cast item into new container
    # Enforce conditions are dealt with here
    click.echo('\n----------Amend Entries-----------')
    success = False
    while not success:
        success, res = change_container(item, target, edits=edits)
        if not success:
            fix_prompt = f'New value for "{res}"'
            new_val = click.prompt(fix_prompt)
            edits.update({res: new_val})

    return res
