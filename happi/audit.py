"""
This module contains functions and helpers for auditing the happi database.
Checks are simple functions that take a happi.SearchResult a positional
argument and returns None when successful.  When a check fails, it should throw
an Exception with a helpful error message.  These exception messages will be
caught and organized by the cli audit tool.
"""
from __future__ import annotations

import contextlib
import inspect
import io
import sys
from typing import Callable, List, Optional, TypedDict

from jinja2 import DebugUndefined, Environment, meta

from . import SearchResult

CLIENT_KEYS = ['_id', 'type', 'creation', 'last_edit']


class CheckResults(TypedDict):
    name: list[str]
    success: list[bool]
    check: list[str]
    msg: list[str]


class ItemAuditInfo(TypedDict):
    failed_check: list[str]
    audit_errors: list[str]


class AuditResults(TypedDict):
    test_results: CheckResults
    audited: int
    failures: int
    failed_names: list[str]
    items: dict[str, ItemAuditInfo]


Check = Callable[[SearchResult], None]
CheckList = list[Check]


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
    ignore_keys: Optional[list[str]] = None
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
        extra.pop(key, None)
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
    if id_field != name_field:
        raise ValueError(f'id: {id_field} != name: {name_field}')


def check_wait_connection(result: SearchResult) -> None:
    """
    Check if all the signals on the device can connect to their PV's

    This can take a long time, consider filtering your query before running
    """
    dev = result.get()

    if not (hasattr(dev, 'wait_for_connection') and
            callable(getattr(dev, 'wait_for_connection'))):
        raise ValueError('device has no wait_for_connection method, '
                         'and is likely not an ophyd v1 device')

    try:
        dev.wait_for_connection(timeout=5)
    except TimeoutError as te:
        # If we encounter a timeout error, gather some more detailed stats
        sigs = list(sig.item for sig in dev.walk_signals())
        conn_sigs = sum(sig.connected for sig in sigs)

        raise ValueError(f'{conn_sigs}/{len(sigs)} signals connected. \n'
                         f'original error: {te}')


def check_args_kwargs_match(result: SearchResult) -> None:
    """
    Check that arguments that request information from the container
    have information in those entries.

    i.e.: makes sure there is information in the entry named "extra"
          if the kwargs = {'extra': '{{extra}}'}
    """
    # Happi fills in values when search result is created, must pull
    # raw document from client level
    cl = result.client
    doc = cl.find_document(**{cl._id_key: result[cl._id_key]})
    # pick out any jinja-like template
    env = Environment(undefined=DebugUndefined)

    # render template and check if any variables were undefined
    template = env.from_string(str(doc))
    rendered = template.render(**doc)
    undefined = meta.find_undeclared_variables(env.parse(rendered))

    if len(undefined) != 0:
        raise ValueError(f'undefined variables found in document: {undefined}')


def find_unfilled_mandatory_info(
    result: SearchResult
) -> list[str]:
    """
    Return all mandatory fields that are missing a value
    """
    return [info for info in result.item.mandatory_info
            if getattr(result.item, info) is None]


def find_unfilled_optional_info(
    result: SearchResult
) -> list[str]:
    """
    Return all optional fields that are missing a value
    """
    # cannot getattr for extraneous info, shortcircuit conditional
    return [info for info in list(result.item.keys())
            if info not in result.item.mandatory_info
            and info not in result.item.extraneous.keys()
            and getattr(result.item, info) is None]


def check_unfilled_mandatory_info(result: SearchResult) -> None:
    """
    Check that all mandatory EntryInfo have a value.

    This identifies problems originating from a mismatch between
    an item's backend representation and desired container.
    This may arise from manual editing of the backend database.
    """
    unfilled_info = find_unfilled_mandatory_info(result)
    if len(unfilled_info) != 0:
        raise ValueError(f'unfilled mandatory information found: {unfilled_info}')


def verify_result(
    result: SearchResult,
    check: Callable[[SearchResult], None]
) -> tuple[bool, str, str]:
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


def audit(
    results: list[SearchResult],
    redirect: bool = True,
    verbose: bool = False,
    check_list: Optional[CheckList] = None,
    catch_keyboard_interrupt: bool = True,
) -> AuditResults:
    """
    Audit the given ``SearchResult`` items.

    Parameters
    ----------
    results : list[SearchResult]
        The search results from the happi client to audit.
    redirect : bool
        During the audit process, capture standard output and standard error to
        avoid connection and error-related spam.
    verbose : bool
        Output status messages during the audit process.
    check_list : list[Check]
        The callable checks to perform.
    catch_keyboard_interrupt : bool, optional
        Catch and record when the user attempts to cancel the audit process.

    Returns
    -------
    AuditResults
        The summarized results of the audit.
    """
    if check_list is None:
        # If unspecified, use all checks
        check_list = list(checks)

    test_results: CheckResults = {
        "name": [],
        "success": [],
        "check": [],
        "msg": [],
    }

    @contextlib.contextmanager
    def maybe_redirect():
        if redirect:
            f = io.StringIO()
            with contextlib.redirect_stderr(f), contextlib.redirect_stdout(f):
                yield
        else:
            yield

    try:
        for i, res in enumerate(results):
            if verbose and sys.__stdout__.isatty():
                print(f"checking device #: {i}", end="\r")

            # Capture stdout, stderr for this audit
            with maybe_redirect():
                for check_fn in check_list:
                    try:
                        success, check, msg = verify_result(res, check_fn)
                    except KeyboardInterrupt:
                        test_results["name"].append(res.item.name)
                        test_results["success"].append(False)
                        test_results["check"].append("")
                        test_results["msg"].append("Interrupted by user")
                        raise
                    else:
                        test_results["name"].append(res.item.name)
                        test_results["success"].append(success)
                        test_results["check"].append(check)
                        test_results["msg"].append(msg)
    except KeyboardInterrupt:
        if not catch_keyboard_interrupt:
            raise
        if verbose:
            print("Caught KeyboardInterrupt; exiting early...")

    unique_fails = {
        test_results["name"][i]
        for i in range(len(test_results["name"]))
        if not test_results["success"][i]
    }

    audit_results: AuditResults = {
        "test_results": test_results,
        "audited": len(results),
        "failures": len(unique_fails),
        "failed_names": sorted(unique_fails),
        "items": {
            name: {"failed_check": [], "audit_errors": []}
            for name in [res.item.name for res in results]
        },
    }
    item_info = audit_results["items"]
    for name, success, check, msg in zip(
        test_results["name"],
        test_results["success"],
        test_results["check"],
        test_results["msg"],
    ):
        if not success:
            item_info[name]['failed_check'].append(check)
            item_info[name]['audit_errors'].append(msg)

    return audit_results


checks: List[Check] = [
    check_instantiation,
    check_extra_info,
    check_name_match_id,
    check_wait_connection,
    check_args_kwargs_match,
    check_unfilled_mandatory_info,
]
