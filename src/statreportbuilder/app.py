import sys
import traceback

from PySide6.QtWidgets import QApplication

from src.statreportbuilder.ui.main_window import MainWindow
from src.statreportbuilder.ui.theme import GLOBAL_STYLESHEET


def run() -> int:
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("StatReportBuilder")
        app.setStyleSheet(GLOBAL_STYLESHEET)

        window = MainWindow()
        window.show()

        return app.exec()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1
