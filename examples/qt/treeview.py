import pathlib

from qtpy import QtCore, QtWidgets

import happi
import happi.qt


class HappiDeviceExplorer(QtWidgets.QFrame):
    _GROUP_KEYS = {'Name': 'name',
                   'Type': 'type',
                   'Device Class': 'device_class'}

    def __init__(self, parent=None):
        super().__init__(parent=parent)

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

        self.setLayout(QtWidgets.QVBoxLayout())

        self.filter_frame = QtWidgets.QFrame()
        self.filter_frame.setLayout(QtWidgets.QGridLayout())

        self.filter_frame.layout().addWidget(self.filter_label, 1, 0)
        self.filter_frame.layout().addWidget(self.filter_edit, 1, 1)
        self.filter_frame.layout().addWidget(self.group_label, 2, 0)
        self.filter_frame.layout().addWidget(self.group_combo, 2, 1)

        self.splitter = QtWidgets.QSplitter()
        self.splitter.setOrientation(QtCore.Qt.Vertical)

        self.splitter.addWidget(self.filter_frame)
        self.splitter.addWidget(self.view)
        self.splitter.setSizes([0, 1])
        self.splitter.setHandleWidth(10)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        self.splitter.setCollapsible(1, False)

        handle = self.splitter.handle(1)
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        button = QtWidgets.QToolButton(handle)
        button.setArrowType(QtCore.Qt.DownArrow)
        button.clicked.connect(lambda: self.handle_splitter_button(True))
        layout.addWidget(button)
        button = QtWidgets.QToolButton(handle)
        button.setArrowType(QtCore.Qt.UpArrow)
        button.clicked.connect(lambda: self.handle_splitter_button(False))
        layout.addWidget(button)
        handle.setLayout(layout)

        self.layout().addWidget(self.splitter)

    def handle_splitter_button(self, down=True):
        if down:
            self.splitter.setSizes([1, 1])
        else:
            self.splitter.setSizes([0, 1])


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    file_path = pathlib.Path(__file__).resolve()
    db_path = file_path.parent.parent / "db.json"

    cli = happi.Client(path=db_path)
    w = HappiDeviceExplorer()
    w.view.client = cli
    w.view.search(type='OphydItem')
    w.show()

    app.exec_()
