from __future__ import annotations

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QAction, QDrag
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QToolButton,
    QWidget,
)

from src.statreportbuilder.core.blocks import BLOCK_REGISTRY


BLOCK_MIME_TYPE = "application/x-statreportbuilder-block"


PRESETS = [
    ("two_sample_ttest", "Two-Sample T-Test"),
]


class DraggableBlockButton(QToolButton):
    def __init__(self, type_id: str, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._type_id = type_id
        self.setText(label)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip(f"Drag onto canvas to add a {label} block")
        self._drag_start = None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is None or not (event.buttons() & Qt.LeftButton):
            return
        if (event.position() - self._drag_start).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(BLOCK_MIME_TYPE, self._type_id.encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)
        self._drag_start = None


class BlockPalette(QWidget):
    preset_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        label = QLabel("Blocks:")
        label.setStyleSheet("color: #555;")
        layout.addWidget(label)

        for type_id, cls in BLOCK_REGISTRY.items():
            btn = DraggableBlockButton(type_id, cls.title)
            layout.addWidget(btn)

        layout.addSpacing(16)

        preset_btn = QToolButton()
        preset_btn.setText("Presets ▾")
        preset_btn.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(preset_btn)
        for preset_id, preset_label in PRESETS:
            action = QAction(preset_label, menu)
            action.triggered.connect(
                lambda _checked=False, pid=preset_id: self.preset_requested.emit(pid)
            )
            menu.addAction(action)
        preset_btn.setMenu(menu)
        layout.addWidget(preset_btn)

        layout.addStretch()

        hint = QLabel("Drag to canvas · Drag port-to-port to connect · Del to remove")
        hint.setStyleSheet("color: #888;")
        layout.addWidget(hint)
