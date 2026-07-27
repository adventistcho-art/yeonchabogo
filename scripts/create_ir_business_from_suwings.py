# -*- coding: utf-8 -*-
"""SU-WINGs 신규 사업 -> IR 계획관리(busiTreeMgr) 자동 등록."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

from ir_business_client import create_business, login_ir
from suwings_client import fetch_business_with_login

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
FALLBACK_CONFIG = Path(r"F:\기획평가\2026\2025연차보고서\연차보고 시스템으로 정리\scripts\config.json")


def configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def load_credentials(args: argparse.Namespace) -> tuple[str, str, str]:
    username = args.username
    password = args.password
    base_url = args.ir_url
    for path in (CONFIG_PATH, FALLBACK_CONFIG):
        if not path.is_file():
            continue
        cfg = json.loads(path.read_text(encoding="utf-8"))
        username = username or cfg.get("username", "")
        password = password or cfg.get("password", "")
        base_url = base_url or cfg.get("baseUrl", "https://ir.syu.ac.kr/")
    if not username or not password:
        raise SystemExit("username/password가 필요합니다. config.json 또는 CLI 인자로 지정하세요.")
    return username, password, base_url


def main() -> None:
    configure_console_encoding()
    parser = argparse.ArgumentParser(description="SU-WINGs 신규 사업을 IR 계획관리에 등록")
    parser.add_argument("--busi-name", required=True, help="SU-WINGs 사업명")
    parser.add_argument("--dept-name", required=True, help="IR 주관부서명 (예: 금연금주클리닉)")
    parser.add_argument("--year", default="", help="IR/SU-WINGs 연도 (기본: SU-WINGs 회계년도)")
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--ir-url", default="")
    parser.add_argument("--show-browser", action="store_true", help="SU-WINGs 조회 시 브라우저 표시")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-suwings", action="store_true", help="SU-WINGs 조회 생략")
    parser.add_argument("--busi-code", default="", help="--skip-suwings일 때 사업코드")
    parser.add_argument("--busi-class", default="", help="--skip-suwings일 때 사업분류 (예: 4-3-5 ...)")
    args = parser.parse_args()

    username, password, base_url = load_credentials(args)

    if args.skip_suwings:
        from suwings_client import SuwingsBusiness

        if not args.busi_code or not args.busi_class:
            raise SystemExit("--skip-suwings 사용 시 --busi-code, --busi-class 필요")
        sw = SuwingsBusiness(
            busi_name=args.busi_name,
            busi_code=args.busi_code,
            busi_class=args.busi_class,
            busi_class_code="",
            dept_name=args.dept_name,
            acnt_yy=args.year or "2026",
        )
    else:
        print(f"[1/3] SU-WINGs 조회: {args.busi_name}")
        sw = fetch_business_with_login(
            username,
            password,
            args.busi_name,
            args.dept_name,
            headless=not args.show_browser,
        )
        print(
            f"  사업코드={sw.busi_code}, 분류={sw.busi_class}, "
            f"담당부서(SU-WINGs)={sw.dept_name}, 회계년도={sw.acnt_yy}"
        )

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    print("[2/3] IR 로그인")
    login_ir(session, base_url, username, password)

    print("[3/3] IR 계획관리 등록")
    result = create_business(
        session,
        base_url,
        sw,
        args.dept_name,
        year=args.year or None,
        dry_run=args.dry_run,
    )
    print("완료")
    print(f"  IR 사업명 : {result.ir_name}")
    print(f"  LVL_CD    : {result.lvl_cd}")
    print(f"  사업코드  : {result.prog_cd}")
    print(f"  주관부서  : {result.dept_name} ({result.dept_cd})")
    print(f"  상위분류  : {result.parent_lvl_cd}")
    print(f"  연도      : {result.year}")
    if args.dry_run:
        print("  (dry-run: IR 저장은 수행하지 않았습니다)")


if __name__ == "__main__":
    main()
