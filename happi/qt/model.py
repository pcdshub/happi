from qtpy import QtCore, QtGui, QtWidgets


class HappiDeviceListView(QtWidgets.QListView):
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
        super().__init__(parent=parent,
                                                  **kwargs)
        self._client = client
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Devices"])

        self.proxy_model = QtCore.QSortFilterProxyModel()
        self.proxy_model.setFilterKeyColumn(-1)
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setSourceModel(self.model)
        self.setModel(self.proxy_model)

        self.models = {}
        self._happi_entries = []

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

    def search(self, *args, **kwargs):
        """
        Performs a search into the Happi database and populate the model
        with the new data.

        args and kwargs are sent directly to happi.Client.search method.
        """
        self._happi_entries = self._client.search(*args, **kwargs)
        self._update_data()

    def _update_data(self):
        """
        Update the model with new data from the search.
        """
        def create_item(entry):
            itm = QtGui.QStandardItem(entry.name)
            itm.setData(entry)
            itm.setFlags(itm.flags() & ~QtCore.Qt.ItemIsEditable)
            return itm

        items = [create_item(entry) for entry in self._happi_entries]
        if not self._happi_entries:
            return
        for entry in self._happi_entries:
            items.append(create_item(entry))

        self.model.clear()

        for row, itm in enumerate(items):
            self.model.setItem(row, itm)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.sort(0, QtCore.Qt.AscendingOrder)
