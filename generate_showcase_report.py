#!/usr/bin/env python3
"""Standalone showcase report generator for StatReportBuilder."""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

# Must set offscreen platform BEFORE importing any PySide6 modules
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication(sys.argv)

# Now safe to import UI modules
from src.statreportbuilder.core.blocks import (
    ActionImpactBlock,
    BoxplotBlock,
    ConfidenceIntervalBlock,
    ConfidenceIntervalPlotBlock,
    CSVLoaderBlock,
    DatasetFrequencyTableBlock,
    DatasetNumericalStatsBlock,
    DatasetVariableTableBlock,
    HistogramBlock,
    NormalityTestBlock,
    QQPlotBlock,
    TwoMeanTTestBlock,
    VarianceTestBlock,
)
from src.statreportbuilder.core.graph import Edge, Graph
from src.statreportbuilder.core.pdf_export import export_html_to_pdf
from src.statreportbuilder.core.storage import Project
from src.statreportbuilder.ui.draft_report import compile_report_html


def build_showcase_graph() -> Graph:
    """Construct a comprehensive showcase graph with all block types."""
    g = Graph()

    # Infrastructure (excluded from report output via results.pop)
    g.nodes["loader"] = CSVLoaderBlock(
        "loader", params={"csv_name": "two_mean_ttest_dataset.csv"}
    )

    # Examination blocks
    g.nodes["variables"] = DatasetVariableTableBlock(
        "variables", params={"max_rows": 50}
    )
    g.nodes["freq"] = DatasetFrequencyTableBlock(
        "freq", params={"column": "group"}
    )
    g.nodes["numstats"] = DatasetNumericalStatsBlock(
        "numstats", params={"decimals": 4}
    )

    # Validity (assumption-checking) blocks
    g.nodes["normality"] = NormalityTestBlock(
        "normality",
        params={
            "group_column": "group",
            "value_column": "test_score",
            "alpha": 0.05,
        },
    )
    g.nodes["qq"] = QQPlotBlock(
        "qq",
        params={
            "group_column": "group",
            "value_column": "test_score",
            "output_size": "medium",
        },
    )
    g.nodes["variance"] = VarianceTestBlock(
        "variance",
        params={
            "group_column": "group",
            "value_column": "test_score",
            "alpha": 0.05,
        },
    )

    # Hypothesis test block
    g.nodes["ttest"] = TwoMeanTTestBlock(
        "ttest",
        params={
            "group_column": "group",
            "value_column": "test_score",
            "equal_var": False,
            "alpha": 0.05,
        },
    )

    # Post-hoc block
    g.nodes["ci"] = ConfidenceIntervalBlock(
        "ci",
        params={
            "group_column": "group",
            "value_column": "test_score",
            "confidence": 0.95,
            "equal_var": False,
        },
    )

    # Graphics blocks
    g.nodes["box"] = BoxplotBlock(
        "box",
        params={
            "group_column": "group",
            "value_column": "test_score",
            "output_size": "medium",
        },
    )
    g.nodes["hist"] = HistogramBlock(
        "hist",
        params={
            "group_column": "group",
            "value_column": "test_score",
            "bins": 20,
            "output_size": "medium",
        },
    )
    g.nodes["ciplot"] = ConfidenceIntervalPlotBlock(
        "ciplot",
        params={
            "group_column": "group",
            "value_column": "test_score",
            "confidence": 0.95,
            "output_size": "medium",
        },
    )

    # Text block (no inputs)
    g.nodes["action"] = ActionImpactBlock(
        "action",
        params={
            "action": "Adopt the experimental teaching method for the next academic year.",
            "impact": (
                "Students taught with the experimental method scored significantly higher "
                "on standardised tests (p < 0.05). Implementing this approach across all "
                "cohorts is expected to raise average test scores by approximately 5 points."
            ),
        },
    )

    # Wire all dataframe consumers to loader output
    df_consumers = [
        "variables",
        "freq",
        "numstats",
        "normality",
        "qq",
        "variance",
        "ttest",
        "ci",
        "box",
        "hist",
        "ciplot",
    ]
    for nid in df_consumers:
        g.edges.append(Edge("loader", "dataframe", nid, "dataframe"))

    return g


def main() -> None:
    """Generate the showcase report."""
    project = Project(
        name="project1",
        root=Path(__file__).parent / "Projects" / "project1",
    )

    print("Building showcase graph...")
    g = build_showcase_graph()

    print("Executing graph...")
    results = g.execute({"project": project})

    # Report any block errors
    for nid, res in results.items():
        if isinstance(res, dict) and "_error" in res:
            print(f"  [ERROR] Block '{nid}': {res['_error']}")

    # Suppress loader from report output (it's infrastructure, not a section)
    results.pop("loader", None)

    print("Compiling HTML...")
    html = compile_report_html(g, results)

    # Inject a document-level title
    title_html = (
        "<h1 style='color:#1f5fa8;'>StatReportBuilder — T-Test Workflow Showcase</h1>"
        f"<p style='color:#888;font-size:10pt;'>Generated {date.today()}</p><hr/>"
    )
    html = html.replace("<body>", f"<body>{title_html}", 1)

    # Write HTML
    out_dir = project.reports_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "showcase_report.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"[OK] HTML report: {html_path}")

    # Write PDF
    pdf_path = out_dir / "showcase_report.pdf"
    export_html_to_pdf(html, pdf_path)
    print(f"[OK] PDF report: {pdf_path}")

    print("\nShowcase report generated successfully!")


if __name__ == "__main__":
    main()
