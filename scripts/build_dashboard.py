# -*- coding: utf-8 -*-
"""Embed merged IR + submission data into index.html and briefing.html."""
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

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


def _file_uri_to_path(href: str) -> Path:
    path = unquote(urlparse(href).path)
    if path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]
    return Path(path)


def apply_web_plan2026_hrefs(report: dict, site_root: Path, ir_pdf_root: Path) -> int:
    """Use site-relative paths for plan2026 HTML shipped under site_root/html/."""
    updated = 0
    for dept in report.get("departments", []):
        for proj in dept.get("projects", []):
            href = proj.get("plan2026HtmlPath")
            if not href:
                continue
            if href.startswith("file:"):
                full = _file_uri_to_path(href)
                try:
                    rel = full.relative_to(ir_pdf_root).as_posix()
                except ValueError:
                    continue
            elif href.startswith("html/"):
                rel = href
            else:
                continue
            if (site_root / rel.replace("/", os.sep)).is_file():
                proj["plan2026HtmlPath"] = rel
                updated += 1
    return updated


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
    merged = enrich_plan2026_budgets(merged, ir_pdf_root, ROOT)

    from copy_plan2026_html import copy_target_plan2026  # noqa: WPS433

    copy_target_plan2026()
    web_paths = apply_web_plan2026_hrefs(merged, ROOT, ir_pdf_root)
    kst = timezone(timedelta(hours=9))
    merged["builtAt"] = datetime.now(kst).strftime("%Y-%m-%d %H:%M")
    merged["webPlan2026Count"] = web_paths

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
    print(f"Web plan2026 hrefs: {web_paths}")


if __name__ == "__main__":
    main()
