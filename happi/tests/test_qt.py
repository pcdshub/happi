import pytest

from happi.client import Client

try:
    from pytestqt.qtbot import QtBot

    from happi.qt.widgets import HappiItemMetadataView, HappiSearchWidget
    qt_missing = False
except ImportError:
    class QtBot:
        pass

    HappiSearchWidget = None
    HappiItemMetadataView = None
    qt_missing = True


@pytest.mark.skipif(qt_missing, reason="qt packages not installed")
def test_search_widget(qtbot: QtBot, mockjsonclient: Client):
    search_widget = HappiSearchWidget(client=mockjsonclient)
    qtbot.addWidget(search_widget)


@pytest.mark.skipif(qt_missing, reason="qt packages not installed")
def test_item_view(qtbot: QtBot, mockjsonclient: Client):
    search_widget = HappiItemMetadataView(client=mockjsonclient)
    qtbot.addWidget(search_widget)
