from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument


def export_html_to_pdf(html: str, output_path: Path) -> None:
    writer = QPdfWriter(str(output_path))
    writer.setResolution(96)
    writer.setPageSize(QPageSize(QPageSize.Letter))
    writer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Millimeter)

    doc = QTextDocument()
    doc.setHtml(html)

    print_method = getattr(doc, "print_", None) or doc.print
    print_method(writer)
