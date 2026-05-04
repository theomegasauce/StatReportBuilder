from __future__ import annotations

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.statreportbuilder.core.blocks import (
    BLOCK_REGISTRY,
    CATEGORY_HYPOTHESIS,
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    PALETTE_BLOCK_TYPE_IDS,
)
from src.statreportbuilder.ui.theme import (
    BG_REGION,
    BORDER,
    PRIMARY,
    TEXT_MUTED,
    category_color,
)


BLOCK_MIME_TYPE = "application/x-statreportbuilder-block"

PRESETS_BY_CATEGORY: dict[str, list[tuple[str, str, str]]] = {
    CATEGORY_HYPOTHESIS: [
        ("two_mean_ttest_full", "Two-Mean T-Test (full)",
         "Loader → examine, validity, t-test, CI, plots, action"),
    ],
}


class DraggableBlockCard(QFrame):
    def __init__(
        self,
        type_id: str,
        title: str,
        subtitle: str = "",
        category: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._type_id = type_id
        self._drag_start = None

        bg = category_color(category, "bg") if category else "#ffffff"
        bg_hover = category_color(category, "bg_hover") if category else "#f0f6ff"
        border = category_color(category, "border") if category else "#c8c8c8"
        accent = category_color(category, "accent") if category else PRIMARY

        self.setObjectName("DraggableBlockCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedSize(170, 56)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip(f"Drag onto canvas to add a {title} block")
        self.setStyleSheet(
            f"#DraggableBlockCard {{ background: {bg}; border: 1px solid {border}; "
            f"border-left: 4px solid {accent}; border-radius: 6px; }}"
            f"#DraggableBlockCard:hover {{ background: {bg_hover}; border-color: {accent}; "
            f"border-left: 4px solid {accent}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(0)

        title_label = QLabel(title)
        font = title_label.font()
        font.setBold(True)
        title_label.setFont(font)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"color: {accent}; background: transparent;")
        layout.addWidget(title_label)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; background: transparent;")
            layout.addWidget(sub)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is None or not (event.buttons() & Qt.LeftButton):
            return
        if (
            event.position() - self._drag_start
        ).manhattanLength() < QApplication.startDragDistance():
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(BLOCK_MIME_TYPE, self._type_id.encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)
        self._drag_start = None


class PresetCard(QFrame):
    clicked = Signal(str)

    def __init__(
        self,
        preset_id: str,
        title: str,
        subtitle: str = "",
        category: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._preset_id = preset_id
        self.setFixedSize(220, 56)
        self.setCursor(Qt.PointingHandCursor)

        bg = category_color(category, "bg") if category else "#e6f1fb"
        bg_hover = category_color(category, "bg_hover") if category else "#d4e7f7"
        border = category_color(category, "border") if category else "#7fb1de"
        accent = category_color(category, "accent") if category else PRIMARY

        self.setObjectName("PresetCard")
        self.setStyleSheet(
            f"#PresetCard {{ background: {bg}; border: 1px solid {border}; "
            f"border-left: 4px solid {accent}; border-radius: 6px; }}"
            f"#PresetCard:hover {{ background: {bg_hover}; border-color: {accent}; "
            f"border-left: 4px solid {accent}; }}"
        )
        self.setToolTip(f"Click to insert the {title} preset")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(0)

        title_label = QLabel("★  " + title)
        font = title_label.font()
        font.setBold(True)
        title_label.setFont(font)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"color: {accent}; background: transparent;")
        layout.addWidget(title_label)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; background: transparent;")
            sub.setWordWrap(True)
            layout.addWidget(sub)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._preset_id)
            event.accept()
            return
        super().mousePressEvent(event)


class _CategoryRow(QWidget):
    def __init__(self, cards: list[QWidget], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        host = QWidget()
        host.setStyleSheet("background: transparent;")
        h_layout = QHBoxLayout(host)
        h_layout.setContentsMargins(2, 2, 2, 2)
        h_layout.setSpacing(8)
        if cards:
            for w in cards:
                h_layout.addWidget(w)
        else:
            placeholder = QLabel("(no blocks in this category yet)")
            placeholder.setStyleSheet("color: #888; font-style: italic; padding: 4px;")
            h_layout.addWidget(placeholder)
        h_layout.addStretch()
        scroll.setWidget(host)

        layout.addWidget(scroll, stretch=1)


class BlockRegion(QWidget):
    preset_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BlockRegion")
        self.setFixedHeight(120)
        self.setStyleSheet(
            f"#BlockRegion {{ background: {BG_REGION}; border-bottom: 1px solid {BORDER}; }}"
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 6, 12, 6)
        outer.setSpacing(4)

        tab_bar = QHBoxLayout()
        tab_bar.setContentsMargins(0, 0, 0, 0)
        tab_bar.setSpacing(4)

        self._stack = QStackedWidget()
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)

        for index, category in enumerate(CATEGORY_ORDER):
            accent = category_color(category, "accent")
            bg = category_color(category, "bg")
            btn = QPushButton(CATEGORY_LABELS[category])
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { background: transparent; border: 1px solid transparent; "
                f"padding: 4px 12px; border-radius: 4px; color: {TEXT_MUTED}; font-weight: bold; "
                f"border-bottom: 3px solid transparent; }}"
                f"QPushButton:hover {{ background: {bg}; color: {accent}; }}"
                f"QPushButton:checked {{ background: #ffffff; color: {accent}; "
                f"border-bottom: 3px solid {accent}; }}"
            )
            self._tab_group.addButton(btn, index)
            tab_bar.addWidget(btn)
            self._stack.addWidget(self._build_category_page(category))

        tab_bar.addStretch()
        outer.addLayout(tab_bar)
        outer.addWidget(self._stack, stretch=1)

        self._tab_group.idClicked.connect(self._stack.setCurrentIndex)
        first_btn = self._tab_group.button(0)
        if first_btn is not None:
            first_btn.setChecked(True)

    def _build_category_page(self, category: str) -> QWidget:
        cards: list[QWidget] = []

        for preset_id, title, subtitle in PRESETS_BY_CATEGORY.get(category, []):
            card = PresetCard(preset_id, title, subtitle, category=category)
            card.clicked.connect(self.preset_requested)
            cards.append(card)

        for type_id in PALETTE_BLOCK_TYPE_IDS.get(category, []):
            cls = BLOCK_REGISTRY.get(type_id)
            if cls is None:
                continue
            cards.append(DraggableBlockCard(type_id, cls.title, category=category))

        return _CategoryRow(cards)
