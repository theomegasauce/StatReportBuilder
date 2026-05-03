from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from src.statreportbuilder.core.blocks import (
    CSVLoaderBlock,
    ReportBlock,
    TwoSampleTTestBlock,
)
from src.statreportbuilder.core.graph import Edge, Graph


PROJECTS_ROOT = Path.home() / "Documents" / "StatReportBuilder" / "Projects"


@dataclass
class Project:
    name: str
    root: Path

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def manifest_path(self) -> Path:
        return self.root / "project.json"

    def csv_path(self, name: str) -> Path:
        return self.data_dir / name

    def report_path(self, name: str) -> Path:
        return self.reports_dir / name

    def list_reports(self) -> list[str]:
        if not self.reports_dir.exists():
            return []
        return sorted(p.name for p in self.reports_dir.glob("*.json"))

    def list_csvs(self) -> list[str]:
        if not self.data_dir.exists():
            return []
        return sorted(p.name for p in self.data_dir.glob("*.csv"))


def list_projects() -> list[Project]:
    if not PROJECTS_ROOT.exists():
        return []
    projects: list[Project] = []
    for entry in sorted(PROJECTS_ROOT.iterdir()):
        manifest = entry / "project.json"
        if entry.is_dir() and manifest.exists():
            try:
                data = json.loads(manifest.read_text())
                name = data.get("name", entry.name)
            except (json.JSONDecodeError, OSError):
                name = entry.name
            projects.append(Project(name=name, root=entry))
    return projects


def create_project(name: str, template: str | None = None) -> Project:
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    root = _unique_path(PROJECTS_ROOT / _slug(name))
    root.mkdir()

    project = Project(name=name, root=root)
    project.reports_dir.mkdir()
    project.data_dir.mkdir()
    project.manifest_path.write_text(
        json.dumps({"name": name, "template": template}, indent=2)
    )

    if template == "T-Test":
        create_report_file(project, "T-Test Report", _two_sample_ttest_template())
    elif template is not None:
        create_report_file(project, f"{template} Report")

    return project


def create_report_file(
    project: Project, filename: str, graph: Graph | None = None
) -> Path:
    project.reports_dir.mkdir(parents=True, exist_ok=True)
    if not filename.endswith(".json"):
        filename = f"{filename}.json"
    path = _unique_path(project.reports_dir / filename)
    if graph is None:
        graph = Graph()
    graph.save(path)
    return path


def import_csv(project: Project, source_path: Path) -> Path:
    project.data_dir.mkdir(parents=True, exist_ok=True)
    target = _unique_path(project.data_dir / source_path.name)
    shutil.copy2(source_path, target)
    return target


def rename_report_file(project: Project, old_name: str, new_name: str) -> Path:
    src = project.report_path(old_name)
    if not new_name.endswith(".json"):
        new_name = f"{new_name}.json"
    dst = _unique_path(project.reports_dir / new_name)
    src.rename(dst)
    return dst


def duplicate_report_file(project: Project, name: str) -> Path:
    src = project.report_path(name)
    dst = _unique_path(project.reports_dir / src.name)
    shutil.copy2(src, dst)
    return dst


def delete_report_file(project: Project, name: str) -> None:
    path = project.report_path(name)
    if path.exists():
        path.unlink()


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, ext = path.stem, path.suffix
    parent = path.parent
    i = 2
    while True:
        candidate = parent / f"{stem} ({i}){ext}"
        if not candidate.exists():
            return candidate
        i += 1


def _slug(name: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip()
    return cleaned or "Project"


def _two_sample_ttest_template() -> Graph:
    g = Graph()
    g.nodes["loader"] = CSVLoaderBlock("loader")
    g.nodes["ttest"] = TwoSampleTTestBlock("ttest")
    g.nodes["report"] = ReportBlock("report")
    g.edges.append(Edge("loader", "dataframe", "ttest", "dataframe"))
    g.edges.append(Edge("ttest", "result", "report", "result"))
    g.positions = {
        "loader": (-300.0, -40.0),
        "ttest": (-20.0, -40.0),
        "report": (260.0, -40.0),
    }
    return g
