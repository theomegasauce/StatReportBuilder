from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.statreportbuilder.core.blocks import Block
from src.statreportbuilder.core.graph import Graph
from src.statreportbuilder.ui.output_renderer import (
    extract_interpretation,
    output_to_html,
)
from src.statreportbuilder.ui.theme import category_color


PAGE_FORMATS = ["A4", "Letter", "Legal"]
OVERRIDE_TITLE = "title"
OVERRIDE_NARRATIVE = "narrative"
NARRATIVE_SEEDED_FLAG = "narrative_seeded"


@dataclass
class BlockSnapshot:
    node_id: str
    block: Block
    result: dict[str, Any] | None
    overrides: dict[str, str]


def _primary_output(block: Block, result: dict[str, Any] | None) -> Any:
    if result is None or "_error" in result:
        return None
    if not block.outputs:
        return None
    return result.get(block.outputs[0].name)


def _effective_title(block: Block, overrides: dict[str, str]) -> str:
    override = (overrides.get(OVERRIDE_TITLE) or "").strip()
    if override:
        return override
    params_title = str(block.params.get("title") or "").strip()
    return params_title or block.title


def _effective_narrative(
    snapshot: "BlockSnapshot",
) -> str:
    if OVERRIDE_NARRATIVE in snapshot.overrides:
        return snapshot.overrides.get(OVERRIDE_NARRATIVE, "")
    return extract_interpretation(_primary_output(snapshot.block, snapshot.result))


class _BlockCard(QFrame):
    override_changed = Signal(str, str, str)

    def __init__(self, snapshot: BlockSnapshot, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._node_id = snapshot.node_id
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #cdd7e3; border-radius: 6px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(6)
        self._title_edit = QLineEdit()
        self._title_edit.setText(_effective_title(snapshot.block, snapshot.overrides))
        self._title_edit.setPlaceholderText("Section title")
        self._title_edit.setStyleSheet(
            "QLineEdit { font-weight: bold; font-size: 13px; color: #1f5fa8; "
            "background: transparent; border: 1px solid transparent; padding: 2px 4px; }"
            "QLineEdit:focus { border: 1px solid #4a90e2; background: #fafcff; }"
            "QLineEdit:hover { border: 1px solid #cdd7e3; }"
        )
        self._title_edit.editingFinished.connect(self._emit_title)
        header.addWidget(self._title_edit, stretch=1)

        category = getattr(snapshot.block, "category", "")
        badge_bg = category_color(category, "bg")
        badge_fg = category_color(category, "accent")

        badge = QLabel(f"{snapshot.block.title}  ·  {snapshot.node_id}")
        badge.setStyleSheet(
            f"color: {badge_fg}; font-size: 10px; font-weight: bold; padding: 2px 6px; "
            f"background: {badge_bg}; border-radius: 3px; border: none;"
        )
        header.addWidget(badge)
        layout.addLayout(header)

        self._narrative = QPlainTextEdit()
        self._narrative.setPlainText(_effective_narrative(snapshot))
        self._narrative.setPlaceholderText(
            "Narrative for this section… (included verbatim above the block output)"
        )
        self._narrative.setFixedHeight(80)
        self._narrative.setStyleSheet(
            "QPlainTextEdit { border: 1px solid #cdd7e3; border-radius: 4px; "
            "background: #fafcff; }"
        )
        self._narrative.textChanged.connect(self._emit_narrative)
        layout.addWidget(self._narrative)

        layout.addWidget(self._build_output_view(snapshot))

    def _build_output_view(self, snapshot: BlockSnapshot) -> QWidget:
        if snapshot.result is not None and "_error" in snapshot.result:
            label = QLabel(f"Error: {snapshot.result['_error']}")
            label.setWordWrap(True)
            label.setStyleSheet(
                "color: #883333; background: #fbeaea; border: 1px solid #c99; "
                "padding: 8px; border-radius: 4px;"
            )
            return label

        value = _primary_output(snapshot.block, snapshot.result)
        if value is None:
            label = QLabel("No output yet — connect upstream blocks or set required parameters.")
            label.setStyleSheet("color: #888; padding: 6px; border: none;")
            label.setAlignment(Qt.AlignCenter)
            return label

        browser = QTextBrowser()
        browser.setOpenLinks(False)
        browser.setStyleSheet(
            "QTextBrowser { border: 1px solid #d6dee9; border-radius: 4px; "
            "background: #fafcff; padding: 4px; }"
        )
        browser.setHtml(output_to_html(value))
        browser.setMinimumHeight(80)
        browser.setMaximumHeight(280)
        return browser

    def _emit_title(self) -> None:
        self.override_changed.emit(self._node_id, OVERRIDE_TITLE, self._title_edit.text())

    def _emit_narrative(self) -> None:
        self.override_changed.emit(
            self._node_id, OVERRIDE_NARRATIVE, self._narrative.toPlainText()
        )


class RenderOptionsRegion(QWidget):
    setting_changed = Signal(str, object)
    compile_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RenderOptionsRegion")
        self.setFixedHeight(100)
        self.setStyleSheet(
            "#RenderOptionsRegion { background: #eef3fa; border-bottom: 1px solid #cdd7e3; }"
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(2)

        label = QLabel("Render Format")
        label.setStyleSheet("color: #1f5fa8; font-size: 11px; font-weight: bold;")
        outer.addWidget(label)

        bar = QHBoxLayout()
        bar.setSpacing(8)

        bar.addWidget(QLabel("Font size:"))
        self._font_size = QSpinBox()
        self._font_size.setRange(6, 36)
        self._font_size.setValue(11)
        self._font_size.setSuffix(" pt")
        self._font_size.valueChanged.connect(
            lambda v: self._emit_setting("font_size_pt", int(v))
        )
        bar.addWidget(self._font_size)

        bar.addWidget(QLabel("Page:"))
        self._page_format = QComboBox()
        self._page_format.addItems(PAGE_FORMATS)
        self._page_format.currentTextChanged.connect(
            lambda v: self._emit_setting("page_format", v)
        )
        bar.addWidget(self._page_format)

        bar.addStretch()

        self._compile_btn = QPushButton("Compile / Render")
        self._compile_btn.setStyleSheet(
            "QPushButton { background: #1f5fa8; color: white; padding: 5px 16px; "
            "border: 1px solid #174d8a; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #2a6cb8; border-color: #1f5fa8; color: white; }"
            "QPushButton:pressed { background: #174d8a; }"
        )
        self._compile_btn.clicked.connect(self.compile_requested)
        bar.addWidget(self._compile_btn)

        outer.addLayout(bar)
        outer.addStretch()

        self._suppress_settings = False

    def apply_settings(self, settings: dict[str, Any]) -> None:
        self._suppress_settings = True
        try:
            self._font_size.setValue(int(settings.get("font_size_pt", 11)))
            fmt = str(settings.get("page_format", "A4"))
            idx = self._page_format.findText(fmt)
            if idx >= 0:
                self._page_format.setCurrentIndex(idx)
        finally:
            self._suppress_settings = False

    def _emit_setting(self, name: str, value: Any) -> None:
        if self._suppress_settings:
            return
        self.setting_changed.emit(name, value)


class DraftReportPane(QWidget):
    override_changed = Signal(str, str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(360)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._content = QWidget()
        self._content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(12, 12, 12, 12)
        self._content_layout.setSpacing(10)
        self._content_layout.addStretch()
        self._scroll.setWidget(self._content)
        root.addWidget(self._scroll, stretch=1)

    def set_snapshot(
        self, graph: Graph | None, results: dict[str, dict[str, Any]] | None
    ) -> None:
        self._clear_cards()

        if graph is None or not graph.nodes:
            placeholder = QLabel(
                "Drop blocks into the graph to assemble your report preview."
            )
            placeholder.setStyleSheet("color: gray;")
            placeholder.setAlignment(Qt.AlignCenter)
            self._content_layout.insertWidget(0, placeholder)
            return

        results = results or {}
        for nid in graph.topological_order():
            block = graph.nodes[nid]
            snapshot = BlockSnapshot(
                node_id=nid,
                block=block,
                result=results.get(nid),
                overrides=graph.block_overrides.get(nid, {}),
            )
            card = _BlockCard(snapshot)
            card.override_changed.connect(self.override_changed)
            self._content_layout.insertWidget(self._content_layout.count() - 1, card)

    def _clear_cards(self) -> None:
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()


def compile_report_html(
    graph: Graph, results: dict[str, dict[str, Any]]
) -> str:
    settings = graph.render_settings or {}
    family = settings.get("font_family", "Arial, sans-serif")
    size = int(settings.get("font_size_pt", 11))

    head = (
        "<html><head><style>"
        f"body {{ font-family: {family}; font-size: {size}pt; color: #222; "
        "margin: 32px; line-height: 1.45; }}"
        "h1, h2 { border-bottom: 1px solid #ccc; padding-bottom: 4px; }"
        "table { border-collapse: collapse; margin: 8px 0; }"
        "th, td { border: 1px solid #888; padding: 6px 12px; text-align: left; }"
        "th { background: #eee; }"
        ".section { margin-bottom: 28px; }"
        ".narrative { white-space: pre-wrap; margin: 6px 0 10px 0; }"
        ".error { color: #883333; background: #fbeaea; border: 1px solid #c99; padding: 10px; }"
        "</style></head><body>"
    )

    body_parts: list[str] = []
    rendered_any = False
    for nid in graph.topological_order():
        block = graph.nodes[nid]
        result = results.get(nid)
        overrides = graph.block_overrides.get(nid, {})

        if result is not None and "_error" in result:
            body_parts.append(
                f"<div class='section'><h2>{_effective_title(block, overrides)}</h2>"
                f"<div class='error'>{result['_error']}</div></div>"
            )
            rendered_any = True
            continue

        value = _primary_output(block, result)
        snapshot = BlockSnapshot(
            node_id=nid, block=block, result=result, overrides=overrides,
        )
        narrative = _effective_narrative(snapshot).strip()
        if value is None and not narrative:
            continue

        title = _effective_title(block, overrides)
        section = [f"<div class='section'><h2>{title}</h2>"]
        if narrative:
            section.append(f"<div class='narrative'>{narrative}</div>")
        if value is not None:
            section.append(output_to_html(value, include_interpretation=False))
        section.append("</div>")
        body_parts.append("".join(section))
        rendered_any = True

    if not rendered_any:
        body_parts.append(
            "<p style='color:#888;'><em>No connected blocks have produced output yet.</em></p>"
        )

    return head + "".join(body_parts) + "</body></html>"


class CompiledReportDialog(QDialog):
    export_requested = Signal(str)

    def __init__(self, html: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Compiled Report")
        self.resize(900, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QWidget()
        toolbar.setStyleSheet("background: #eef3fa; border-bottom: 1px solid #cdd7e3;")
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(8, 6, 8, 6)
        bar.addStretch()

        export_btn = QToolButton()
        export_btn.setText("Export")
        export_btn.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(export_btn)
        for fmt in ("PDF", "HTML"):
            action = QAction(fmt, menu)
            action.triggered.connect(
                lambda _checked=False, f=fmt: self.export_requested.emit(f)
            )
            menu.addAction(action)
        export_btn.setMenu(menu)
        bar.addWidget(export_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        bar.addWidget(close_btn)

        layout.addWidget(toolbar)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(html)
        layout.addWidget(browser, stretch=1)
