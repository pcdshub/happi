"""
Helper QObject classes for managing dataclass instances.

Contains utilities for synchronizing dataclass instances between
widgets.
"""
from __future__ import annotations

import functools
import logging
import platform
from typing import Any, Callable, Dict, List, Optional, Tuple

from qtpy import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)


class ThreadWorker(QtCore.QThread):
    """
    Worker thread helper.  For running a function in a background QThread.

    Parameters
    ----------
    func : callable
        The function to call when the thread starts.
    *args
        Arguments for the function call.
    **kwargs
        Keyword arguments for the function call.
    """

    error_raised = QtCore.Signal(Exception)
    returned = QtCore.Signal(object)
    func: Callable
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]
    return_value: Any

    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.return_value = None

    @QtCore.Slot()
    def run(self):
        try:
            self.return_value = self.func(*self.args, **self.kwargs)
        except Exception as ex:
            logger.exception(
                "Failed to run %s(*%s, **%r) in thread pool",
                self.func,
                self.args,
                self.kwargs,
            )
            self.return_value = ex
            self.error_raised.emit(ex)
        else:
            self.returned.emit(self.return_value)


def run_in_gui_thread(
    func: Callable,
    *args,
    _start_delay_ms: int = 0,
    **kwargs
):
    """Run the provided function in the GUI thread."""
    QtCore.QTimer.singleShot(
        _start_delay_ms,
        functools.partial(func, *args, **kwargs)
    )


def get_clipboard() -> Optional[QtGui.QClipboard]:
    """Get the clipboard instance. Requires a QApplication."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        return None

    return QtWidgets.QApplication.clipboard()


def get_clipboard_modes() -> List[int]:
    """
    Get the clipboard modes for the current platform.

    Returns
    -------
    list of int
        Qt-specific modes to try for interacting with the clipboard.
    """
    clipboard = get_clipboard()
    if clipboard is None:
        return []

    if platform.system() == "Linux":
        # Mode selection is only valid for X11.
        return [
            QtGui.QClipboard.Selection,
            QtGui.QClipboard.Clipboard
        ]

    return [QtGui.QClipboard.Clipboard]


def copy_to_clipboard(text: str, *, quiet: bool = False):
    """
    Copy ``text`` to the clipboard.

    Parameters
    ----------
    text : str
        The text to copy to the clipboard.

    quiet : bool, optional, keyword-only
        If quiet is set, do not log the copied text.  Defaults to False.
    """
    clipboard = get_clipboard()
    if clipboard is None:
        return None

    for mode in get_clipboard_modes():
        clipboard.setText(text, mode=mode)
        event = QtCore.QEvent(QtCore.QEvent.Clipboard)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.sendEvent(clipboard, event)

    if not quiet:
        logger.warning(
            (
                "Copied text to clipboard:\n"
                "-------------------------\n"
                "%s\n"
                "-------------------------\n"
            ),
            text
        )


def get_clipboard_text() -> str:
    """
    Get ``text`` from the clipboard. If unavailable or unset, empty string.

    Returns
    -------
    str
        The clipboard text, if available.
    """
    clipboard = get_clipboard()
    if clipboard is None:
        return ""
    for mode in get_clipboard_modes():
        text = clipboard.text(mode=mode)
        if text:
            return text
    return ""
