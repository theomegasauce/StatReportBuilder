from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QMessageBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from src.statreportbuilder.ui.output_renderer import DataFrameModel


class CSVPreviewDialog(QDialog):
    def __init__(self, csv_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Preview — {csv_path.name}")
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            QMessageBox.critical(self, "Preview failed", f"Could not read CSV:\n{exc}")
            self.close()
            return

        info = QLabel(f"{len(df):,} rows × {len(df.columns)} columns")
        info.setStyleSheet("color: #555; padding: 4px;")
        layout.addWidget(info)

        view = QTableView()
        view.setModel(DataFrameModel(df))
        view.setAlternatingRowColors(True)
        layout.addWidget(view)


def csv_summary(csv_path: Path) -> str:
    try:
        df = pd.read_csv(csv_path, nrows=1)
        rows = sum(1 for _ in csv_path.open("r", encoding="utf-8")) - 1
        return f"{rows:,} rows × {len(df.columns)} columns"
    except Exception:
        return ""
