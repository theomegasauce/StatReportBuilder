from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.statreportbuilder.core.blocks import Block
from src.statreportbuilder.ui.output_renderer import render_error, render_output
from src.statreportbuilder.ui.parameter_form import ParameterForm


@dataclass
class NodeContext:
    block: Block
    result: dict[str, Any] | None
    columns_by_input: dict[str, list[str]]
    csv_choices: list[str]


class TechnicalOutputView(QWidget):
    parameter_changed = Signal(str, str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._splitter = QSplitter(Qt.Vertical)
        self._splitter.setChildrenCollapsible(False)

        self._params_host = QWidget()
        self._params_layout = QVBoxLayout(self._params_host)
        self._params_layout.setContentsMargins(0, 0, 0, 0)
        self._set_params_placeholder()

        self._output_host = QWidget()
        self._output_layout = QVBoxLayout(self._output_host)
        self._output_layout.setContentsMargins(0, 0, 0, 0)
        self._set_output_placeholder()

        self._splitter.addWidget(self._params_host)
        self._splitter.addWidget(self._output_host)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 2)
        self._splitter.setSizes([220, 420])

        layout.addWidget(self._splitter)

        self._current_node_id: str | None = None

    def show_node(self, ctx: NodeContext | None) -> None:
        self._clear(self._params_layout)

        if ctx is None:
            self._current_node_id = None
            self._set_params_placeholder()
            self.refresh_output(None)
            return

        self._current_node_id = ctx.block.node_id

        form = ParameterForm(
            ctx.block,
            columns_by_input=ctx.columns_by_input,
            csv_choices=ctx.csv_choices,
        )
        form.parameter_changed.connect(self._on_param_changed)
        self._params_layout.addWidget(form)

        self.refresh_output(ctx)

    def refresh_output(self, ctx: NodeContext | None) -> None:
        self._clear(self._output_layout)

        if ctx is None:
            self._set_output_placeholder()
            return

        if ctx.result is None:
            self._set_output_placeholder("No output yet — block has not been executed.")
        elif "_error" in ctx.result:
            self._output_layout.addWidget(render_error(ctx.result["_error"]))
        else:
            value = self._primary_output(ctx.block, ctx.result)
            self._output_layout.addWidget(render_output(value))

    @staticmethod
    def _primary_output(block: Block, result: dict[str, Any]) -> Any:
        if not block.outputs:
            return None
        return result.get(block.outputs[0].name)

    def _on_param_changed(self, name: str, value: Any) -> None:
        if self._current_node_id is not None:
            self.parameter_changed.emit(self._current_node_id, name, value)

    def _set_params_placeholder(self) -> None:
        label = QLabel("Select a node to edit its parameters.")
        label.setStyleSheet("color: gray;")
        label.setAlignment(Qt.AlignCenter)
        self._params_layout.addWidget(label)

    def _set_output_placeholder(self, text: str = "Output for the selected node will render here.") -> None:
        label = QLabel(text)
        label.setStyleSheet("color: gray;")
        label.setAlignment(Qt.AlignCenter)
        self._output_layout.addWidget(label)

    @staticmethod
    def _clear(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()


class ReportPreviewView(QWidget):
    export_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 6, 8, 6)
        toolbar_layout.addStretch()

        export_btn = QToolButton()
        export_btn.setText("Export")
        export_btn.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(export_btn)
        for fmt in ("PDF", "HTML", "DOCX"):
            action = QAction(fmt, menu)
            action.triggered.connect(lambda _checked=False, f=fmt: self.export_requested.emit(f))
            menu.addAction(action)
        export_btn.setMenu(menu)
        toolbar_layout.addWidget(export_btn)

        layout.addWidget(toolbar)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._set_placeholder()
        layout.addWidget(self._browser, stretch=1)

    def set_html(self, html: str | None) -> None:
        if not html:
            self._set_placeholder()
            return
        self._browser.setHtml(html)

    def _set_placeholder(self) -> None:
        self._browser.setHtml(
            "<h2 style='color:#888;text-align:center;margin-top:80px;'>"
            "Compiled report will render here"
            "</h2>"
        )


class OutputReportPane(QWidget):
    parameter_changed = Signal(str, str, object)
    export_requested = Signal(str)
    view_changed = Signal(int)

    VIEW_OUTPUT = 0
    VIEW_REPORT = 1

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(300)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        toggle_bar = QWidget()
        toggle_layout = QHBoxLayout(toggle_bar)
        toggle_layout.setContentsMargins(8, 8, 8, 8)
        toggle_layout.setSpacing(0)

        self._btn_output = QPushButton("Output / Edit")
        self._btn_report = QPushButton("Report")
        for btn in (self._btn_output, self._btn_report):
            btn.setCheckable(True)
            btn.setMinimumWidth(110)
        self._btn_output.setChecked(True)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.addButton(self._btn_output, self.VIEW_OUTPUT)
        self._group.addButton(self._btn_report, self.VIEW_REPORT)
        self._group.idClicked.connect(self._on_view_changed)

        toggle_layout.addWidget(self._btn_output)
        toggle_layout.addWidget(self._btn_report)
        toggle_layout.addStretch()

        root.addWidget(toggle_bar)

        self._stack = QStackedWidget()
        self._technical = TechnicalOutputView()
        self._report = ReportPreviewView()

        self._technical.parameter_changed.connect(self.parameter_changed)
        self._report.export_requested.connect(self.export_requested)

        self._stack.addWidget(self._technical)
        self._stack.addWidget(self._report)
        root.addWidget(self._stack, stretch=1)

    def _on_view_changed(self, view_id: int) -> None:
        self._stack.setCurrentIndex(view_id)
        self.view_changed.emit(view_id)

    def set_view(self, view_id: int) -> None:
        button = self._group.button(view_id)
        if button is not None:
            button.setChecked(True)
            self._on_view_changed(view_id)

    def current_view(self) -> int:
        return self._stack.currentIndex()

    def show_node(self, ctx: NodeContext | None) -> None:
        self._technical.show_node(ctx)

    def refresh_output(self, ctx: NodeContext | None) -> None:
        self._technical.refresh_output(ctx)

    def set_report_html(self, html: str | None) -> None:
        self._report.set_html(html)
