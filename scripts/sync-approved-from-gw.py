# -*- coding: utf-8 -*-
"""Scrape GW 결재한 공문·통합문서함 and sync approved_submissions.json + PDF downloads."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from gw_client import (
    INTEGRATED_DOCBOX_ID,
    configure_console_encoding,
    download_submission_pdf,
    fetch_yeoncha_docs,
    IR_TARGET,
    make_session,
    merge_gw_docs,
)
from submission_utils import GW_SEARCH_KEYWORDS, infer_dept

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"


def load_paths() -> tuple[Path, Path, str]:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        cfg = json.load(f)
    target = Path(cfg["paths"]["submissionDir"])
    approved_json = target / "approved_submissions.json"
    docbox_id = str(cfg.get("gw", {}).get("integratedDocboxId", INTEGRATED_DOCBOX_ID))
    return target, approved_json, docbox_id


def preserve_legacy_entries(all_docs: list[dict], approved_json: Path) -> list[dict]:
    if not approved_json.is_file():
        return all_docs
    with approved_json.open(encoding="utf-8") as f:
        old = json.load(f).get("approved", [])
    by_sender = {d["sender"]: d for d in old if d.get("sender")}
    for d in all_docs:
        if not d.get("worklistid") and d["sender"] in by_sender:
            d["worklistid"] = by_sender[d["sender"]].get("worklistid")
        if d.get("dept") is None and d["sender"] in by_sender:
            d["dept"] = by_sender[d["sender"]].get("dept")
    new_senders = {d["sender"] for d in all_docs}
    for d in old:
        if d.get("sender") and d["sender"] not in new_senders:
            d["dept"] = infer_dept(d.get("title", ""), d["sender"], IR_TARGET) or d.get("dept")
            all_docs.append(d)
    return merge_gw_docs(all_docs, [])


def main() -> None:
    configure_console_encoding()
    if len(sys.argv) < 2:
        print("Usage: sync-approved-from-gw.py <PHPSESSID> [sekey]")
        sys.exit(1)

    target_dir, approved_json, docbox_id = load_paths()
    phpsessid = sys.argv[1]
    sekey = sys.argv[2] if len(sys.argv) > 2 else ""

    session = make_session(phpsessid, sekey)
    all_docs = fetch_yeoncha_docs(session, docbox_id=docbox_id)
    all_docs = preserve_legacy_entries(all_docs, approved_json)

    target_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[str] = []
    for d in all_docs:
        wid = d.get("worklistid")
        sender = d["sender"]
        out_pdf = target_dir / f"{sender}.pdf"
        if out_pdf.exists():
            continue
        if not wid:
            print(f"SKIP download (no worklistid): {sender}")
            continue
        if download_submission_pdf(
            session,
            wid,
            out_pdf,
            phpsessid=phpsessid,
            sekey=sekey,
        ):
            downloaded.append(sender)
            print(f"OK {sender}.pdf")
        else:
            print(f"FAIL {wid} {sender}")

    by_source: dict[str, int] = {}
    for d in all_docs:
        src = d.get("gwSource") or "unknown"
        by_source[src] = by_source.get(src, 0) + 1

    meta = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": (
            "결재할문서함·결재한문서함·통합문서함 "
            f"(검색: {', '.join(GW_SEARCH_KEYWORDS)}, docbox={docbox_id})"
        ),
        "sources": by_source,
        "approved": all_docs,
    }
    with approved_json.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    mapped = sum(1 for d in all_docs if d.get("dept"))
    print(f"Total approved: {len(all_docs)}, IR mapped: {mapped}, Downloaded: {len(downloaded)}")
    print(f"By source: {by_source}")
    print(f"Saved: {approved_json}")


if __name__ == "__main__":
    main()
