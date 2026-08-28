# -*- coding: utf-8 -*-
"""Embed merged IR + submission data into dashboard.html and briefing.html."""
import json
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

from budget_history import merge_budget_history
from performance_plan_html import enrich_performance_plan_html
from plan2026_budget import enrich_plan2026_budgets
from submission_data import merge_submission_into_report

ROOT = Path(__file__).resolve().parent.parent
CONFIG = Path(__file__).resolve().parent / "config.json"
MARKER_START = '<script id="report-data" type="application/json">'
MARKER_END = '</script>'

EMBED_TARGETS = (
    ROOT / "dashboard.html",
    ROOT / "briefing.html",
)


def load_config() -> dict:
    with CONFIG.open(encoding="utf-8") as f:
        return json.load(f)


def embed_json(html_path: Path, merged: dict) -> None:
    html = html_path.read_text(encoding="utf-8")
    if MARKER_START not in html:
        raise SystemExit(f"Marker not found in {html_path}")
    if MARKER_END not in html:
        raise SystemExit(f"Closing marker not found in {html_path} (file may be truncated)")

    payload = sanitize_embed_payload(merged)
    start = html.index(MARKER_START) + len(MARKER_START)
    end = html.index(MARKER_END, start)
    embedded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    embedded = embedded.replace("</", "<\\/")
    new_html = html[:start] + embedded + html[end:]
    tmp_path = html_path.with_suffix(html_path.suffix + ".tmp")
    tmp_path.write_text(new_html, encoding="utf-8")
    tmp_path.replace(html_path)


def sanitize_embed_payload(report: dict) -> dict:
    """Drop bulky IR source fields already exported to html/ files."""
    payload = json.loads(json.dumps(report, ensure_ascii=False))
    for dept in payload.get("departments", []):
        evaluation = dept.get("evaluation") or {}
        evaluation.pop("performancePlan2026Html", None)
        dept["evaluation"] = evaluation
    return payload


def _file_uri_to_path(href: str) -> Path:
    path = unquote(urlparse(href).path)
    if path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]
    return Path(path)


def link_plan2026_from_site_html(report: dict, site_root: Path) -> int:
    """Attach site-relative plan2026 paths from html/{dept}/*.html when missing."""
    html_root = site_root / "html"
    if not html_root.is_dir():
        return 0

    linked = 0
    for dept in report.get("departments", []):
        dept_name = dept.get("name", "")
        dept_dir = html_root / dept_name
        if not dept_dir.is_dir():
            continue

        by_name = {p.get("name"): p for p in dept.get("projects", []) if p.get("name")}
        for path in sorted(dept_dir.glob("*_plan2026.html")):
            if path.name == "performance_plan2026.html":
                continue
            stem = path.stem
            project_name = stem[: -len("_plan2026")] if stem.endswith("_plan2026") else stem
            rel = Path("html") / dept_name / path.name
            proj = by_name.get(project_name)
            if not proj or proj.get("plan2026HtmlPath"):
                continue
            proj["plan2026HtmlPath"] = rel.as_posix()
            linked += 1
    return linked


def apply_web_plan2026_hrefs(
    report: dict,
    site_root: Path,
    ir_pdf_root: Path,
    *,
    path_key: str = "plan2026HtmlPath",
) -> int:
    """Use site-relative paths for HTML shipped under site_root/html/."""
    updated = 0
    items: list[tuple[dict, str | None]] = []
    if path_key == "performancePlan2026HtmlPath":
        for dept in report.get("departments", []):
            items.append((dept, dept.get(path_key)))
    else:
        for dept in report.get("departments", []):
            for proj in dept.get("projects", []):
                items.append((proj, proj.get(path_key)))

    for target, href in items:
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
            target[path_key] = rel
            updated += 1
    return updated


def copy_annual_report_pdfs(ir_pdf_root: Path, site_root: Path) -> int:
    """Copy annual_reports/{year}/*.pdf into the dashboard site for web-relative links."""
    copied = 0
    for year in (2024, 2025):
        src_dir = ir_pdf_root / "annual_reports" / str(year)
        if not src_dir.is_dir():
            continue
        dest_dir = site_root / "annual_reports" / str(year)
        dest_dir.mkdir(parents=True, exist_ok=True)
        for pdf in src_dir.glob("*.pdf"):
            dest = dest_dir / pdf.name
            if not dest.exists() or dest.stat().st_size != pdf.stat().st_size:
                shutil.copy2(pdf, dest)
            copied += 1
    return copied


def apply_web_annual_report_hrefs(report: dict, site_root: Path, ir_pdf_root: Path) -> int:
    """Use site-relative paths for annual report PDFs shipped under site_root."""
    updated = 0
    keys = ("annualReport2024PdfHref", "annualReport2025IrPdfHref", "annualReport2025PdfHref")
    for dept in report.get("departments", []):
        for key in keys:
            href = dept.get(key)
            if not href:
                continue
            if href.startswith("file:"):
                full = _file_uri_to_path(href)
                try:
                    rel = full.relative_to(ir_pdf_root).as_posix()
                except ValueError:
                    continue
            elif href.startswith("annual_reports/"):
                rel = href
            else:
                continue
            if (site_root / rel.replace("/", os.sep)).is_file():
                dept[key] = rel
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
    plan_html_count = enrich_performance_plan_html(merged, ROOT, ir_pdf_root)

    from copy_plan2026_html import copy_target_plan2026  # noqa: WPS433

    copy_target_plan2026()
    annual_pdf_count = copy_annual_report_pdfs(ir_pdf_root, ROOT)
    linked = link_plan2026_from_site_html(merged, ROOT)
    web_paths = apply_web_plan2026_hrefs(merged, ROOT, ir_pdf_root)
    web_plan_paths = apply_web_plan2026_hrefs(merged, ROOT, ir_pdf_root, path_key="performancePlan2026HtmlPath")
    web_annual_paths = apply_web_annual_report_hrefs(merged, ROOT, ir_pdf_root)
    kst = timezone(timedelta(hours=9))
    merged["builtAt"] = datetime.now(kst).strftime("%Y-%m-%d %H:%M")
    merged["webPlan2026Count"] = web_paths
    merged["webPerformancePlanCount"] = web_plan_paths
    merged["webAnnualReportCount"] = web_annual_paths
    merged["performancePlanHtmlCount"] = plan_html_count
    merged["annualReportPdfCount"] = annual_pdf_count

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
    print(f"Linked plan2026 from site html: {linked}")
    print(f"Web plan2026 hrefs: {web_paths}")
    print(f"Performance plan HTML: {plan_html_count} files, web hrefs: {web_plan_paths}")
    print(f"Annual report PDFs copied: {annual_pdf_count}, web hrefs: {web_annual_paths}")


if __name__ == "__main__":
    main()
