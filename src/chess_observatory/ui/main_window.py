"""Minimal main window (Phase 0).

This is a real Qt window, not a mock: ``chess-obs ui`` launches it and the
offscreen test suite opens it. Styling arrives with the design tokens in
Phase 6; until then the window stays out of Qt's way so theme tests are not
anchored to placeholder colours.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from chess_observatory import __version__


class MainWindow(QMainWindow):
    """The application window."""

    def __init__(self, *, theme: str = "observatory-dark") -> None:
        super().__init__()
        self._theme = theme
        self.setObjectName("MainWindow")
        self.setWindowTitle("Chess Observatory")
        self.resize(1280, 800)

        central = QWidget(self)
        central.setObjectName("WelcomeScreen")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(12)
        layout.addStretch(1)

        title = QLabel("Chess Observatory", central)
        title.setObjectName("WelcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = title.font()
        title_font.setPointSize(28)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)

        subtitle = QLabel(
            "A computational chess research workstation\n"
            "The designed workspace arrives in Phase 6.",
            central,
        )
        subtitle.setObjectName("WelcomeSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version = QLabel(f"version {__version__} · theme {theme}", central)
        version.setObjectName("WelcomeVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(version)
        layout.addStretch(1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready")

    @property
    def theme(self) -> str:
        """Theme id requested at construction (wired to tokens in Phase 6)."""
        return self._theme
