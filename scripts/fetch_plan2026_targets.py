# -*- coding: utf-8 -*-
"""Fetch latest 2026 plan2026 HTML from IR busiMgr4 for briefing target departments."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

IR_SCRIPTS = Path(r"F:\기획평가\2026\2025연차보고서\연차보고 시스템으로 정리\scripts")
sys.path.insert(0, str(IR_SCRIPTS))

from playwright.sync_api import sync_playwright  # noqa: E402

from scrape_ir import (  # type: ignore  # noqa: E402
    DATA_PATH,
    download_plan2026_by_suffix,
    load_config,
    login,
)

# (busiMgr4 suffix in project name, report department name)
TARGETS: list[tuple[str, str]] = [
    ("건축・안전관리팀", "건축・안전관리팀"),
    ("교육미디어지원팀", "교육미디어지원팀"),
    ("조경미화팀", "조경미화팀"),
    ("전기통신팀", "전기통신팀"),
    ("관재팀", "관재팀"),
    ("총무인사팀", "총무과"),
    ("기획처", "기획처"),
    ("IR센터", "IR센터"),
    ("학생복지팀", "학생복지팀"),
    ("장애학생지원센터", "장애학생지원센터"),
    ("학생상담센터", "학생상담센터"),
    ("교목처", "교목처"),
    ("인성교육원", "인성교육원"),
    ("콘서바토리", "콘서바토리"),
    ("교수지원", "교수지원"),
    ("교원인사", "교원인사"),
    ("학사지원팀", "학사지원팀"),
    ("부속실", "부속실"),
    ("커뮤니케이션팀", "커뮤니케이션팀"),
    ("대외협력처", "대외국제처"),
    ("연구산학팀", "연구산학팀"),
    ("소프트웨어중심대학사업단", "소프트웨어중심대학사업단"),
    ("학술정보팀", "학술정보팀"),
    ("정보전산팀", "정보전산팀"),
    ("취업진로지원센터", "취업진로지원센터"),
    ("창업교육센터", "창업교육센터"),
    ("국제교육원", "국제교육원"),
    ("일반대학원(교학)", "일반대학원(교학)"),
    ("신학대학원(교학)", "신학대학원(교학)"),
    ("경영대학원(교학)", "경영대학원(교학)"),
    ("재무팀", "재무팀"),
    ("구매팀", "구매팀"),
]

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "fetch_plan2026_targets_log.json"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not DATA_PATH.is_file():
        raise SystemExit(f"Missing {DATA_PATH}")

    cfg = load_config()
    plan_year = int(cfg.get("plan2026Year", 2026))
    force = "--skip-force" not in sys.argv

    report = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    summary: dict = {"targets": [], "force": force, "planYear": plan_year}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context(
            viewport={"width": 1600, "height": 900},
            accept_downloads=True,
        )
        page = context.new_page()
        login(page, cfg)

        for suffix, dept_name in TARGETS:
            print(f"\n=== {dept_name} (suffix: {suffix}) ===", flush=True)
            log = download_plan2026_by_suffix(
                page,
                report,
                suffix=suffix,
                dept_name=dept_name,
                plan_year=plan_year,
                force=force,
            )
            report["plan2026SyncedAt"] = datetime.now(timezone.utc).astimezone().isoformat(
                timespec="seconds"
            )
            DATA_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            entry = {
                "suffix": suffix,
                "dept": dept_name,
                "matched": len(log["matched"]),
                "downloaded": len(log["downloaded"]),
                "skipped": len(log["skipped"]),
                "failed": len(log["failed"]),
            }
            summary["targets"].append(entry)
            print(
                f"  matched={entry['matched']} downloaded={entry['downloaded']} "
                f"skipped={entry['skipped']} failed={entry['failed']}",
                flush=True,
            )

        browser.close()

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote log {LOG_PATH}")
    print(f"Updated {DATA_PATH}")


if __name__ == "__main__":
    main()
