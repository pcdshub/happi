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
    result.get()


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
    check: Callable[[SearchResult], None]
) -> Tuple[bool, str, str]:
    """
    Validate device against the provided check

    Parameters
    ----------
    result : happi.SearchResult
        result to be verified

    check : Callable[[SearchResult], None]
        a verification function that raise exceptions if
        verification fails.

    Returns
    -------
    bool
        whether or not the device passed the checks
    str
        name of check that failed, if any
    str
        error message describing reason for failure and possible steps
        to fix.  Empty string if validation is successful
    """
    success, msg = True, ""
    # verify checks have the correct signature, as much as is reasonable
    sig = inspect.signature(check)
    sig.bind(result)

    try:
        check(result)
    except Exception as ex:
        success = False
        msg = str(ex)

    return success, check.__name__, msg


checks = [check_instantiation, check_extra_info, check_name_match_id]
