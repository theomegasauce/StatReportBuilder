from __future__ import annotations

from src.statreportbuilder.core.blocks import (
    CATEGORY_EXAMINATION,
    CATEGORY_GRAPHICS,
    CATEGORY_HYPOTHESIS,
    CATEGORY_POSTHOC,
    CATEGORY_TEXT,
    CATEGORY_VALIDITY,
)


# Blue-hued palette
PRIMARY = "#1f5fa8"
PRIMARY_HOVER = "#174d8a"
PRIMARY_LIGHT = "#e8f1fb"
ACCENT = "#4a90e2"

BG_APP = "#f4f7fb"
BG_PANEL = "#ffffff"
BG_PANEL_ALT = "#fafcff"
BG_HEADER = "#eaf1f9"
BG_REGION = "#eef3fa"

BORDER = "#cdd7e3"
BORDER_STRONG = "#a8b8cc"

TEXT_PRIMARY = "#1c2733"
TEXT_MUTED = "#5e6b7a"
TEXT_FAINT = "#8a96a3"


# Per-category color coding (hue → light bg, mid border, deep accent text)
CATEGORY_COLORS: dict[str, dict[str, str]] = {
    CATEGORY_EXAMINATION: {
        "bg": "#e6f1fb",
        "bg_hover": "#d4e7f7",
        "border": "#7fb1de",
        "accent": "#1f5fa8",
        "header_bg": "#cfe3f4",
    },
    CATEGORY_VALIDITY: {
        "bg": "#e3f3ee",
        "bg_hover": "#cee9e0",
        "border": "#77b9a3",
        "accent": "#1d7a5f",
        "header_bg": "#cae6db",
    },
    CATEGORY_HYPOTHESIS: {
        "bg": "#e7ecf9",
        "bg_hover": "#d3dcf2",
        "border": "#7e92cf",
        "accent": "#3147a3",
        "header_bg": "#d0d9ee",
    },
    CATEGORY_POSTHOC: {
        "bg": "#f1eaf6",
        "bg_hover": "#e3d6ed",
        "border": "#a48cc0",
        "accent": "#6b3f93",
        "header_bg": "#dccfe6",
    },
    CATEGORY_GRAPHICS: {
        "bg": "#fbf0e1",
        "bg_hover": "#f4e1c6",
        "border": "#dab27a",
        "accent": "#9c6a1f",
        "header_bg": "#efd8b3",
    },
    CATEGORY_TEXT: {
        "bg": "#eef0f3",
        "bg_hover": "#dee2e8",
        "border": "#9aa6b6",
        "accent": "#46566a",
        "header_bg": "#dde2e9",
    },
}


def category_color(category: str, key: str) -> str:
    palette = CATEGORY_COLORS.get(category, CATEGORY_COLORS[CATEGORY_EXAMINATION])
    return palette[key]


GLOBAL_STYLESHEET = f"""
QWidget {{
    color: {TEXT_PRIMARY};
    font-size: 12px;
}}

QMainWindow, QDialog {{
    background: {BG_APP};
}}

QMenuBar {{
    background: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    background: transparent;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background: {PRIMARY_LIGHT};
    color: {PRIMARY};
}}

QMenu {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    padding: 4px;
}}
QMenu::item {{
    padding: 5px 18px;
    border-radius: 3px;
}}
QMenu::item:selected {{
    background: {PRIMARY_LIGHT};
    color: {PRIMARY};
}}

QPushButton {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    padding: 5px 14px;
    border-radius: 4px;
    color: {TEXT_PRIMARY};
}}
QPushButton:hover {{
    background: {PRIMARY_LIGHT};
    border-color: {ACCENT};
    color: {PRIMARY};
}}
QPushButton:pressed {{
    background: {BG_HEADER};
}}
QPushButton:disabled {{
    background: #f0f2f5;
    color: {TEXT_FAINT};
    border-color: {BORDER};
}}

QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    padding: 3px 6px;
    border-radius: 4px;
    color: {TEXT_PRIMARY};
}}
QToolButton:hover {{
    background: {PRIMARY_LIGHT};
    border-color: {ACCENT};
    color: {PRIMARY};
}}

QLineEdit, QPlainTextEdit, QTextBrowser, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 3px 6px;
    selection-background-color: {ACCENT};
    selection-color: white;
}}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 18px;
}}

QCheckBox {{
    spacing: 6px;
}}

QTreeWidget, QListWidget, QTableWidget {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
    selection-background-color: {PRIMARY_LIGHT};
    selection-color: {PRIMARY};
    alternate-background-color: {BG_PANEL_ALT};
}}
QTreeWidget::item, QListWidget::item {{
    padding: 3px 4px;
}}
QTreeWidget::item:hover, QListWidget::item:hover {{
    background: {BG_HEADER};
}}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background: {PRIMARY_LIGHT};
    color: {PRIMARY};
}}
QHeaderView::section {{
    background: {BG_HEADER};
    border: none;
    border-right: 1px solid {BORDER};
    padding: 4px 8px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
}}

QSplitter::handle {{
    background: {BORDER};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #c2cfe0;
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: #c2cfe0;
    border-radius: 5px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QToolTip {{
    background: {TEXT_PRIMARY};
    color: white;
    border: 1px solid {PRIMARY};
    padding: 3px 6px;
}}
"""
