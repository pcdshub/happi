import logging
import collections
from qtpy import QtCore, QtGui, QtWidgets

from ..utils import get_happi_entry_value

logger = logging.getLogger(__name__)


class HappiViewMixin(object):
    """
    Base class to be used for View widgets
    """
    def __init__(self, client=None, **kwargs):
        super().__init__(**kwargs)
        self._client = client
        self._entries = []

    @property
    def client(self):
        """
        The client to use for search.

        Returns
        -------
        happi.Client
        """
        return self._client

    @client.setter
    def client(self, client):
        self._client = client

    def entries(self):
        """
        List of search results.

        Returns
        -------
        list
        """
        return self._entries

    def search(self, *args, **kwargs):
        """
        Performs a search into the Happi database and populate the model
        with the new data.

        args and kwargs are sent directly to happi.Client.search method.
        """
        self._entries = self._client.search(*args, **kwargs)

    @staticmethod
    def create_item(entry):
        itm = QtGui.QStandardItem(entry.name)
        itm.setData(entry)
        itm.setFlags(itm.flags() & ~QtCore.Qt.ItemIsEditable)
        return itm


class HappiDeviceListView(QtWidgets.QListView, HappiViewMixin):
    """
    QListView which displays Happi entries.

    Parameters
    ----------
    parent : QWidget
        The parent widget

    client : Client
        A happi.Client instance

    kwargs : dict
        Additional arguments to be passed to the QListView constructor.
    """
    def __init__(self, parent=None, client=None, **kwargs):
        super().__init__(parent=parent, client=client, **kwargs)
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Devices"])

        self.proxy_model = QtCore.QSortFilterProxyModel()
        self.proxy_model.setFilterKeyColumn(-1)
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setSourceModel(self.model)
        self.setModel(self.proxy_model)

    def search(self, *args, **kwargs):
        """
        Performs a search into the Happi database and populate the model
        with the new data.

        args and kwargs are sent directly to happi.Client.search method.
        """
        super().search(*args, **kwargs)
        self._update_data()

    def _update_data(self):
        """
        Update the model with new data from the search.
        """
        if not self.entries():
            return
        items = [self.create_item(entry) for entry in self.entries()]

        self.model.clear()

        for row, itm in enumerate(items):
            self.model.setItem(row, itm)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.sort(0, QtCore.Qt.AscendingOrder)


class HappiDeviceTreeView(QtWidgets.QTreeView, HappiViewMixin):
    """
    QListView which displays Happi entries.

    Parameters
    ----------
    parent : QWidget
        The parent widget

    client : Client
        A happi.Client instance

    kwargs : dict
        Additional arguments to be passed to the QListView constructor.
    """
    def __init__(self, parent=None, client=None, **kwargs):
        super().__init__(parent=parent, client=client, **kwargs)
        self.setSortingEnabled(True)
        self._models = dict()
        self._groups = []
        self._active_group = ""

        self.proxy_model = QtCore.QSortFilterProxyModel()
        self.proxy_model.setFilterKeyColumn(-1)
        self.proxy_model.setRecursiveFilteringEnabled(True)
        self.proxy_model.setDynamicSortFilter(True)
        self.setModel(self.proxy_model)

    def search(self, *args, **kwargs):
        """
        Performs a search into the Happi database and populate the model
        with the new data.

        args and kwargs are sent directly to happi.Client.search method.
        """
        super().search(*args, **kwargs)
        self._update_data()

    def group_by(self, field, force=False):
        if field and (self._active_group != field or force):
            self._active_group = field
            model = self._models.get(field, None)
            if not model:
                logger.error('Group model for %s does not exist. Update the '
                             'groups information first.')
            self.proxy_model.setSourceModel(model)

    @property
    def groups(self):
        """
        List of fields to be used when grouping Happi entries.

        Returns
        -------
        list
        """
        return self._groups

    @groups.setter
    def groups(self, groups):
        if self._groups != groups and groups:
            self._groups = groups
            if not self._active_group:
                self._active_group = groups[0]
            self._update_data()

    def _create_group_model(self, field, force=False):
        if field in self._models and not force:
            return

        model = QtGui.QStandardItemModel()
        model.setHorizontalHeaderLabels(["Devices"])

        entry_group = collections.defaultdict(list)

        for entry in self.entries():
            try:
                field_val = get_happi_entry_value(entry, field)
                entry_group[field_val].append(entry)
            except ValueError:
                logger.exception(
                    'Could not retrieve value for field %s at entry %s',
                    field, entry
                )

        for idx, (key_value, entries) in enumerate(entry_group.items()):
            root = QtGui.QStandardItem(key_value)
            # Disable edit
            root.setFlags(root.flags() & ~QtCore.Qt.ItemIsEditable)

            if len(entries) == 1 and entries[0].name == key_value:
                root.setData(entries[0])
            else:
                # Pack the entries into the root
                root.setData(entries)

                for entry in entries:
                    root.appendRow(self.create_item(entry))
            model.appendRow(root)

        self._models[field] = model
        return model

    def _update_data(self):
        """
        Update the model with new data from the search.
        """
        for field in self._groups:
            if not field:
                return
            self._create_group_model(field, force=True)
        self.group_by(self._active_group, force=True)
