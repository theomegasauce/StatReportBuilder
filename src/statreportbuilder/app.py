import sys

from PySide6.QtWidgets import QApplication

from src.statreportbuilder.ui.main_window import MainWindow
from src.statreportbuilder.ui.theme import GLOBAL_STYLESHEET


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("StatReportBuilder")
    app.setStyleSheet(GLOBAL_STYLESHEET)

    window = MainWindow()
    window.show()

    return app.exec()
