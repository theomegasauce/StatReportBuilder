from __future__ import annotations

from typing import Any

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, Qt
from PySide6.QtWidgets import (
    QLabel,
    QTableView,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class DataFrameModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame, max_rows: int = 200) -> None:
        super().__init__()
        self._df = df.head(max_rows)

    def rowCount(self, parent=None) -> int:
        return len(self._df)

    def columnCount(self, parent=None) -> int:
        return len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if role != Qt.DisplayRole or not index.isValid():
            return None
        value = self._df.iat[index.row(), index.column()]
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:.4f}"
        return str(value)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._df.columns[section])
        return str(self._df.index[section])


def render_output(value: Any) -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    if value is None:
        label = QLabel("No output yet. Configure parameters or run upstream blocks.")
        label.setStyleSheet("color: gray;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        return container

    if isinstance(value, pd.DataFrame):
        view = QTableView()
        view.setModel(DataFrameModel(value))
        view.horizontalHeader().setStretchLastSection(True)
        view.setAlternatingRowColors(True)
        info = QLabel(
            f"{len(value):,} rows × {len(value.columns)} columns "
            f"(showing first {min(len(value), 200)})"
        )
        info.setStyleSheet("color: gray; padding: 4px;")
        layout.addWidget(view, stretch=1)
        layout.addWidget(info)
        return container

    if isinstance(value, str) and ("<html" in value.lower() or "<body" in value.lower()):
        browser = QTextBrowser()
        browser.setHtml(value)
        layout.addWidget(browser)
        return container

    if isinstance(value, dict):
        browser = QTextBrowser()
        browser.setHtml(_dict_to_html(value))
        layout.addWidget(browser)
        return container

    label = QLabel(str(value))
    label.setWordWrap(True)
    layout.addWidget(label)
    return container


def render_error(message: str) -> QWidget:
    label = QLabel(f"Error:\n\n{message}")
    label.setWordWrap(True)
    label.setStyleSheet(
        "color: #883333; background: #fbeaea; border: 1px solid #c99; padding: 12px;"
    )
    label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    return label


def _dict_to_html(data: dict) -> str:
    rows = []
    for key, value in data.items():
        if isinstance(value, float):
            display = f"{value:.4f}"
        else:
            display = str(value)
        rows.append(
            f"<tr><th style='text-align:left;padding:4px 12px;'>{key}</th>"
            f"<td style='padding:4px 12px;'>{display}</td></tr>"
        )
    return (
        "<table style='border-collapse:collapse;font-family:Arial,sans-serif;'>"
        + "".join(rows)
        + "</table>"
    )
