"""Qt launch path.

Kept in ``ui/`` so the import-graph rule is simple: only this package may import
PySide6. The CLI imports :func:`run` lazily and never pulls in Qt for commands
that do not need a window.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from chess_observatory import __version__
from chess_observatory.config import Config
from chess_observatory.ui.main_window import MainWindow


def run(config: Config, *, smoke: bool = False) -> int:
    """Open the workspace.

    With ``smoke=True`` the window is opened, events are processed once, and the
    window is closed again: the CI proof that the GUI starts offscreen.
    """
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(sys.argv[:1])
    app.setApplicationName("Chess Observatory")
    app.setApplicationVersion(__version__)

    window = MainWindow(theme=config.ui.theme)
    window.show()
    if smoke:
        app.processEvents()
        window.close()
        app.processEvents()
        return 0
    return int(app.exec())
