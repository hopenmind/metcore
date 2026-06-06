"""`hopenmind-gui` executable entry point."""

from __future__ import annotations

import sys


def main() -> int:
    from PyQt6.QtWidgets import QApplication

    from metcore_gui.main_window import build_main_window

    app = QApplication.instance() or QApplication(sys.argv)
    win = build_main_window(show=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
