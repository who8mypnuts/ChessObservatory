"""The window opens offscreen and is a real QMainWindow."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow

from chess_observatory.ui.main_window import MainWindow

pytestmark = pytest.mark.ui


def test_main_window_opens(qtbot) -> None:
    window = MainWindow(theme="midnight")
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(20)

    assert isinstance(window, QMainWindow)
    assert window.isVisible()
    assert window.windowTitle() == "Chess Observatory"
    assert window.theme == "midnight"
    assert window.centralWidget() is not None
    assert window.statusBar().currentMessage() == "Ready"


def test_central_labels_are_present(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.findChild(QLabel, "WelcomeTitle") is not None
    assert window.findChild(QLabel, "WelcomeVersion") is not None
