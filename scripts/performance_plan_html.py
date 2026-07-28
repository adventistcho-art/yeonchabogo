# -*- coding: utf-8 -*-
"""Write IR performance plan (2026) HTML exports for dashboard viewing."""
from __future__ import annotations

import html as html_module
import re
from pathlib import Path


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:120] or "unknown"


def plan_body(dept: dict) -> str:
    evaluation = dept.get("evaluation") or {}
    raw = (evaluation.get("performancePlan2026Html") or "").strip()
    if raw and raw not in ("-", "null"):
        return raw
    text = (evaluation.get("performancePlan2026") or "").strip()
    if not text or text == "-":
        return ""
    return f"<pre>{html_module.escape(text)}</pre>"


def wrap_plan_document(dept_name: str, body: str) -> str:
    title = html_module.escape(dept_name)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ko">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        f"<title>{title} - 성과관리계획(2026년 반영)</title>\n"
        "<style>\n"
        "body { font-family: 'Malgun Gothic', sans-serif; margin: 24px; line-height: 1.6; color: #222; }\n"
        "h1 { font-size: 18px; margin: 0 0 16px; }\n"
        "pre { white-space: pre-wrap; word-break: break-word; font-family: inherit; margin: 0; }\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        f"<h1>{title} · 성과관리계획(2026년 반영)</h1>\n"
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )


def enrich_performance_plan_html(report: dict, site_root: Path, ir_pdf_root: Path) -> int:
    """Create html/{dept}/performance_plan2026.html from IR comment HTML/text."""
    count = 0
    for dept in report.get("departments", []):
        body = plan_body(dept)
        if not body:
            dept.pop("performancePlan2026HtmlPath", None)
            continue

        rel = Path("html") / safe_filename(dept["name"]) / "performance_plan2026.html"
        doc = wrap_plan_document(dept["name"], body)
        for root in (ir_pdf_root, site_root):
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(doc, encoding="utf-8")
        dept["performancePlan2026HtmlPath"] = rel.as_posix()
        count += 1
    return count
