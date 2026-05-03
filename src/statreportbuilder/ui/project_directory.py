from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class CollapsibleSection(QWidget):
    add_clicked = Signal()

    def __init__(self, title: str, content: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        h = QHBoxLayout(header)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(4)

        self._toggle_btn = QToolButton()
        self._toggle_btn.setStyleSheet("QToolButton { border: none; font-weight: bold; }")
        self._toggle_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._toggle_btn.setArrowType(Qt.DownArrow)
        self._toggle_btn.setText(title)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)
        self._toggle_btn.clicked.connect(self._on_toggled)
        h.addWidget(self._toggle_btn)

        h.addStretch()

        self._add_btn = QToolButton()
        self._add_btn.setText("+")
        self._add_btn.setToolTip(f"Add to {title}")
        self._add_btn.clicked.connect(self.add_clicked)
        h.addWidget(self._add_btn)

        layout.addWidget(header)

        self._content = content
        layout.addWidget(content)

    def _on_toggled(self, checked: bool) -> None:
        self._toggle_btn.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self._content.setVisible(checked)

    def is_expanded(self) -> bool:
        return self._toggle_btn.isChecked()

    def set_expanded(self, expanded: bool) -> None:
        self._toggle_btn.setChecked(expanded)
        self._on_toggled(expanded)


class ProjectDirectory(QWidget):
    file_selected = Signal(str)
    file_rename_requested = Signal(str)
    file_duplicate_requested = Signal(str)
    file_delete_requested = Signal(str)
    file_create_requested = Signal()

    csv_preview_requested = Signal(str)
    csv_import_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        title = QLabel("Project")
        title.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(title)

        self._files_list = QListWidget()
        self._files_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._files_list.customContextMenuRequested.connect(self._on_files_context_menu)
        self._files_list.currentItemChanged.connect(self._on_file_changed)

        self._csv_list = QListWidget()
        self._csv_list.itemDoubleClicked.connect(self._on_csv_double_clicked)

        files_section = CollapsibleSection("Report Builder Files", self._files_list)
        files_section.add_clicked.connect(self.file_create_requested)
        layout.addWidget(files_section)

        csv_section = CollapsibleSection("Imported Data", self._csv_list)
        csv_section.add_clicked.connect(self.csv_import_requested)
        layout.addWidget(csv_section)

        layout.addStretch()

        self._files_section = files_section
        self._csv_section = csv_section

    def set_files(self, names: list[str]) -> None:
        self._files_list.blockSignals(True)
        self._files_list.clear()
        for name in names:
            self._files_list.addItem(QListWidgetItem(name))
        self._files_list.blockSignals(False)

    def set_csvs(self, names: list[str], summaries: dict[str, str] | None = None) -> None:
        self._csv_list.clear()
        summaries = summaries or {}
        for name in names:
            item = QListWidgetItem(name)
            if name in summaries and summaries[name]:
                item.setToolTip(summaries[name])
            self._csv_list.addItem(item)

    def set_active_file(self, name: str | None) -> None:
        if name is None:
            self._files_list.clearSelection()
            return
        for i in range(self._files_list.count()):
            item = self._files_list.item(i)
            if item.text() == name:
                self._files_list.setCurrentItem(item)
                return

    def _on_file_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is not None:
            self.file_selected.emit(current.text())

    def _on_files_context_menu(self, pos) -> None:
        item = self._files_list.itemAt(pos)
        if item is None:
            return

        menu = QMenu(self)
        rename = QAction("Rename", menu)
        duplicate = QAction("Duplicate", menu)
        delete = QAction("Delete", menu)

        rename.triggered.connect(lambda: self.file_rename_requested.emit(item.text()))
        duplicate.triggered.connect(lambda: self.file_duplicate_requested.emit(item.text()))
        delete.triggered.connect(lambda: self.file_delete_requested.emit(item.text()))

        menu.addAction(rename)
        menu.addAction(duplicate)
        menu.addSeparator()
        menu.addAction(delete)
        menu.exec(self._files_list.mapToGlobal(pos))

    def _on_csv_double_clicked(self, item: QListWidgetItem) -> None:
        self.csv_preview_requested.emit(item.text())
