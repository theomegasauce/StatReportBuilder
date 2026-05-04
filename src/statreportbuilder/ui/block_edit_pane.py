from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.statreportbuilder.core.blocks import Block
from src.statreportbuilder.ui.parameter_form import ParameterForm


@dataclass
class BlockEditContext:
    block: Block
    columns_by_input: dict[str, list[str]]
    csv_choices: list[str]


class BlockEditPane(QWidget):
    parameter_changed = Signal(str, str, object)
    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BlockEditPane")
        self.setStyleSheet(
            "#BlockEditPane { background: #fafbfc; border-top: 1px solid #d4d6da; }"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header.setStyleSheet("background: #eef2f7;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 4, 4)
        self._title = QLabel("Block options")
        self._title.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self._title)
        header_layout.addStretch()

        close_btn = QToolButton()
        close_btn.setText("×")
        close_btn.setToolTip("Close (selecting a block reopens this pane)")
        close_btn.setAutoRaise(True)
        close_btn.setStyleSheet("QToolButton { font-size: 16px; padding: 0 6px; }")
        close_btn.clicked.connect(self.close_requested)
        header_layout.addWidget(close_btn)

        root.addWidget(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        root.addWidget(self._scroll, stretch=1)

        self._current_node_id: str | None = None
        self._set_placeholder()

    def show_block(self, ctx: BlockEditContext | None) -> None:
        if ctx is None:
            self._current_node_id = None
            self._title.setText("Block options")
            self._set_placeholder()
            return

        self._current_node_id = ctx.block.node_id
        self._title.setText(f"Options · {ctx.block.title}")

        form = ParameterForm(
            ctx.block,
            columns_by_input=ctx.columns_by_input,
            csv_choices=ctx.csv_choices,
        )
        form.parameter_changed.connect(self._on_param_changed)
        self._scroll.setWidget(form)

    def _set_placeholder(self) -> None:
        label = QLabel("Select a block to edit its options.")
        label.setStyleSheet("color: gray; padding: 16px;")
        label.setAlignment(Qt.AlignCenter)
        self._scroll.setWidget(label)

    def _on_param_changed(self, name: str, value: Any) -> None:
        if self._current_node_id is not None:
            self.parameter_changed.emit(self._current_node_id, name, value)

    def current_node_id(self) -> str | None:
        return self._current_node_id
