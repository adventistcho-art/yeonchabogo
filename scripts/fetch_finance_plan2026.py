# -*- coding: utf-8 -*-
"""Fetch plan2026 HTML for 재무처 teams only."""
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

TARGETS = [
    ("예산팀", "예산팀"),
    ("재무팀", "재무팀"),
    ("구매팀", "구매팀"),
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = load_config()
    plan_year = int(cfg.get("plan2026Year", 2026))
    force = "--skip-force" not in sys.argv
    report = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context(
            viewport={"width": 1600, "height": 900},
            accept_downloads=True,
        )
        page = context.new_page()
        login(page, cfg)

        for suffix, dept_name in TARGETS:
            print(f"\n=== {dept_name} ===", flush=True)
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
            print(
                f"  matched={len(log['matched'])} downloaded={len(log['downloaded'])} "
                f"skipped={len(log['skipped'])} failed={len(log['failed'])}",
                flush=True,
            )

        browser.close()


if __name__ == "__main__":
    main()
