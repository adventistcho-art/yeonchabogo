# -*- coding: utf-8 -*-
"""Persist grad-school plan2026 project data from briefing embed into report2025.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

GRAD_DEPTS = (
    "일반대학원(교학)",
    "신학대학원(교학)",
    "경영대학원(교학)",
)

MARKER_START = '<script id="report-data" type="application/json">'
MARKER_END = "</script>"


def load_briefing_report(briefing_path: Path) -> dict:
    html = briefing_path.read_text(encoding="utf-8")
    start = html.index(MARKER_START) + len(MARKER_START)
    end = html.index(MARKER_END, start)
    return json.loads(html[start:end])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parent.parent
    cfg = json.loads((root / "scripts" / "config.json").read_text(encoding="utf-8"))
    report_path = Path(cfg["paths"]["reportJson"])
    briefing_path = root / "briefing.html"

    if not briefing_path.is_file():
        raise SystemExit(f"Missing {briefing_path}")

    briefing = load_briefing_report(briefing_path)
    briefing_by_name = {d.get("name"): d for d in briefing.get("departments", [])}

    report = json.loads(report_path.read_text(encoding="utf-8"))
    report_depts = report.setdefault("departments", [])
    index_by_name = {d.get("name"): i for i, d in enumerate(report_depts)}

    for dept_name in GRAD_DEPTS:
        src = briefing_by_name.get(dept_name)
        if not src:
            print(f"Skip missing in briefing: {dept_name}")
            continue
        plan_count = sum(1 for p in src.get("projects", []) if p.get("plan2026HtmlPath"))
        if dept_name in index_by_name:
            report_depts[index_by_name[dept_name]] = src
        else:
            report_depts.append(src)
            index_by_name[dept_name] = len(report_depts) - 1
        print(f"{dept_name}: {len(src.get('projects', []))} projects, {plan_count} plan2026")

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {report_path}")


if __name__ == "__main__":
    main()
