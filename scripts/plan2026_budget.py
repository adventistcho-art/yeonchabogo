# -*- coding: utf-8 -*-
"""Parse 2026 adjusted budget from plan2026 HTML exports."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


def _cell_digits(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "", html, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"[^\d]", "", text)


def parse_plan2026_budget(html_text: str) -> int:
    """Sum 조정예산 (column 7) from plan2026 HTML."""
    total = 0
    pattern = re.compile(
        r'ColAddr="7"[^>]*align="right"[^>]*>(.*?)</TD>',
        re.S | re.I,
    )
    for block in pattern.findall(html_text):
        digits = _cell_digits(block)
        if digits:
            total += int(digits)
    return total


def _resolve_plan_path(href_or_rel: str, ir_pdf_root: Path | None) -> Path | None:
    if not href_or_rel:
        return None
    if href_or_rel.startswith("file:"):
        path = unquote(urlparse(href_or_rel).path)
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        return Path(path)
    if ir_pdf_root:
        return ir_pdf_root / href_or_rel.replace("/", "\\")
    return Path(href_or_rel)


def enrich_plan2026_budgets(report: dict, ir_pdf_root: Path | None = None) -> dict:
    """Add budget2026 to projects and summary2026 to departments."""
    for dept in report.get("departments", []):
        total = 0
        funded = 0
        for proj in dept.get("projects", []):
            href = proj.get("plan2026HtmlPath")
            budget2026 = None
            path = _resolve_plan_path(href or "", ir_pdf_root)
            if path and path.is_file():
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                    val = parse_plan2026_budget(text)
                    budget2026 = val if val > 0 else 0
                except OSError:
                    budget2026 = None
            proj["budget2026"] = budget2026
            if budget2026 and budget2026 > 0:
                total += budget2026
                funded += 1
        dept["summary2026"] = {
            "totalBudget": total,
            "fundedProjectCount": funded,
        }
    return report


def dept_by_name(report: dict, name: str) -> dict | None:
    return next((d for d in report.get("departments", []) if d.get("name") == name), None)
