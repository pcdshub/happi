"""
Core classes for Qt-based display GUIs.
"""
import sys
from typing import Any, ClassVar

from qtpy.uic import loadUiType

from ..utils import HAPPI_SOURCE_PATH


class DesignerDisplay:
    """Helper class for loading designer .ui files and adding logic."""
    filename: ClassVar[str]
    ui_form: ClassVar[Any]

    def __init_subclass__(cls):
        """Read the file when the class is created"""
        super().__init_subclass__()
        cls.ui_form, _ = loadUiType(
            str(HAPPI_SOURCE_PATH / "qt" / cls.filename)
        )

    def __init__(self, *args, **kwargs):
        """Apply the file to this widget when the instance is created"""
        super().__init__(*args, **kwargs)
        self.ui_form.setupUi(self, self)

    def retranslateUi(self, *args, **kwargs):
        """Required function for setupUi to work in __init__"""
        self.ui_form.retranslateUi(self, *args, **kwargs)

    def show_type_hints(self, fp=sys.stdout):
        """
        Show type hints of widgets included in the display for development
        purposes.

        Parameters
        ----------
        fp : file-like object, optional
            Defaults to ``sys.stdout``.
        """
        cls_attrs = set()
        obj_attrs = set(dir(self))
        annotated = set(self.__annotations__)
        for cls in type(self).mro():
            cls_attrs |= set(dir(cls))
        likely_from_ui = obj_attrs - cls_attrs - annotated
        for attr in sorted(likely_from_ui):
            try:
                obj = getattr(self, attr, None)
            except Exception:
                ...
            else:
                if obj is None:
                    continue

                print(
                    f"{attr}: {obj.__class__.__module__}"
                    f".{obj.__class__.__name__}",
                    file=fp
                )
