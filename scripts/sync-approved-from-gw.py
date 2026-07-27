# -*- coding: utf-8 -*-
"""Scrape 결재할/결재한 문서함 (내부수신) and sync approved_submissions.json + PDF downloads."""
import json
import re
import sys
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, urlencode

import requests
from bs4 import BeautifulSoup

from submission_utils import GW_SEARCH_KEYWORDS, infer_dept

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
BASE_URL = "https://gw.syu.ac.kr/officialDoc/official_doc_receive_inside.html"

IR_DEPARTMENTS = sorted([
    "IR센터", "SUPREME센터", "건축・안전관리팀", "경영대학원(교학)", "공통기기실험실", "관재팀", "교목처",
    "교수지원", "교수학습개발팀", "교양교육원", "교원인사", "교육미디어지원팀", "국제교육원", "글로컬사회혁신원",
    "금연금주클리닉", "기획처", "대외국제처", "대학혁신지원사업단", "부속실", "비교과통합센터", "생활교육원",
    "소프트웨어중심대학사업단", "신학대학원(교학)", "예산팀", "원격교육지원센터", "인성교육원", "일반대학원(교학)",
    "임상간호대학원(교학)", "입학관리본부", "장애학생지원센터", "전기통신팀", "정보전산팀", "조경미화팀",
    "창업교육센터", "체육문화센터", "최고경영자과정", "취업진로지원센터", "커뮤니케이션팀", "콘서바토리", "평생교육원",
    "학사지원팀", "학생복지팀", "학생상담센터", "학술정보팀", "박물관", "연구산학팀",
])
EXCLUDED = {
    "신학과", "경영학과", "물리치료학과", "식품영양학과", "상담심리학과", "약학과", "음악학과",
    "건축학과(5년)", "화학생명과학과", "아트앤디자인학과", "컴퓨터공학부", "항공관광외국어학부",
    "동물자원과학과", "인공지능융합학부", "바이오융합공학과", "간호학과", "융합과학과",
    "환경디자인원예학과", "임상전문간호학과", "통합예술학과", "영어영문학과", "보건관리학과",
}
IR_TARGET = sorted(d for d in IR_DEPARTMENTS if d not in EXCLUDED)


def load_paths() -> tuple[Path, Path]:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        cfg = json.load(f)
    target = Path(cfg["paths"]["submissionDir"])
    approved_json = target / "approved_submissions.json"
    return target, approved_json


def extract_pdf_from_zip(data: bytes, out_path: str) -> bool:
    with zipfile.ZipFile(BytesIO(data)) as zf:
        pdfs = [n for n in zf.namelist() if n.lower().endswith(".pdf")]
        if not pdfs:
            return False
        with zf.open(pdfs[0]) as src, open(out_path, "wb") as dst:
            dst.write(src.read())
        return True


def configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def extract_worklist_id(tr, row_text: str) -> str | None:
    chk = tr.select_one("input[type=checkbox][worklistid]")
    if chk and chk.get("worklistid"):
        return chk["worklistid"]

    blob = row_text
    for td in tr.select("td"):
        blob += " " + (td.get("onclick") or "")
    for a in tr.select("a[href]"):
        blob += " " + a.get("href", "")

    wid_match = re.search(r"worklistid[='](\d+)", blob, re.I)
    if wid_match:
        return wid_match.group(1)
    go_match = re.search(r"goView\s*\(\s*['\"]?(\d+)", blob)
    return go_match.group(1) if go_match else None


def parse_docs(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    docs: dict[str, dict] = {}

    for tr in soup.select("table.workflowTable tbody tr"):
        tds = tr.select("td")
        if len(tds) < 4:
            continue

        sender = tds[2].get_text(strip=True)
        title = tds[3].get_text(strip=True)
        if not sender or not title:
            continue
        if not re.search(r"연차|부서연차", title + sender, re.I):
            continue

        wid = extract_worklist_id(tr, tr.get("onclick") or "")
        key = wid or sender
        docs[key] = {
            "worklistid": wid,
            "title": title,
            "sender": sender,
            "dept": infer_dept(title, sender, IR_TARGET),
        }
    return list(docs.values())


def fetch_inbox(
    session: requests.Session,
    pagetype: str,
    keyword: str = "",
    boxid: str = "",
) -> str:
    params = {
        "pagetype": pagetype,
        "search": "workflowname",
        "conts": keyword,
        "startdate": "2025-07-20",
        "enddate": datetime.now().strftime("%Y-%m-%d"),
        "searchPeriod": "1y",
        "listnum": "50",
    }
    if boxid:
        params["boxid"] = boxid
    url = BASE_URL + "?" + urlencode(params, encoding="utf-8")
    r = session.get(url, timeout=60)
    r.raise_for_status()
    return r.text


def merge_docs(*doc_lists: list[list[dict]]) -> list[dict]:
    merged: dict[str, dict] = {}
    for docs in doc_lists:
        for d in docs:
            key = d.get("worklistid") or d["sender"]
            merged[key] = d
    return sorted(merged.values(), key=lambda x: (x.get("worklistid") or "", x["sender"]), reverse=True)


def main():
    configure_console_encoding()
    if len(sys.argv) < 2:
        print("Usage: sync-approved-from-gw.py <PHPSESSID> [sekey]")
        sys.exit(1)

    target_dir, approved_json = load_paths()
    phpsessid = sys.argv[1]
    sekey = sys.argv[2] if len(sys.argv) > 2 else ""

    session = requests.Session()
    session.cookies.set("PHPSESSID", phpsessid, domain="gw.syu.ac.kr")
    if sekey:
        session.cookies.set("sekey", sekey, domain="gw.syu.ac.kr")
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    all_docs: list[dict] = []
    for kw in GW_SEARCH_KEYWORDS:
        html = fetch_inbox(session, "SCHED", kw, boxid="202")
        found = parse_docs(html)
        print(f"결재할문서함 search '{kw}': {len(found)} docs")
        all_docs = merge_docs(all_docs, found)

    html = fetch_inbox(session, "SENT", "")
    sent_found = parse_docs(html)
    print(f"결재한문서함 (연차 필터): {len(sent_found)} docs")
    all_docs = merge_docs(all_docs, sent_found)

    if approved_json.is_file():
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
        all_docs = merge_docs(all_docs, [])

    target_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for d in all_docs:
        wid = d.get("worklistid")
        sender = d["sender"]
        out_pdf = target_dir / f"{sender}.pdf"
        if out_pdf.exists():
            continue
        if not wid:
            print(f"SKIP download (no worklistid): {sender}")
            continue
        url = f"https://gw.syu.ac.kr/workflow/sign_download_zip.html?worklistid={wid}&PHPSESSID={phpsessid}"
        if sekey:
            url += f"&sekey={quote(sekey, safe='')}"
        r = session.get(url, timeout=60)
        if r.status_code != 200 or not r.content.startswith(b"PK"):
            print(f"FAIL {wid} {sender}: status={r.status_code}")
            continue
        if extract_pdf_from_zip(r.content, str(out_pdf)):
            downloaded.append(sender)
            print(f"OK {sender}.pdf")

    meta = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "결재할문서함·결재한문서함 내부수신 (검색: " + ", ".join(GW_SEARCH_KEYWORDS) + ")",
        "approved": all_docs,
    }
    with approved_json.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    mapped = sum(1 for d in all_docs if d.get("dept"))
    print(f"Total approved: {len(all_docs)}, IR mapped: {mapped}, Downloaded: {len(downloaded)}")
    print(f"Saved: {approved_json}")


if __name__ == "__main__":
    main()
