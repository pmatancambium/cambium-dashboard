"""Utilities for handling markdown tables and HTML conversion"""

import html as html_lib
from typing import List, Dict
import re


def is_markdown_table(text: str) -> bool:
    """Check if text is a markdown table or a delimited text"""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]

    if not lines:
        return False

    pipe_counts = [line.count("|") for line in lines]

    if min(pipe_counts) >= 3:
        return True

    if len(lines) >= 2:
        separator_line = lines[1]
        if "|" in separator_line:
            separator_cells = [cell.strip() for cell in separator_line.split("|")]
            separator_cells = [cell for cell in separator_cells if cell]
            if all(
                cell.replace("-", "").replace(":", "") == "" for cell in separator_cells
            ):
                return True

    return False


def parse_markdown_table(text: str) -> List[List[str]]:
    """Parse markdown table or delimited text into a 2D list of cells"""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    table_data = []

    for i, line in enumerate(lines):
        if (
            i == 1
            and "-" in line
            and all(
                cell.replace("-", "").replace(":", "") == ""
                for cell in line.split("|")
                if cell.strip()
            )
        ):
            continue

        cells = [cell.strip() for cell in line.split("|")]
        cells = [cell for cell in cells if cell]

        if cells:
            if any(len(cell) > 100 for cell in cells):
                max_cells = len(cells)
                current_row = []
                for cell in cells:
                    if len(cell) > 100:
                        if current_row:
                            table_data.append(current_row)
                        table_data.append([cell])
                        current_row = []
                    else:
                        current_row.append(cell)
                if current_row:
                    table_data.append(current_row)
            else:
                table_data.append(cells)

    return table_data


def format_table_html(markdown_text: str) -> str:
    """Convert markdown table to HTML with RTL support and enhanced styling"""
    table_data = parse_markdown_table(markdown_text)

    table_styles = """
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
        font-size: 14px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-radius: 4px;
        overflow: hidden;
    """

    header_styles = """
        background-color: #f8f9fa;
        color: #1a1a1a;
        font-weight: 600;
        padding: 12px;
        text-align: right;
        border: 1px solid #e0e0e0;
        white-space: nowrap;
    """

    cell_styles = """
        padding: 10px 12px;
        text-align: right;
        border: 1px solid #e0e0e0;
        line-height: 1.4;
    """

    row_hover_style = """
    <style>
        .custom-table tbody tr:hover {
            background-color: #f5f5f5;
            transition: background-color 0.2s ease;
        }
        .custom-table tbody tr:nth-child(even) {
            background-color: #fafafa;
        }
    </style>
    """

    output = f"{row_hover_style}<div dir='rtl'><table class='custom-table' style='{table_styles}'>"

    if table_data:
        output += "<thead><tr>"
        for cell in table_data[0]:
            escaped_cell = html_lib.escape(cell)
            if not escaped_cell or escaped_cell.strip("-| ") == "":
                escaped_cell = "&nbsp;"
            output += f"<th style='{header_styles}'>{escaped_cell}</th>"
        output += "</tr></thead>"

    if len(table_data) > 1:
        output += "<tbody>"
        for row in table_data[1:]:
            output += "<tr>"
            for cell in row:
                escaped_cell = html_lib.escape(cell)
                if not escaped_cell or escaped_cell.strip("-| ") == "":
                    escaped_cell = "&nbsp;"
                output += f"<td style='{cell_styles}'>{escaped_cell}</td>"
            output += "</tr>"
        output += "</tbody>"

    output += "</table></div>"
    return output
