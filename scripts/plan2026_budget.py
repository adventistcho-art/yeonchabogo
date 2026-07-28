# -*- coding: utf-8 -*-
"""Parse 2026 adjusted budget from plan2026 HTML exports."""
from __future__ import annotations

import os
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


def _resolve_plan_path(
    href_or_rel: str,
    ir_pdf_root: Path | None = None,
    site_root: Path | None = None,
) -> Path | None:
    if not href_or_rel:
        return None
    if href_or_rel.startswith("file:"):
        path = unquote(urlparse(href_or_rel).path)
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        p = Path(path)
        return p if p.is_file() else None
    rel = href_or_rel.replace("/", os.sep)
    for base in (ir_pdf_root, site_root):
        if not base:
            continue
        candidate = base / rel
        if candidate.is_file():
            return candidate
    return None


def _project_budget_fallback(proj: dict) -> int | None:
    raw = proj.get("budget")
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    digits = re.sub(r"[^\d]", "", str(raw))
    return int(digits) if digits else None


def enrich_plan2026_budgets(
    report: dict,
    ir_pdf_root: Path | None = None,
    site_root: Path | None = None,
) -> dict:
    """Add budget2026 to projects and summary2026 to departments."""
    for dept in report.get("departments", []):
        total = 0
        funded = 0
        for proj in dept.get("projects", []):
            href = proj.get("plan2026HtmlPath")
            budget2026 = None
            path = _resolve_plan_path(href or "", ir_pdf_root, site_root)
            if path and path.is_file():
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                    val = parse_plan2026_budget(text)
                    if val > 0:
                        budget2026 = val
                except OSError:
                    budget2026 = None
            if not budget2026:
                fallback = _project_budget_fallback(proj)
                budget2026 = fallback if fallback else 0
            proj["budget2026"] = budget2026
            if budget2026 and budget2026 > 0:
                total += budget2026
                funded += 1
        summary2026: dict[str, Any] = {
            "totalBudget": total,
            "fundedProjectCount": funded,
        }
        perf2026 = dept.get("performance2026", {}).get("adjustedBudget")
        if perf2026 is not None:
            summary2026["source"] = "perfGrid"
            summary2026["totalBudget"] = perf2026
        elif total > 0:
            summary2026["source"] = "plan2026Html"
        dept["summary2026"] = summary2026
    return report


def dept_by_name(report: dict, name: str) -> dict | None:
    return next((d for d in report.get("departments", []) if d.get("name") == name), None)
