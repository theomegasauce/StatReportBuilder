from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.statreportbuilder.core.blocks import Block


class ParameterForm(QWidget):
    parameter_changed = Signal(str, object)

    def __init__(
        self,
        block: Block,
        columns_by_input: dict[str, list[str]] | None = None,
        csv_choices: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._block = block
        self._columns_by_input = columns_by_input or {}
        self._csv_choices = csv_choices or []
        self._suppress = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel(block.title)
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        for spec in block.params_spec:
            widget = self._build_widget(spec)
            if widget is not None:
                form.addRow(spec.label, widget)

        layout.addLayout(form)
        layout.addStretch()

    def _build_widget(self, spec) -> QWidget | None:
        current = self._block.params.get(spec.name, spec.default)

        if spec.kind == "string":
            w = QLineEdit()
            w.setText(str(current or ""))
            w.editingFinished.connect(lambda n=spec.name, ww=w: self._emit(n, ww.text()))
            return w

        if spec.kind == "text":
            w = QPlainTextEdit()
            w.setPlainText(str(current or ""))
            w.setFixedHeight(80)
            w.textChanged.connect(lambda n=spec.name, ww=w: self._emit(n, ww.toPlainText()))
            return w

        if spec.kind == "number":
            w = QDoubleSpinBox()
            w.setDecimals(4)
            w.setRange(-1e9, 1e9)
            w.setSingleStep(0.01)
            try:
                w.setValue(float(current))
            except (TypeError, ValueError):
                w.setValue(0.0)
            w.valueChanged.connect(lambda v, n=spec.name: self._emit(n, float(v)))
            return w

        if spec.kind == "boolean":
            w = QCheckBox()
            w.setChecked(bool(current))
            w.toggled.connect(lambda v, n=spec.name: self._emit(n, bool(v)))
            return w

        if spec.kind == "choice":
            w = QComboBox()
            w.addItems(spec.choices or [])
            if current and current in (spec.choices or []):
                w.setCurrentText(str(current))
            w.currentTextChanged.connect(lambda v, n=spec.name: self._emit(n, v))
            return w

        if spec.kind == "file_ref":
            w = QComboBox()
            w.addItem("")
            w.addItems(self._csv_choices)
            if current:
                idx = w.findText(str(current))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            w.currentTextChanged.connect(lambda v, n=spec.name: self._emit(n, v))
            return w

        if spec.kind == "column_ref":
            w = QComboBox()
            columns = self._columns_by_input.get(spec.source or "", [])
            w.addItem("")
            w.addItems(columns)
            if current:
                idx = w.findText(str(current))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            w.currentTextChanged.connect(lambda v, n=spec.name: self._emit(n, v))
            return w

        return None

    def _emit(self, name: str, value: Any) -> None:
        if self._suppress:
            return
        self._block.params[name] = value
        self.parameter_changed.emit(name, value)
