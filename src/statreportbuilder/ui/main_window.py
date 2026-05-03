from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QInputDialog, QMainWindow, QStackedWidget

from src.statreportbuilder.core import storage
from src.statreportbuilder.core.storage import Project
from src.statreportbuilder.ui.home_screen import HomeScreen
from src.statreportbuilder.ui.home_screen import Project as HomeProject
from src.statreportbuilder.ui.project_view import ProjectView


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("StatReportBuilder")
        self.resize(1200, 800)

        self._stack = QStackedWidget(self)
        self.setCentralWidget(self._stack)

        self.home_screen = HomeScreen()
        self._stack.addWidget(self.home_screen)

        self._project_view: ProjectView | None = None
        self._close_project_action: QAction | None = None
        self._projects_by_name: dict[str, Project] = {}

        self._build_menu_bar()
        self._wire_signals()
        self._refresh_home()

    def _build_menu_bar(self) -> None:
        bar = self.menuBar()

        file_menu = bar.addMenu("File")
        file_menu.addAction("New Project", self._on_new_project)
        self._close_project_action = QAction("Close Project", self)
        self._close_project_action.setEnabled(False)
        self._close_project_action.triggered.connect(self.close_project)
        file_menu.addAction(self._close_project_action)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        edit_menu = bar.addMenu("Edit")
        edit_menu.addAction("Undo")
        edit_menu.addAction("Redo")

        bar.addMenu("View")
        bar.addMenu("Project")
        bar.addMenu("Tools")

        help_menu = bar.addMenu("Help")
        help_menu.addAction("About")

    def _wire_signals(self) -> None:
        self.home_screen.project_opened.connect(self._open_project_by_name)
        self.home_screen.new_project_requested.connect(self._on_new_project)
        self.home_screen.template_selected.connect(self._on_template_selected)

    def _refresh_home(self) -> None:
        projects = storage.list_projects()
        self._projects_by_name = {p.name: p for p in projects}
        self.home_screen.set_projects([HomeProject(name=p.name) for p in projects])

    def _on_new_project(self) -> None:
        name, ok = QInputDialog.getText(self, "New project", "Project name:")
        if not ok or not name.strip():
            return
        project = storage.create_project(name.strip())
        self._refresh_home()
        self._open_project(project)

    def _on_template_selected(self, template: str) -> None:
        name, ok = QInputDialog.getText(
            self, "New project", "Project name:", text=f"My {template} Project"
        )
        if not ok or not name.strip():
            return
        project = storage.create_project(name.strip(), template=template)
        self._refresh_home()
        self._open_project(project)

    def _open_project_by_name(self, name: str) -> None:
        project = self._projects_by_name.get(name)
        if project is None:
            return
        self._open_project(project)

    def _open_project(self, project: Project) -> None:
        if self._project_view is not None:
            self._stack.removeWidget(self._project_view)
            self._project_view.deleteLater()

        self._project_view = ProjectView(project)
        self._stack.addWidget(self._project_view)
        self._stack.setCurrentWidget(self._project_view)

        self.setWindowTitle(f"StatReportBuilder — {project.name}")
        if self._close_project_action is not None:
            self._close_project_action.setEnabled(True)

    def close_project(self) -> None:
        if self._project_view is None:
            return

        self._stack.setCurrentWidget(self.home_screen)
        self._stack.removeWidget(self._project_view)
        self._project_view.deleteLater()
        self._project_view = None

        self.setWindowTitle("StatReportBuilder")
        if self._close_project_action is not None:
            self._close_project_action.setEnabled(False)

        self._refresh_home()
