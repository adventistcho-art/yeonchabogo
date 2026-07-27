# -*- coding: utf-8 -*-
"""Approve 연차보고서 docs in GW 결재할문서함 (내부수신 SCHED boxid=202)."""
import argparse
import sys

from gw_client import approve_document, configure_console_encoding, fetch_pending_yeoncha_docs, make_session


def main() -> None:
    configure_console_encoding()
    parser = argparse.ArgumentParser(description="GW 결재할문서함 연차보고서 자동 승인")
    parser.add_argument("phpsessid", help="PHPSESSID cookie value")
    parser.add_argument("sekey", nargs="?", default="", help="sekey cookie value (optional)")
    parser.add_argument("--dry-run", action="store_true", help="List targets only, do not approve")
    parser.add_argument(
        "--title-filter",
        default=r"연차|부서연차",
        help="Regex for document title filter (default: 연차|부서연차)",
    )
    args = parser.parse_args()

    import re

    title_filter = re.compile(args.title_filter, re.I)
    session = make_session(args.phpsessid, args.sekey)

    docs = fetch_pending_yeoncha_docs(session)
    docs = [d for d in docs if title_filter.search(d.get("title", ""))]
    print(f"Pending docs to approve: {len(docs)}")
    for d in docs:
        print(f"  [{d.get('worklistid')}] {d['sender']} | {d['title'][:50]}")

    if args.dry_run:
        return

    ok_count = 0
    fail_count = 0
    for d in docs:
        wid = d.get("worklistid")
        ok, msg = approve_document(session, d)
        status = "OK" if ok else "FAIL"
        print(f"{status} {wid} {d['sender']}: {msg}")
        if ok:
            ok_count += 1
        else:
            fail_count += 1

    print(f"Done: {ok_count} approved, {fail_count} failed")


if __name__ == "__main__":
    main()
