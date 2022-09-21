"""
Functions and helpers for auditing the happi database
Features to include:
- Search for subset -> function takes List[SearchResult]
- checks
    - instantiation check
    - run method check (get_lightpath_state)
    - Extra information check
    - check all are enforced?
- Return warnings based on function

Eventually want to discover checks via entrypoints?
let users specify checks via index?
"""
from typing import Callable, List, Optional, Tuple

from happi import SearchResult

CLIENT_KEYS = ['_id', 'type', 'creation', 'last_edit']


def check_instantiation(result: SearchResult) -> None:
    """
    attempts to get the instantiated device from the happi.SearchResult
    Allow any exceptions to be bubbled up to the validator

    How do we catch subscription callback exceptions?.....

    Parameters
    ----------
    result : SearchResult
        happi entry to be validated
    """
    _ = result.get()


def check_extra_info(
    result: SearchResult,
    ignore_keys: Optional[List[str]] = None
) -> None:
    """
    Check if there is any extra info in the result that does not
    match the container.

    Ignores the presence of client-side metadata
    - id
    - type
    - creation
    - last_edit

    TODO: make a new exception?
    """
    if ignore_keys is None:
        ignore_keys = CLIENT_KEYS

    extra = result.item.extraneous.copy()
    for key in ignore_keys:
        extra.pop(key)
    if len(extra) != 0:
        raise ValueError(f'Un-enforced metadata found: {list(extra.keys())}')
    # present with entry info but not enforced?


def check_valid_info(result: SearchResult) -> None:
    """
    Check if the entry info that exists on the container is valid, as
    specified by the EntryInfo.enforce()

    May not be necessary, happi will skip the entry if enforce fails.
    Upon creation of the item and setting of entry info, will throw a
    warning and escape
    """
    it = result.item
    for einfo in it.entry_info:
        einfo.enforce_value(getattr(it, einfo.key))


def check_lightpath_valid(result: SearchResult) -> None:
    """
    Check if the desired device is lightpath-valid by:
    - verifying device.get_lightpath_state() runs
    - received LightpathState is valid
    """
    dev = result.get()

    state = dev.get_lightpath_state()

    assert isinstance(state.inserted, bool), 'inserted is not a bool'
    assert isinstance(state.removed, bool), 'removed is not a bool'
    assert isinstance(state.output, dict), 'ouptut is not a dict'


def check_name_match_id(result: SearchResult) -> None:
    """
    Check if the item's ``_id`` field matches its ``name``.
    This is a convention we have held for a while, making searching
    in either direction easier.
    """

    assert result.metadata.get('_id') == result.metadata.get('name')


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

    try:
        for check in checks:
            check(result)
    except Exception as ex:
        success = False
        msg = (f"Failed check ({check.__name__}): {str(ex)}")

    return success, msg


checks = {
    'check_instantiation': check_instantiation,
    'check_extra_info': check_extra_info,
    'check_lightpath_valid': check_lightpath_valid,
    'check_name_match_id': check_name_match_id
}
