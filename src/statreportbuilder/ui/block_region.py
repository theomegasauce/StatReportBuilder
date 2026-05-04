from __future__ import annotations

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.statreportbuilder.core.blocks import BLOCK_REGISTRY


BLOCK_MIME_TYPE = "application/x-statreportbuilder-block"


PRESETS = [
    ("two_sample_ttest", "Two-Mean T-Test", "CSV → T-Test → Report"),
]


class DraggableBlockCard(QFrame):
    def __init__(
        self, type_id: str, title: str, subtitle: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._type_id = type_id
        self._drag_start = None

        self.setObjectName("DraggableBlockCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedSize(160, 56)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip(f"Drag onto canvas to add a {title} block")
        self.setStyleSheet(
            "#DraggableBlockCard { background: #ffffff; border: 1px solid #c8c8c8; border-radius: 6px; }"
            "#DraggableBlockCard:hover { background: #f0f6ff; border-color: #4a90e2; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(0)

        title_label = QLabel(title)
        font = title_label.font()
        font.setBold(True)
        title_label.setFont(font)
        layout.addWidget(title_label)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet("color: #777; font-size: 10px;")
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


class PresetCard(QToolButton):
    def __init__(
        self, preset_id: str, title: str, subtitle: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._preset_id = preset_id
        self.setFixedSize(180, 56)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.setStyleSheet(
            "QToolButton { background: #fff7ec; border: 1px solid #d8b87a; "
            "border-radius: 6px; padding: 6px 10px; text-align: left; }"
            "QToolButton:hover { background: #fdecc8; border-color: #b88a30; }"
        )
        text = title if not subtitle else f"{title}\n{subtitle}"
        self.setText(text)
        self.setToolTip(f"Click to insert the {title} preset")

    @property
    def preset_id(self) -> str:
        return self._preset_id


class BlockRegion(QWidget):
    preset_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BlockRegion")
        self.setFixedHeight(100)
        self.setStyleSheet(
            "#BlockRegion { background: #f3f4f6; border-bottom: 1px solid #d4d6da; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        basic_cards: list[QWidget] = [
            DraggableBlockCard(type_id, cls.title) for type_id, cls in BLOCK_REGISTRY.items()
        ]
        layout.addWidget(self._build_section("Basic Blocks", basic_cards), stretch=7)

        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setFrameShadow(QFrame.Sunken)
        layout.addWidget(divider)

        preset_cards: list[QWidget] = []
        for preset_id, title, subtitle in PRESETS:
            card = PresetCard(preset_id, title, subtitle)
            card.clicked.connect(
                lambda _checked=False, pid=preset_id: self.preset_requested.emit(pid)
            )
            preset_cards.append(card)
        layout.addWidget(self._build_section("Presets", preset_cards), stretch=3)

    @staticmethod
    def _build_section(title: str, cards: list[QWidget]) -> QWidget:
        section = QWidget()
        s_layout = QVBoxLayout(section)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(2)

        label = QLabel(title)
        label.setStyleSheet("color: #555; font-size: 11px; font-weight: bold;")
        s_layout.addWidget(label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setFixedHeight(64)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        host = QWidget()
        host.setStyleSheet("background: transparent;")
        h_layout = QHBoxLayout(host)
        h_layout.setContentsMargins(2, 2, 2, 2)
        h_layout.setSpacing(8)
        for w in cards:
            h_layout.addWidget(w)
        h_layout.addStretch()
        scroll.setWidget(host)

        s_layout.addWidget(scroll, stretch=1)
        return section
