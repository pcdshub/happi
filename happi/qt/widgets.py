"""
Widget classes designed for atef-to-happi interaction.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Dict, List, Optional, Union

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtWidgets import QWidget

import happi
from happi.qt.model import (HappiDeviceListView, HappiDeviceTreeView,
                            HappiViewMixin)

from .designer import DesignerDisplay
from .helpers import ThreadWorker, copy_to_clipboard

logger = logging.getLogger(__name__)


class HappiSearchWidget(DesignerDisplay, QWidget):
    """
    Happi item (device) search widget.

    This widget includes a list view and a tree view for showing all items
    in happi.

    It provides the following signals:
    * ``happi_items_selected`` - one or more happi items were selected.
    * ``happi_items_chosen`` - one or more happi items were chosen by the user.

    To configure multi-item selection, external configuration of
    ``happi_list_view`` and ``happi_tree_view`` are currently required.

    Parameters
    ----------
    parent : QWidget, optional
        The parent widget.

    client : happi.Client, optional
        Happi client instance.  May be supplied at initialization time or
        later.
    """
    filename: ClassVar[str] = 'happi_search_widget.ui'
    happi_items_selected: ClassVar[QtCore.Signal] = QtCore.Signal(
        "QStringList"
    )
    happi_items_chosen: ClassVar[QtCore.Signal] = QtCore.Signal(
        "QStringList"
    )

    _client: Optional[happi.client.Client]
    _last_selected: List[str]
    _search_thread: Optional[ThreadWorker]
    _tree_current_category: str
    _tree_updated: bool
    button_choose: QtWidgets.QPushButton
    button_refresh: QtWidgets.QPushButton
    combo_by_category: QtWidgets.QComboBox
    device_selection_group: QtWidgets.QGroupBox
    edit_filter: QtWidgets.QLineEdit
    happi_list_view: HappiDeviceListView
    happi_tree_view: HappiDeviceTreeView
    label_filter: QtWidgets.QLabel
    layout_by_name: QtWidgets.QHBoxLayout
    list_or_tree_frame: QtWidgets.QFrame
    radio_by_category: QtWidgets.QRadioButton
    radio_by_name: QtWidgets.QRadioButton

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        client: Optional[happi.Client] = None,
    ):
        super().__init__(parent=parent)
        self._client = None
        self._last_selected = []
        self._tree_current_category = "beamline"
        self._search_thread = None
        self._tree_has_data = False
        self._setup_ui()
        # Set the client at the end, as this may trigger an update:
        self.client = client

    def _setup_ui(self):
        """Configure UI elements at init time."""
        self._setup_tree_view()
        self._setup_list_view()

        def record_selected_items(items: List[str]):
            self._last_selected = items

        self.happi_items_selected.connect(record_selected_items)

        def items_chosen():
            self.happi_items_chosen.emit(list(self._last_selected))

        self.button_refresh.clicked.connect(self.refresh_happi)
        self.button_choose.clicked.connect(items_chosen)
        self.list_or_tree_frame.layout().insertWidget(0, self.happi_list_view)

        self.radio_by_name.clicked.connect(self._select_device_widget)
        self.radio_by_category.clicked.connect(self._select_device_widget)
        self.combo_by_category.currentTextChanged.connect(
            self._category_changed
        )
        self.button_refresh.clicked.emit()

    def _setup_list_view(self):
        """Set up the happi_list_view."""
        def list_selection_changed(
            selected: QtCore.QItemSelection,
            deselected: QtCore.QItemSelection
        ):
            self.happi_items_selected.emit(
                [idx.data() for idx in selected.indexes()]
            )

        view = self.happi_list_view
        view.selectionModel().selectionChanged.connect(
            list_selection_changed
        )

        def item_double_clicked(index: QtCore.QModelIndex):
            self.happi_items_chosen.emit([index.data()])

        view.doubleClicked.connect(item_double_clicked)

        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        view.customContextMenuRequested.connect(
            self._list_view_context_menu
        )

        self.edit_filter.textEdited.connect(self._update_filter)

    def _setup_tree_view(self):
        """Set up the happi_tree_view."""
        view = self.happi_tree_view
        view.setVisible(False)
        view.groups = [
            self.combo_by_category.itemText(idx)
            for idx in range(self.combo_by_category.count())
        ]
        self.list_or_tree_frame.layout().insertWidget(0, view)

        def tree_selection_changed(
            selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection
        ):
            items = [
                idx.data() for idx in selected.indexes()
                if idx.parent().data() is not None  # skip top-level items
            ]
            self.happi_items_selected.emit(items)

        view.selectionModel().selectionChanged.connect(
            tree_selection_changed
        )

        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        view.customContextMenuRequested.connect(self._tree_view_context_menu)

        self.edit_filter.textEdited.connect(self._update_filter)
        view.proxy_model.setRecursiveFilteringEnabled(True)

    def _update_filter(self, text: Optional[str] = None) -> None:
        """
        Update the list/tree view filters based on the ``edit_filter`` text.
        """
        if text is None:
            text = self.edit_filter.text()

        text = text.strip()
        self.happi_list_view.proxy_model.setFilterRegExp(text)
        self.happi_tree_view.proxy_model.setFilterRegExp(text)

    def _tree_view_context_menu(self, pos: QtCore.QPoint) -> None:
        """Context menu for the happi tree view."""
        self.menu = QtWidgets.QMenu(self)
        index: QtCore.QModelIndex = self.happi_tree_view.indexAt(pos)
        if index is not None:
            def copy(*_):
                copy_to_clipboard(index.data())

            copy_action = self.menu.addAction(f"&Copy: {index.data()}")
            copy_action.triggered.connect(copy)

        self.menu.exec_(self.happi_tree_view.mapToGlobal(pos))

    def _list_view_context_menu(self, pos: QtCore.QPoint) -> None:
        """Context menu for the happi list view."""
        self.menu = QtWidgets.QMenu(self)
        index: QtCore.QModelIndex = self.happi_list_view.indexAt(pos)
        if index is not None:
            def copy(*_):
                copy_to_clipboard(index.data())

            copy_action = self.menu.addAction(f"&Copy: {index.data()}")
            copy_action.triggered.connect(copy)

        self.menu.exec_(self.happi_list_view.mapToGlobal(pos))

    @property
    def selected_device_widget(self) -> Union[
        HappiDeviceListView, HappiDeviceTreeView
    ]:
        """The selected device widget - either the list or tree view."""
        if self.radio_by_name.isChecked():
            return self.happi_list_view

        return self.happi_tree_view

    @QtCore.Slot(str)
    def _category_changed(self, category: str):
        """By-category category has changed."""
        if self._tree_has_data and self._tree_current_category == category:
            return

        self._tree_current_category = category
        self.happi_tree_view.group_by(category)
        # Bugfix (?) otherwise this ends up in descending order
        self.happi_tree_view.model().sort(0, QtCore.Qt.AscendingOrder)
        self.radio_by_category.setChecked(True)
        self._select_device_widget()

    @QtCore.Slot()
    def _select_device_widget(self):
        """Switch between the list/table view."""
        selected = self.selected_device_widget
        for widget in (self.happi_tree_view, self.happi_list_view):
            widget.setVisible(selected is widget)

        if self.happi_tree_view.isVisible() and not self._tree_has_data:
            self._tree_has_data = True
            self.refresh_happi()

    @QtCore.Slot()
    def refresh_happi(self):
        """Search happi again and update the widgets."""
        def search():
            # TODO/upstream: this is coupled with 'search' in the view
            HappiViewMixin.search(self.selected_device_widget)

        def update_gui():
            # TODO/upstream: this is coupled with 'search' in the view
            self.selected_device_widget._update_data()
            self.button_refresh.setEnabled(True)
            self._update_filter()

        def report_error(ex: Exception):
            logger.warning(
                "Failed to update happi information: %s",
                ex, exc_info=ex
            )
            self.button_refresh.setEnabled(True)

        if self._client is None:
            return
        if self._search_thread is not None and self._search_thread.isRunning():
            return

        self.button_refresh.setEnabled(False)
        self._search_thread = ThreadWorker(search)
        self._search_thread.finished.connect(update_gui)
        self._search_thread.error_raised.connect(report_error)
        self._search_thread.start()

    @property
    def client(self) -> Optional[happi.Client]:
        """The client to use for search."""
        return self._client

    @client.setter
    def client(self, client: Optional[happi.Client]):
        self._client = client
        self.happi_tree_view.client = client
        self.happi_list_view.client = client
        self.refresh_happi()


class HappiItemMetadataView(DesignerDisplay, QtWidgets.QWidget):
    """
    Happi item (device) metadata information widget.

    This widget contains a table that displays key and value information
    as provided from the happi client.

    The default context menu allows for copying of keys or values.

    It emits an ``updated_metadata(item_name: str, md: dict)`` when the
    underlying model is updated.

    Parameters
    ----------
    parent : QWidget, optional
        The parent widget.

    client : happi.Client, optional
        Happi client instance.  May be supplied at initialization time or
        later.
    """
    filename: ClassVar[str] = 'happi_metadata_view.ui'
    updated_metadata: ClassVar[QtCore.Signal] = QtCore.Signal(str, object)

    _client: Optional[happi.client.Client]
    _item_name: Optional[str]
    item: Optional[happi.HappiItem]
    label_title: QtWidgets.QLabel
    model: QtGui.QStandardItemModel
    proxy_model: QtCore.QSortFilterProxyModel
    table_view: QtWidgets.QTableView
    _metadata: Dict[str, Any]

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        client: Optional[happi.Client] = None,
        item_name: Optional[str] = None,
    ):
        super().__init__(parent=parent)
        self._client = None
        self._item_name = None
        self._item = None
        self._setup_ui()
        # Set the client/item at the end, as this may trigger an update:
        self.client = client
        self.item_name = item_name

    def _setup_ui(self):
        """Configure UI elements at init time."""
        self.model = QtGui.QStandardItemModel()

        self.proxy_model = QtCore.QSortFilterProxyModel()
        self.proxy_model.setFilterKeyColumn(-1)
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setSourceModel(self.model)
        self.table_view.setModel(self.proxy_model)

        self.table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(
            self._table_context_menu
        )

    def _table_context_menu(self, pos: QtCore.QPoint) -> None:
        """Context menu when the key/value table is right-clicked."""
        self.menu = QtWidgets.QMenu(self)
        index: QtCore.QModelIndex = self.table_view.indexAt(pos)
        if index is not None:
            def copy(*_):
                copy_to_clipboard(index.data())

            copy_action = self.menu.addAction(f"&Copy: {index.data()}")
            copy_action.triggered.connect(copy)

        self.menu.exec_(self.table_view.mapToGlobal(pos))

    def _update_metadata(self):
        """
        Update the metadata based on ``self.item_name`` using the configured
        client.
        """
        if self.client is None or self.item_name is None:
            return

        try:
            self.item = self.client[self.item_name]
        except KeyError:
            self.item = None

        metadata = dict(self.item or {})
        self._metadata = metadata
        self.updated_metadata.emit(self.item_name, metadata)
        self.model.clear()
        if self.item is None:
            self.label_title.setText("")
            return

        self.label_title.setText(metadata["name"])
        self.model.setHorizontalHeaderLabels(["Key", "Value"])
        skip_keys = {"_id", "name"}
        for key, value in sorted(metadata.items()):
            if key in skip_keys:
                continue

            key_item = QtGui.QStandardItem(str(key))
            value_item = QtGui.QStandardItem(str(value))
            key_item.setFlags(key_item.flags() & ~QtCore.Qt.ItemIsEditable)
            value_item.setFlags(value_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.model.appendRow([key_item, value_item])

    @property
    def client(self) -> Optional[happi.Client]:
        """The client to use for search."""
        return self._client

    @client.setter
    def client(self, client: Optional[happi.Client]):
        self._client = client
        self._update_metadata()

    @property
    def item_name(self) -> Optional[str]:
        """The item name to search for metadata."""
        return self._item_name

    @item_name.setter
    def item_name(self, item_name: Optional[str]):
        self._item_name = item_name
        self._update_metadata()

    @property
    def metadata(self) -> Dict[str, Any]:
        """The current happi item metadata, as a dictionary."""
        return dict(self._metadata)
