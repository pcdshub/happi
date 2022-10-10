"""
This module contains functions and helpers for auditing the happi database.
Checks are simple functions that take a happi.SearchResult a positional
argument and returns None when successful.  When a check fails, it should throw
an Exception with a helpful error message.  These exception messages will be
caught and organized by the cli audit tool.
"""
import inspect
from typing import Callable, List, Optional, Tuple

from happi import SearchResult

CLIENT_KEYS = ['_id', 'type', 'creation', 'last_edit']


def check_instantiation(result: SearchResult) -> None:
    """
    Check if the device can be instantiated
    Simply attempts to get the device from the happi.SearchResult

    Subscription callback exceptions are silenced in ophyd, and will
    not cause this check to fail.
    """
    _ = result.get()


def check_extra_info(
    result: SearchResult,
    ignore_keys: Optional[List[str]] = None
) -> None:
    """
    Check if there is any extra info in the result that does not
    have a corresponding EntryInfo on the container.

    Ignores the presence of client-side metadata keys
    - id
    - type
    - creation
    - last_edit
    """
    if ignore_keys is None:
        ignore_keys = CLIENT_KEYS

    extra = result.item.extraneous.copy()
    for key in ignore_keys:
        extra.pop(key)
    if len(extra) != 0:
        raise ValueError(f'Un-enforced metadata found: {list(extra.keys())}')


def check_name_match_id(result: SearchResult) -> None:
    """
    Check if the item's ``_id`` field matches its ``name``.
    This is a convention we have held for a while, making searching
    in either direction easier.
    """
    id_field = result.metadata.get('_id')
    name_field = result.metadata.get('name')
    assert id_field == name_field, f'id: {id_field} != name: {name_field}'


def verify_result(
    result: SearchResult,
    checks: List[Callable[[SearchResult], None]]
) -> Tuple[bool, str]:
    """
    Validate device against the provided checks

    Parameters
    ----------
    result : happi.SearchResult
        result to be verified

    checks : List[Callable[[SearchResult], None]]
        a list of verification functions that raise exceptions if
        verification fails.

    Returns
    -------
    bool
        whether or not the device passed the checks
    str
        error message describing reason for failure and possible steps
        to fix.  Empty string if validation is successful
    """
    success, msg = True, ""
    # verify checks have the correct signature, as much as is reasonable
    for check in checks:
        validate_check_signature(check)

    try:
        for check in checks:
            check(result)
    except Exception as ex:
        success = False
        msg = (f"Failed check ({check.__name__}): {str(ex)}")

    return success, msg


def validate_check_signature(fn: Callable) -> None:
    """
    Validate the signature of the provided function.

    Valid check functions:
    - must take a single argument, the happi.SearchResult to check
    - may specify any number of other arguments with defaults provided
    - should return None, as return values are ignored (unchecked)

    Parameters
    ----------
    fn : Callable
        Check function to be validated

    Raises
    -------
    RuntimeError
        if function cannot be used to audit happi SearchResult's
    """

    if not callable(fn):
        raise RuntimeError('requested check function is not callable')

    sig = inspect.getfullargspec(fn)

    if len(sig.args) == 0:
        raise RuntimeError('check function must take at least one argument '
                           '(a happi.SearchResult)')
    if len(sig.args) > 1 and ((len(sig.args) - len(sig.defaults)) != 1):
        raise RuntimeError('check function must take only one argument '
                           'without a default value')
    if sig.kwonlyargs and len(sig.kwonlyargs) != len(sig.kwonlydefaults):
        raise RuntimeError('check function cannot have keyword-only '
                           'arguments without default values')


checks = [check_instantiation, check_extra_info, check_name_match_id]
