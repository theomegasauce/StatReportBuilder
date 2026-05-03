from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


@dataclass
class Project:
    name: str


@dataclass
class Template:
    name: str
    description: str = ""


class TemplateCard(QPushButton):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        text = title if not subtitle else f"{title}\n\n{subtitle}"
        super().__init__(text, parent)
        self.setFixedSize(180, 110)
        self.setCursor(Qt.PointingHandCursor)


class ProjectCard(QWidget):
    clicked = Signal(str)

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = project
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        icon = QLabel()
        icon.setFixedSize(96, 96)
        icon.setStyleSheet(
            "background-color: #d8d8d8; border: 1px solid #b8b8b8; border-radius: 6px;"
        )
        layout.addWidget(icon, alignment=Qt.AlignHCenter)

        name = QLabel(project.name)
        name.setAlignment(Qt.AlignCenter)
        name.setFixedWidth(120)
        name.setWordWrap(True)
        layout.addWidget(name, alignment=Qt.AlignHCenter)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._project.name)
        super().mousePressEvent(event)


class HomeScreen(QWidget):
    new_project_requested = Signal()
    template_selected = Signal(str)
    project_opened = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._grid: QGridLayout | None = None
        self._build()
        self.set_projects([])

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_section())

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        root.addWidget(separator)

        root.addWidget(self._build_bottom_section(), stretch=1)

    def _build_top_section(self) -> QWidget:
        section = QWidget()
        section.setFixedHeight(190)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(10)

        header = QLabel("Start a new project")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        row = QHBoxLayout()
        row.setSpacing(12)

        new_btn = TemplateCard("+ New Project", "Blank project")
        new_btn.clicked.connect(self.new_project_requested)
        row.addWidget(new_btn)

        for template in self._default_templates():
            card = TemplateCard(template.name, template.description)
            card.clicked.connect(
                lambda _checked=False, name=template.name: self.template_selected.emit(name)
            )
            row.addWidget(card)

        row.addStretch()
        layout.addLayout(row)
        return section

    def _build_bottom_section(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(10)

        header = QLabel("Your projects")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        host = QWidget()
        self._grid = QGridLayout(host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(20)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll.setWidget(host)
        layout.addWidget(scroll, stretch=1)
        return section

    def set_projects(self, projects: list[Project]) -> None:
        assert self._grid is not None

        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not projects:
            empty = QLabel("No projects yet. Create one above to get started.")
            empty.setStyleSheet("color: gray;")
            self._grid.addWidget(empty, 0, 0)
            return

        columns = 5
        for index, project in enumerate(projects):
            card = ProjectCard(project)
            card.clicked.connect(self.project_opened)
            self._grid.addWidget(card, index // columns, index % columns)

    @staticmethod
    def _default_templates() -> list[Template]:
        return [
            Template("T-Test", "Compare two means"),
            Template("ANOVA", "Compare 3+ groups"),
            Template("Regression", "Linear / logistic models"),
        ]
