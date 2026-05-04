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


HIDDEN_RESULT_KEYS = {
    "tables", "plots", "text_sections", "interpretation",
}


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
        browser.setHtml(output_to_html(value))
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


def output_to_html(
    value: Any,
    max_rows: int = 50,
    include_interpretation: bool = False,
) -> str:
    if value is None:
        return "<p style='color:#888;'><em>No output yet.</em></p>"

    if isinstance(value, pd.DataFrame):
        return _df_to_html(value, max_rows)

    if isinstance(value, str):
        if "<html" in value.lower() or "<body" in value.lower():
            return value
        return f"<p>{value}</p>"

    if isinstance(value, dict):
        return _structured_dict_to_html(
            value, max_rows=max_rows, include_interpretation=include_interpretation
        )

    return f"<pre>{value}</pre>"


def _structured_dict_to_html(
    data: dict,
    max_rows: int = 50,
    include_interpretation: bool = False,
) -> str:
    parts: list[str] = []

    text_sections = data.get("text_sections")
    if isinstance(text_sections, list):
        for section in text_sections:
            heading = str(section.get("heading") or "").strip()
            body = str(section.get("body") or "").strip()
            if heading:
                parts.append(f"<h3 style='margin:8px 0 4px 0;'>{heading}</h3>")
            if body:
                parts.append(f"<p style='white-space:pre-wrap;margin:0 0 8px 0;'>{body}</p>")

    tables = data.get("tables")
    if isinstance(tables, list):
        for table in tables:
            name = str(table.get("name") or "").strip()
            df = table.get("data")
            if name:
                parts.append(
                    f"<p style='font-weight:bold;margin:8px 0 4px 0;'>{name}</p>"
                )
            if isinstance(df, pd.DataFrame):
                parts.append(_df_to_html(df, max_rows))

    plots = data.get("plots")
    if isinstance(plots, list):
        for plot in plots:
            png = plot.get("png_base64")
            name = str(plot.get("name") or "").strip()
            if not png:
                continue
            if name:
                parts.append(
                    f"<p style='font-weight:bold;margin:8px 0 4px 0;'>{name}</p>"
                )
            parts.append(
                f"<img src='data:image/png;base64,{png}' "
                "style='max-width:100%;height:auto;display:block;margin:6px 0;'/>"
            )

    if include_interpretation:
        interp = str(data.get("interpretation") or "").strip()
        if interp:
            parts.append(
                f"<p style='margin:8px 0 0 0;'><em>{interp}</em></p>"
            )

    if parts:
        return "".join(parts)

    extras = {k: v for k, v in data.items() if k not in HIDDEN_RESULT_KEYS}
    if extras:
        return _scalar_dict_to_html(extras)
    return "<p style='color:#888;'><em>No output yet.</em></p>"


def _df_to_html(value: pd.DataFrame, max_rows: int = 50) -> str:
    if len(value) == 0:
        return "<p style='color:#888;'><em>(empty table)</em></p>"
    df = value.head(max_rows)
    rows = ["<table style='border-collapse:collapse; margin:6px 0;'>"]
    rows.append("<tr>" + "".join(
        f"<th style='border:1px solid #aaa; padding:4px 8px; background:#eee;'>{c}</th>"
        for c in df.columns
    ) + "</tr>")
    for _, row in df.iterrows():
        cells = []
        for v in row:
            if pd.isna(v):
                text = ""
            elif isinstance(v, float):
                text = f"{v:.4f}"
            else:
                text = str(v)
            cells.append(
                f"<td style='border:1px solid #aaa; padding:4px 8px;'>{text}</td>"
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    rows.append("</table>")
    if len(value) > max_rows:
        rows.append(
            f"<p style='color:#888; font-size:90%;'>"
            f"Showing first {max_rows} of {len(value):,} rows.</p>"
        )
    return "".join(rows)


def _scalar_dict_to_html(data: dict) -> str:
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


def extract_interpretation(value: Any) -> str:
    if isinstance(value, dict):
        text = value.get("interpretation")
        if isinstance(text, str):
            return text.strip()
    return ""
