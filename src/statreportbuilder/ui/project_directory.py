from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


SECTION_REPORTS = "section_reports"
SECTION_CSVS = "section_csvs"


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
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 0)
        title = QLabel("Project")
        title.setStyleSheet("font-weight: bold; padding: 4px; color: #1f5fa8; font-size: 13px;")
        header.addWidget(title)
        header.addStretch()

        add_btn = QToolButton()
        add_btn.setText("+")
        add_btn.setToolTip("Add to project")
        add_btn.setPopupMode(QToolButton.InstantPopup)
        add_menu = QMenu(add_btn)
        new_report_action = QAction("New Report Builder File", add_menu)
        new_report_action.triggered.connect(self.file_create_requested)
        import_csv_action = QAction("Import CSV…", add_menu)
        import_csv_action.triggered.connect(self.csv_import_requested)
        add_menu.addAction(new_report_action)
        add_menu.addAction(import_csv_action)
        add_btn.setMenu(add_menu)
        header.addWidget(add_btn)
        layout.addLayout(header)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(14)
        self._tree.setAnimated(True)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.currentItemChanged.connect(self._on_current_changed)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._tree, stretch=1)

        bold = self._tree.font()
        bold.setBold(True)

        self._reports_root = QTreeWidgetItem(["Report Builder Files"])
        self._reports_root.setFont(0, bold)
        self._reports_root.setData(0, Qt.UserRole, SECTION_REPORTS)
        self._tree.addTopLevelItem(self._reports_root)
        self._reports_root.setExpanded(True)

        self._csvs_root = QTreeWidgetItem(["Imported Data"])
        self._csvs_root.setFont(0, bold)
        self._csvs_root.setData(0, Qt.UserRole, SECTION_CSVS)
        self._tree.addTopLevelItem(self._csvs_root)
        self._csvs_root.setExpanded(True)

    def set_files(self, names: list[str]) -> None:
        self._tree.blockSignals(True)
        self._reports_root.takeChildren()
        for name in names:
            child = QTreeWidgetItem([name])
            child.setData(0, Qt.UserRole, ("report", name))
            self._reports_root.addChild(child)
        self._tree.blockSignals(False)

    def set_csvs(self, names: list[str], summaries: dict[str, str] | None = None) -> None:
        self._csvs_root.takeChildren()
        summaries = summaries or {}
        for name in names:
            child = QTreeWidgetItem([name])
            child.setData(0, Qt.UserRole, ("csv", name))
            if summaries.get(name):
                child.setToolTip(0, summaries[name])
            self._csvs_root.addChild(child)

    def set_active_file(self, name: str | None) -> None:
        if name is None:
            self._tree.clearSelection()
            self._tree.setCurrentItem(None)
            return
        for i in range(self._reports_root.childCount()):
            child = self._reports_root.child(i)
            if child.text(0) == name:
                self._tree.setCurrentItem(child)
                return

    def _on_current_changed(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        if current is None:
            return
        data = current.data(0, Qt.UserRole)
        if isinstance(data, tuple) and data[0] == "report":
            self.file_selected.emit(data[1])

    def _on_item_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        data = item.data(0, Qt.UserRole)
        if isinstance(data, tuple) and data[0] == "csv":
            self.csv_preview_requested.emit(data[1])

    def _on_context_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        if item is None:
            return

        data = item.data(0, Qt.UserRole)
        menu = QMenu(self)

        if data == SECTION_REPORTS:
            action = QAction("New Report Builder File", menu)
            action.triggered.connect(self.file_create_requested)
            menu.addAction(action)
        elif data == SECTION_CSVS:
            action = QAction("Import CSV…", menu)
            action.triggered.connect(self.csv_import_requested)
            menu.addAction(action)
        elif isinstance(data, tuple) and data[0] == "report":
            name = data[1]
            rename = QAction("Rename", menu)
            duplicate = QAction("Duplicate", menu)
            delete = QAction("Delete", menu)
            rename.triggered.connect(lambda _=False, n=name: self.file_rename_requested.emit(n))
            duplicate.triggered.connect(lambda _=False, n=name: self.file_duplicate_requested.emit(n))
            delete.triggered.connect(lambda _=False, n=name: self.file_delete_requested.emit(n))
            menu.addAction(rename)
            menu.addAction(duplicate)
            menu.addSeparator()
            menu.addAction(delete)
        elif isinstance(data, tuple) and data[0] == "csv":
            name = data[1]
            preview = QAction("Preview", menu)
            preview.triggered.connect(lambda _=False, n=name: self.csv_preview_requested.emit(n))
            menu.addAction(preview)

        if menu.actions():
            menu.exec(self._tree.mapToGlobal(pos))
