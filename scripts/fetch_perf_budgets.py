# -*- coding: utf-8 -*-
"""Fetch IR perf list for prior years and write budget_history.json + perf snapshots."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = Path(__file__).resolve().parent / "config.json"
IR_SCRIPTS = Path(r"F:\기획평가\2026\2025연차보고서\연차보고 시스템으로 정리\scripts")


def _parse_money(value) -> int | None:
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


def rows_to_history(rows: list[dict], year: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        name = row.get("budgOrgnNm") or row.get("deptNm")
        budget = _parse_money(row.get("finBudgAmt"))
        if name and budget is not None:
            out.setdefault(name, {})[year] = budget
    return out


def merge_histories(*maps: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    merged: dict[str, dict[str, int]] = {}
    for m in maps:
        for dept, years in m.items():
            merged.setdefault(dept, {}).update(years)
    return merged


def search_param_for_year(page, year: int) -> str:
    """Set deptAnnualReport search year and return API query string."""
    if "/kuts/deptAnnualReport" not in page.url:
        page.goto("https://ir.syu.ac.kr/kuts/deptAnnualReport", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(3000)
    page.evaluate(
        """(year) => {
            search.setItemValue('sYear', String(year));
            searchStart();
        }""",
        str(year),
    )
    page.wait_for_timeout(5000)
    return page.evaluate("() => search.getParam()")


def fetch_years_via_ir(years: list[int]) -> dict[int, list[dict]]:
    if not IR_SCRIPTS.is_dir():
        raise SystemExit(f"IR scripts not found: {IR_SCRIPTS}")
    sys.path.insert(0, str(IR_SCRIPTS))
    from scrape_ir import APIS, FETCH_ALL_JS, login  # type: ignore

    from playwright.sync_api import sync_playwright

    cfg_path = IR_SCRIPTS / "config.json"
    ir_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    out: dict[int, list[dict]] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login(page, ir_cfg)
        for year in years:
            search_param = search_param_for_year(page, year)
            rows = page.evaluate(
                FETCH_ALL_JS,
                {"apiPath": APIS["perf"], "searchParam": search_param},
            )
            out[year] = [r for r in rows if str(r.get("yyyy")) == str(year)]
            print(f"  {year}: {len(out[year])} perf rows")
        browser.close()
    return out


def main() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    paths = cfg.get("paths", {})
    data_dir = Path(paths["reportJson"]).parent
    years = [2023, 2024, 2026]
    snapshots = paths.get("perfSnapshots") or {}

    try:
        fetched = fetch_years_via_ir(years)
    except Exception as exc:
        print(f"IR fetch skipped ({exc})")
        print("Using existing perf snapshot files if present.")
        fetched = {}

    histories = []
    for year in years:
        snap_path = Path(snapshots.get(str(year), data_dir / f"perf{year}.json"))
        if year in fetched:
            snap_path.write_text(
                json.dumps(fetched[year], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Wrote {snap_path}")
            histories.append(rows_to_history(fetched[year], str(year)))
        elif snap_path.is_file():
            rows = json.loads(snap_path.read_text(encoding="utf-8"))
            histories.append(rows_to_history(rows, str(year)))
            print(f"Loaded {snap_path}")

    if not histories:
        raise SystemExit("No perf data. Run with IR access or place perf2024.json in data/.")

    history = merge_histories(*histories)
    out_path = Path(paths.get("budgetHistoryJson", data_dir / "budget_history.json"))
    out_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} ({len(history)} departments)")


if __name__ == "__main__":
    main()
