import pathlib
from qtpy import QtWidgets

import happi
import happi.qt


class HappiDeviceExplorer(QtWidgets.QFrame):
    _GROUP_KEYS = {'Name': 'name',
                   'Function': 'functional_group',
                   'Location': 'location_group'}

    def __init__(self, parent=None):
        super(HappiDeviceExplorer, self).__init__(parent=parent)

        self.view = happi.qt.model.HappiDeviceTreeView(self)
        self.view.groups = [v for _, v in self._GROUP_KEYS.items()]

        self.group_label = QtWidgets.QLabel("&Group By")
        self.group_combo = QtWidgets.QComboBox()
        self.group_label.setBuddy(self.group_combo)

        for display, val in self._GROUP_KEYS.items():
            self.group_combo.addItem(display, val)

        def set_group(_):
            key = self.group_combo.currentData()
            self.view.group_by(key)

        self.group_combo.currentIndexChanged.connect(set_group)

        self.filter_label = QtWidgets.QLabel("&Filter")
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_label.setBuddy(self.filter_edit)

        def set_filter(text):
            self.view.proxy_model.setFilterRegExp(text)

        self.filter_edit.textEdited.connect(set_filter)

        self.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.filter_label, 1, 0)
        self.layout().addWidget(self.filter_edit, 1, 1)
        self.layout().addWidget(self.group_label, 2, 0)
        self.layout().addWidget(self.group_combo, 2, 1)
        self.layout().addWidget(self.view, 3, 0, 1, 2)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    file_path = pathlib.Path(__file__).resolve()
    db_path = file_path.parent.parent / "db.json"
    cli = happi.Client(path=db_path)
    w = HappiDeviceExplorer()
    w.view.client = cli
    w.view.search(beamline="DEMO_BEAMLINE")
    w.show()

    app.exec_()