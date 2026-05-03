import sys

from PySide6.QtWidgets import QApplication

from src.statreportbuilder.ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("StatReportBuilder")

    window = MainWindow()
    window.show()

    return app.exec()
