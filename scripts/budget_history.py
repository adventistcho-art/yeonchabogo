# -*- coding: utf-8 -*-
"""Merge multi-year budget history into report departments."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _parse_money(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = re.sub(r"[^\d.-]", "", str(value))
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def load_budget_history(path: Path) -> dict[str, dict[str, int | None]]:
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, int | None]] = {}
    for dept_name, years in raw.items():
        if not isinstance(years, dict):
            continue
        out[dept_name] = {str(y): _parse_money(v) for y, v in years.items()}
    return out


def history_from_perf_snapshots(snapshots: dict[str, str | Path]) -> dict[str, dict[str, int]]:
    """Build {dept: {year: budget}} from IR perf list exports."""
    out: dict[str, dict[str, int]] = {}
    for year, path in snapshots.items():
        p = Path(path)
        if not p.is_file():
            continue
        rows = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            continue
        for row in rows:
            name = row.get("budgOrgnNm") or row.get("deptNm")
            budget = _parse_money(row.get("finBudgAmt"))
            if not name or budget is None:
                continue
            out.setdefault(name, {})[str(year)] = budget
    return out


def merge_budget_history(
    report: dict,
    history_path: Path | None = None,
    perf_snapshots: dict[str, str | Path] | None = None,
) -> dict:
    history = load_budget_history(history_path) if history_path else {}
    if perf_snapshots:
        for dept, years in history_from_perf_snapshots(perf_snapshots).items():
            history.setdefault(dept, {}).update(years)

    report_year = str(report.get("year", 2025))
    for dept in report.get("departments", []):
        name = dept.get("name", "")
        perf = dept.setdefault("performance", {})
        current = _parse_money(perf.get("adjustedBudget"))
        hist = dict(history.get(name, {}))
        if current is not None:
            hist[report_year] = current
        cleaned = {y: v for y, v in sorted(hist.items()) if v is not None}
        dept["budgetHistory"] = cleaned

        b_prev = cleaned.get(str(int(report_year) - 1))
        b_curr = cleaned.get(report_year)
        if b_prev and b_curr and b_prev > 0:
            dept["budgetChangeRate"] = round((b_curr - b_prev) / b_prev * 100, 1)
        else:
            dept["budgetChangeRate"] = None
    return report
