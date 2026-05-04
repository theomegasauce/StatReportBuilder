from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.statreportbuilder.core import storage
from src.statreportbuilder.core.blocks import BLOCK_REGISTRY
from src.statreportbuilder.core.graph import Edge, Graph
from src.statreportbuilder.core.pdf_export import export_html_to_pdf
from src.statreportbuilder.core.storage import Project
from src.statreportbuilder.ui.block_edit_pane import BlockEditContext, BlockEditPane
from src.statreportbuilder.ui.block_region import BlockRegion
from src.statreportbuilder.ui.csv_preview import CSVPreviewDialog, csv_summary
from src.statreportbuilder.ui.draft_report import (
    CompiledReportDialog,
    DraftReportPane,
    RenderOptionsRegion,
    compile_report_html,
)
from src.statreportbuilder.ui.node_graph import BLOCK_HEIGHT, BLOCK_WIDTH, NodeGraphBuilder
from src.statreportbuilder.ui.project_directory import ProjectDirectory


PRESET_GRAPHS: dict[str, list[tuple[str, str]]] = {
    "two_mean_ttest_full": [
        ("csv_loader", "loader"),
        ("dataset_variable_table", "variables"),
        ("dataset_numerical_stats", "numstats"),
        ("normality_test", "normality"),
        ("qq_plot", "qq"),
        ("variance_test", "variance"),
        ("two_mean_ttest", "ttest"),
        ("confidence_interval", "ci"),
        ("boxplot", "box"),
        ("ci_plot", "ciplot"),
        ("action_impact", "action"),
    ],
}

PRESET_EDGES: dict[str, list[tuple[int, str, int, str]]] = {
    "two_mean_ttest_full": [
        (0, "dataframe", 1, "dataframe"),
        (0, "dataframe", 2, "dataframe"),
        (0, "dataframe", 3, "dataframe"),
        (0, "dataframe", 4, "dataframe"),
        (0, "dataframe", 5, "dataframe"),
        (0, "dataframe", 6, "dataframe"),
        (0, "dataframe", 7, "dataframe"),
        (0, "dataframe", 8, "dataframe"),
        (0, "dataframe", 9, "dataframe"),
    ],
}

PRESET_LAYOUT: dict[str, dict[str, tuple[float, float]]] = {
    "two_mean_ttest_full": {
        "loader": (0, 0),
        "variables": (1, -2),
        "numstats": (1, -1),
        "normality": (1, 0),
        "qq": (1, 1),
        "variance": (1, 2),
        "ttest": (2, -1),
        "ci": (2, 0),
        "box": (2, 1),
        "ciplot": (2, 2),
        "action": (3, 0),
    },
}


def _next_node_id(graph: Graph, type_id: str) -> str:
    if type_id not in graph.nodes:
        return type_id
    n = 2
    while f"{type_id}_{n}" in graph.nodes:
        n += 1
    return f"{type_id}_{n}"


class ProjectView(QWidget):
    closed = Signal()

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = project
        self._graph: Graph | None = None
        self._graph_path: Path | None = None
        self._results: dict[str, dict[str, Any]] = {}
        self._compiled_html: str | None = None
        self._selected_node: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.block_region = BlockRegion()
        self.render_options = RenderOptionsRegion()
        self.directory = ProjectDirectory()
        self.block_edit = BlockEditPane()
        self.graph_builder = NodeGraphBuilder()
        self.draft_pane = DraftReportPane()

        self._left_splitter = QSplitter(Qt.Vertical)
        self._left_splitter.setChildrenCollapsible(False)
        self._left_splitter.addWidget(self.directory)
        self._left_splitter.addWidget(self.block_edit)
        self._left_splitter.setStretchFactor(0, 2)
        self._left_splitter.setStretchFactor(1, 1)
        self._left_splitter.setSizes([460, 240])
        self.block_edit.hide()

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self._left_splitter)
        self._splitter.addWidget(self.graph_builder)
        self._splitter.addWidget(self.draft_pane)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 3)
        self._splitter.setStretchFactor(2, 2)
        self._splitter.setSizes([240, 760, 500])

        self._top_splitter = QSplitter(Qt.Horizontal)
        self._top_splitter.setChildrenCollapsible(False)
        self._top_splitter.setHandleWidth(0)

        self._block_region_host = QWidget()
        block_host_layout = QVBoxLayout(self._block_region_host)
        block_host_layout.setContentsMargins(0, 0, 0, 0)
        block_host_layout.setSpacing(0)
        block_host_layout.addWidget(self.block_region)

        self._top_splitter.addWidget(self._block_region_host)
        self._top_splitter.addWidget(self.render_options)
        self._top_splitter.setSizes([1000, 500])

        for handle_idx in range(1, self._top_splitter.count()):
            handle = self._top_splitter.handle(handle_idx)
            if handle is not None:
                handle.setEnabled(False)

        self._splitter.splitterMoved.connect(self._sync_top_splitter)

        layout.addWidget(self._top_splitter)
        layout.addWidget(self._splitter, stretch=1)

        self._wire_signals()
        self._refresh_directory()
        self._auto_open_first_report()

    def _wire_signals(self) -> None:
        self.directory.file_selected.connect(self._on_file_selected)
        self.directory.file_create_requested.connect(self._on_create_report)
        self.directory.file_rename_requested.connect(self._on_rename_report)
        self.directory.file_duplicate_requested.connect(self._on_duplicate_report)
        self.directory.file_delete_requested.connect(self._on_delete_report)

        self.directory.csv_import_requested.connect(self._on_import_csv)
        self.directory.csv_preview_requested.connect(self._on_preview_csv)

        self.graph_builder.node_selected.connect(self._on_node_selected)
        self.graph_builder.block_dropped.connect(self._on_block_dropped)
        self.graph_builder.edge_requested.connect(self._on_edge_requested)
        self.graph_builder.delete_requested.connect(self._on_delete_requested)
        self.block_region.preset_requested.connect(self._on_preset_requested)

        self.block_edit.parameter_changed.connect(self._on_parameter_changed)
        self.block_edit.close_requested.connect(self._close_block_edit)

        self.draft_pane.override_changed.connect(self._on_override_changed)
        self.render_options.setting_changed.connect(self._on_setting_changed)
        self.render_options.compile_requested.connect(self._on_compile_requested)

    @property
    def project(self) -> Project:
        return self._project

    def _refresh_directory(self) -> None:
        self.directory.set_files(self._project.list_reports())
        csvs = self._project.list_csvs()
        summaries = {name: csv_summary(self._project.csv_path(name)) for name in csvs}
        self.directory.set_csvs(csvs, summaries)

    def _auto_open_first_report(self) -> None:
        reports = self._project.list_reports()
        if reports:
            self.directory.set_active_file(reports[0])
        else:
            self.graph_builder.set_graph(None)
            self.draft_pane.set_snapshot(None, None)

    def _on_file_selected(self, name: str) -> None:
        path = self._project.report_path(name)
        if not path.exists():
            return
        try:
            graph = Graph.load(path)
        except Exception as exc:
            QMessageBox.critical(self, "Load failed", f"Could not load report:\n{exc}")
            return
        self._graph = graph
        self._graph_path = path
        self._selected_node = None
        self._compiled_html = None
        self.graph_builder.set_graph(graph)
        self._execute()
        self._refresh_draft()
        self._show_selected_block()

    def _execute(self) -> None:
        if self._graph is None:
            self._results = {}
            return
        self._results = self._graph.execute({"project": self._project})

    def _refresh_draft(self) -> None:
        settings = (self._graph.render_settings if self._graph else {}) or {}
        self.render_options.apply_settings(settings)
        self.draft_pane.set_snapshot(self._graph, self._results)

    def _sync_top_splitter(self, *_args: Any) -> None:
        sizes = self._splitter.sizes()
        if len(sizes) < 3:
            return
        left = sizes[0] + sizes[1]
        right = sizes[2]
        self._top_splitter.setSizes([left, right])

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_top_splitter()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_top_splitter()

    def _selected_block_context(self) -> BlockEditContext | None:
        if self._graph is None or self._selected_node is None:
            return None
        block = self._graph.nodes.get(self._selected_node)
        if block is None:
            return None
        return BlockEditContext(
            block=block,
            columns_by_input=self._columns_for(self._selected_node),
            csv_choices=self._project.list_csvs(),
        )

    def _show_selected_block(self) -> None:
        ctx = self._selected_block_context()
        self.block_edit.show_block(ctx)
        if ctx is not None:
            if not self.block_edit.isVisible():
                self.block_edit.show()
                self._left_splitter.setSizes([460, 240])

    def _close_block_edit(self) -> None:
        self.block_edit.hide()

    def _columns_for(self, node_id: str) -> dict[str, list[str]]:
        if self._graph is None:
            return {}
        result: dict[str, list[str]] = {}
        for edge in self._graph.in_edges(node_id):
            src_outputs = self._results.get(edge.src_node) or {}
            value = src_outputs.get(edge.src_port)
            if isinstance(value, pd.DataFrame):
                result[edge.dst_port] = list(value.columns)
        return result

    def _on_node_selected(self, node_id: object) -> None:
        self._selected_node = node_id if isinstance(node_id, str) else None
        self._show_selected_block()

    def _on_parameter_changed(self, node_id: str, _name: str, _value: object) -> None:
        if self._graph is None or self._graph_path is None:
            return
        self._graph.positions = self.graph_builder.collect_positions()
        self._graph.save(self._graph_path)
        self._execute()
        self._refresh_draft()
        self.graph_builder.refresh_block(node_id)

    def _on_setting_changed(self, name: str, value: Any) -> None:
        if self._graph is None or self._graph_path is None:
            return
        self._graph.render_settings[name] = value
        self._graph.save(self._graph_path)

    def _on_override_changed(self, node_id: str, key: str, value: str) -> None:
        if self._graph is None or self._graph_path is None:
            return
        overrides = self._graph.block_overrides.setdefault(node_id, {})
        if value:
            overrides[key] = value
        else:
            overrides.pop(key, None)
            if not overrides:
                self._graph.block_overrides.pop(node_id, None)
        self._graph.save(self._graph_path)

    def _on_compile_requested(self) -> None:
        if self._graph is None:
            QMessageBox.information(self, "No report open", "Open a report first.")
            return
        try:
            self._execute()
        except Exception as exc:
            QMessageBox.critical(self, "Compile failed", str(exc))
            return

        html = compile_report_html(self._graph, self._results)
        self._compiled_html = html
        dlg = CompiledReportDialog(html, self)
        dlg.export_requested.connect(self._on_export)
        dlg.exec()

    def _on_block_dropped(self, type_id: str, scene_pos) -> None:
        if not self._require_active_graph():
            return
        block_cls = BLOCK_REGISTRY.get(type_id)
        if block_cls is None:
            return
        new_id = _next_node_id(self._graph, type_id)
        self._graph.nodes[new_id] = block_cls(new_id)
        self._graph.positions = self.graph_builder.collect_positions()
        self._graph.positions[new_id] = (
            scene_pos.x() - BLOCK_WIDTH / 2,
            scene_pos.y() - BLOCK_HEIGHT / 2,
        )
        self._save_and_refresh(select_node=new_id)

    def _on_preset_requested(self, preset_id: str) -> None:
        if not self._require_active_graph():
            return
        block_specs = PRESET_GRAPHS.get(preset_id)
        edge_specs = PRESET_EDGES.get(preset_id, [])
        layout = PRESET_LAYOUT.get(preset_id, {})
        if not block_specs:
            return

        self._graph.positions = self.graph_builder.collect_positions()
        center = self.graph_builder.viewport_center_in_scene()
        col_spacing = BLOCK_WIDTH + 80
        row_spacing = BLOCK_HEIGHT + 40

        new_ids: list[str] = []
        for index, (type_id, hint) in enumerate(block_specs):
            block_cls = BLOCK_REGISTRY.get(type_id)
            if block_cls is None:
                continue
            new_id = _next_node_id(self._graph, type_id)
            self._graph.nodes[new_id] = block_cls(new_id)
            col, row = layout.get(hint, (index, 0))
            self._graph.positions[new_id] = (
                center.x() + col * col_spacing - BLOCK_WIDTH / 2,
                center.y() + row * row_spacing - BLOCK_HEIGHT / 2,
            )
            new_ids.append(new_id)

        for src_idx, src_port, dst_idx, dst_port in edge_specs:
            if src_idx >= len(new_ids) or dst_idx >= len(new_ids):
                continue
            self._graph.edges.append(
                Edge(new_ids[src_idx], src_port, new_ids[dst_idx], dst_port)
            )

        self._save_and_refresh()

    def _on_edge_requested(
        self, src_node: str, src_port: str, dst_node: str, dst_port: str
    ) -> None:
        if not self._require_active_graph():
            return
        if src_node == dst_node:
            return

        src_block = self._graph.nodes.get(src_node)
        dst_block = self._graph.nodes.get(dst_node)
        if src_block is None or dst_block is None:
            return

        src_kind = next(
            (p.kind for p in src_block.outputs if p.name == src_port), None
        )
        dst_kind = next(
            (p.kind for p in dst_block.inputs if p.name == dst_port), None
        )
        if src_kind is None or dst_kind is None or src_kind != dst_kind:
            QMessageBox.information(
                self,
                "Incompatible ports",
                f"Cannot connect {src_kind or '?'} → {dst_kind or '?'}.",
            )
            return

        if self._would_cycle(src_node, dst_node):
            QMessageBox.information(self, "Cycle blocked", "That connection would create a cycle.")
            return

        self._graph.edges = [
            e for e in self._graph.edges
            if not (e.dst_node == dst_node and e.dst_port == dst_port)
        ]
        self._graph.edges.append(Edge(src_node, src_port, dst_node, dst_port))
        self._graph.positions = self.graph_builder.collect_positions()
        self._save_and_refresh()

    def _on_delete_requested(
        self, node_ids: list, edge_keys: list
    ) -> None:
        if not self._require_active_graph():
            return
        if not node_ids and not edge_keys:
            return

        for nid in node_ids:
            self._graph.nodes.pop(nid, None)
            self._graph.positions.pop(nid, None)
            self._graph.block_overrides.pop(nid, None)

        edge_key_set = {tuple(k) for k in edge_keys}
        self._graph.edges = [
            e for e in self._graph.edges
            if e.src_node not in node_ids
            and e.dst_node not in node_ids
            and (e.src_node, e.src_port, e.dst_node, e.dst_port) not in edge_key_set
        ]

        if self._selected_node in node_ids:
            self._selected_node = None

        self._graph.positions = {
            nid: pos for nid, pos in self._graph.positions.items()
            if nid in self._graph.nodes
        }
        positions_from_canvas = self.graph_builder.collect_positions()
        for nid, pos in positions_from_canvas.items():
            if nid in self._graph.nodes:
                self._graph.positions[nid] = pos

        self._save_and_refresh()

    def _require_active_graph(self) -> bool:
        if self._graph is None or self._graph_path is None:
            QMessageBox.information(
                self,
                "No report open",
                "Open or create a report file before editing the graph.",
            )
            return False
        return True

    def _save_and_refresh(self, select_node: str | None = None) -> None:
        assert self._graph is not None and self._graph_path is not None
        self._graph.save(self._graph_path)
        self.graph_builder.set_graph(self._graph)
        if select_node is not None:
            self._selected_node = select_node
            self.graph_builder.select_node(select_node)
        self._refresh_draft()
        self._show_selected_block()

    def _would_cycle(self, src_node: str, dst_node: str) -> bool:
        if self._graph is None:
            return False
        adjacency: dict[str, list[str]] = {nid: [] for nid in self._graph.nodes}
        for edge in self._graph.edges:
            adjacency.setdefault(edge.src_node, []).append(edge.dst_node)
        adjacency.setdefault(src_node, []).append(dst_node)

        stack = [dst_node]
        seen = {dst_node}
        while stack:
            current = stack.pop()
            if current == src_node:
                return True
            for neighbor in adjacency.get(current, []):
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        return False

    def _on_create_report(self) -> None:
        name, ok = QInputDialog.getText(self, "New report file", "Filename:")
        if not ok or not name.strip():
            return
        storage.create_report_file(self._project, name.strip())
        self._refresh_directory()

    def _on_rename_report(self, current_name: str) -> None:
        new_name, ok = QInputDialog.getText(
            self, "Rename report", "New name:", text=current_name.removesuffix(".json")
        )
        if not ok or not new_name.strip():
            return
        new_path = storage.rename_report_file(self._project, current_name, new_name.strip())
        self._refresh_directory()
        if self._graph_path is not None and self._graph_path.name == current_name:
            self._graph_path = new_path
            self.directory.set_active_file(new_path.name)

    def _on_duplicate_report(self, name: str) -> None:
        storage.duplicate_report_file(self._project, name)
        self._refresh_directory()

    def _on_delete_report(self, name: str) -> None:
        confirm = QMessageBox.question(
            self, "Delete report", f"Delete '{name}'? This cannot be undone."
        )
        if confirm != QMessageBox.Yes:
            return
        storage.delete_report_file(self._project, name)
        if self._graph_path is not None and self._graph_path.name == name:
            self._graph = None
            self._graph_path = None
            self._compiled_html = None
            self.graph_builder.set_graph(None)
            self.draft_pane.set_graph(None)
            self.block_edit.show_block(None)
            self.block_edit.hide()
        self._refresh_directory()

    def _on_import_csv(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import CSV", "", "CSV files (*.csv);;All files (*)"
        )
        if not paths:
            return
        for p in paths:
            try:
                storage.import_csv(self._project, Path(p))
            except Exception as exc:
                QMessageBox.warning(self, "Import failed", f"{Path(p).name}:\n{exc}")
        self._refresh_directory()
        if self._graph is not None:
            self._refresh_draft()
            self._show_selected_block()

    def _on_preview_csv(self, name: str) -> None:
        path = self._project.csv_path(name)
        if not path.exists():
            return
        dlg = CSVPreviewDialog(path, self)
        dlg.exec()

    def _on_export(self, fmt: str) -> None:
        html = self._compiled_html
        if not html:
            QMessageBox.information(
                self, "Nothing to export",
                "Press Compile / Render before exporting.",
            )
            return

        if fmt == "PDF":
            path, _ = QFileDialog.getSaveFileName(
                self, "Export PDF", f"{self._project.name}.pdf", "PDF files (*.pdf)"
            )
            if not path:
                return
            try:
                export_html_to_pdf(html, Path(path))
            except Exception as exc:
                QMessageBox.critical(self, "Export failed", str(exc))
                return
            QMessageBox.information(self, "Export complete", f"Saved to:\n{path}")
            return

        if fmt == "HTML":
            path, _ = QFileDialog.getSaveFileName(
                self, "Export HTML", f"{self._project.name}.html", "HTML files (*.html)"
            )
            if not path:
                return
            Path(path).write_text(html, encoding="utf-8")
            QMessageBox.information(self, "Export complete", f"Saved to:\n{path}")
            return

        QMessageBox.information(self, "Not implemented", f"{fmt} export is not implemented yet.")
