# -*- coding: utf-8 -*-
"""Embed merged IR + submission data into index.html and briefing.html."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from budget_history import merge_budget_history
from plan2026_budget import enrich_plan2026_budgets
from submission_data import merge_submission_into_report

ROOT = Path(__file__).resolve().parent.parent
CONFIG = Path(__file__).resolve().parent / "config.json"
MARKER_START = '<script id="report-data" type="application/json">'
MARKER_END = '</script>'

EMBED_TARGETS = (
    ROOT / "index.html",
    ROOT / "briefing.html",
)


def load_config() -> dict:
    with CONFIG.open(encoding="utf-8") as f:
        return json.load(f)


def embed_json(html_path: Path, merged: dict) -> None:
    html = html_path.read_text(encoding="utf-8")
    if MARKER_START not in html:
        raise SystemExit(f"Marker not found in {html_path}")

    start = html.index(MARKER_START) + len(MARKER_START)
    end = html.index(MARKER_END, start)
    embedded = json.dumps(merged, ensure_ascii=False, separators=(",", ":"))
    html_path.write_text(html[:start] + embedded + html[end:], encoding="utf-8")


def main() -> None:
    cfg = load_config()
    report_path = Path(cfg["paths"]["reportJson"])
    if not report_path.is_file():
        raise SystemExit(f"Missing {report_path}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    merged = merge_submission_into_report(report, cfg)
    history_path = cfg.get("paths", {}).get("budgetHistoryJson")
    perf_snapshots = cfg.get("paths", {}).get("perfSnapshots") or {}
    merged = merge_budget_history(
        merged,
        Path(history_path) if history_path else None,
        perf_snapshots,
    )
    ir_pdf_root = Path(cfg["paths"]["irPdfRoot"])
    merged = enrich_plan2026_budgets(merged, ir_pdf_root)
    kst = timezone(timedelta(hours=9))
    merged["builtAt"] = datetime.now(kst).strftime("%Y-%m-%d %H:%M")

    for target in EMBED_TARGETS:
        if not target.is_file():
            print(f"Skip (not found): {target}")
            continue
        embed_json(target, merged)
        print(f"Embedded {len(merged.get('departments', []))} departments into {target}")

    sm = merged.get("submissionMeta", {})
    print(
        f"Submission: {sm.get('submittedCount', 0)} submitted, "
        f"{sm.get('notSubmittedCount', 0)} pending, "
        f"{sm.get('approvedCount', 0)} GW approved, "
        f"{sm.get('anomalyCount', 0)} anomalies"
    )


if __name__ == "__main__":
    main()
