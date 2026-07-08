"""Manual test runner: opens the real GUI with the actual shutdown call
mocked out, so the button/card/scanline animation can be exercised live
without ever scheduling a real shutdown. Not part of the shipped app.

Run with:
    .venv\\Scripts\\pythonw test_live.py
"""
import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

import main as m


def fake_execute_shutdown_command(seconds):
    print(f"[TEST MODE] Would have run: shutdown /s /t {seconds}  -- not actually run")
    return True


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(m.resource_path('assets', 'icon.png')))
    m.load_bundled_fonts()

    main_window = m.LifeControlButtonApp()
    main_window.execute_shutdown_command = fake_execute_shutdown_command

    main_window.center_window_on_primary_monitor()
    main_window.show()
    sys.exit(app.exec())
