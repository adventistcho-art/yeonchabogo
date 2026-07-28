# -*- coding: utf-8 -*-
"""Shared Groupware (gw.syu.ac.kr) session helpers for 연차보고서 automation."""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from bs4 import BeautifulSoup

from submission_utils import GW_SEARCH_KEYWORDS, infer_dept

BASE_INBOX_URL = "https://gw.syu.ac.kr/officialDoc/official_doc_receive_inside.html"
DOCBOX_OFFICIAL_URL = "https://gw.syu.ac.kr/docbox/docBoxOfficialDoc.html"
INTEGRATED_DOCBOX_ID = "3399"
VIEW_URL = "https://gw.syu.ac.kr/officialDoc/official_doc_view.html"
APPROVE_URL = "https://gw.syu.ac.kr/officialDoc/sign_write_process.html"
WORKPATH_URL = "https://gw.syu.ac.kr/workflow/workpathjson.php"

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


def configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def make_session(phpsessid: str, sekey: str = "") -> requests.Session:
    session = requests.Session()
    session.cookies.set("PHPSESSID", phpsessid, domain="gw.syu.ac.kr")
    if sekey:
        session.cookies.set("sekey", sekey, domain="gw.syu.ac.kr")
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


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


def parse_view_link(onclick: str) -> dict[str, str]:
    m = re.search(r"location\.href='([^']+)'", onclick or "")
    if not m:
        m = re.search(r'location\.href="([^"]+)"', onclick or "")
    if not m:
        return {}
    qs = parse_qs(urlparse(m.group(1)).query)
    return {k: v[0] for k, v in qs.items()}


def _row_sender_title(tr) -> tuple[str, str]:
    offi = tr.select_one("span.txtDropOffi")
    if offi:
        sender = offi.get_text(strip=True)
        title_el = tr.select_one("a.workflowName")
        if title_el:
            return sender, title_el.get_text(strip=True) or title_el.get("title", "")
    tds = tr.select("td")
    if len(tds) >= 4:
        return tds[2].get_text(strip=True), tds[3].get_text(strip=True)
    return "", ""


def parse_inbox_docs(html: str, *, title_filter: re.Pattern[str] | None = None, source: str = "") -> list[dict]:
    title_filter = title_filter or re.compile(r"연차|부서연차", re.I)
    soup = BeautifulSoup(html, "html.parser")
    docs: dict[str, dict] = {}

    for tr in soup.select("table.workflowTable tbody tr"):
        tds = tr.select("td")
        if len(tds) < 4:
            continue

        sender, title = _row_sender_title(tr)
        if not sender or not title or not title_filter.search(title + sender):
            continue

        onclick = (tds[3].get("onclick") if len(tds) > 3 else "") or tr.get("onclick") or ""
        view = parse_view_link(onclick)
        wid = extract_worklist_id(tr, tr.get("onclick") or "") or view.get("worklistid")
        key = wid or sender
        docs[key] = {
            "worklistid": wid,
            "workflowid": view.get("workflowid"),
            "targetid": view.get("targetid", "3"),
            "boxid": view.get("boxid", "202"),
            "title": title,
            "sender": sender,
            "dept": infer_dept(title, sender, IR_TARGET),
            "gwSource": source,
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
    url = BASE_INBOX_URL + "?" + urlencode(params, encoding="utf-8")
    r = session.get(url, timeout=60)
    r.raise_for_status()
    return r.text


def fetch_docbox(session: requests.Session, boxid: str, keyword: str = "") -> str:
    params = {
        "boxid": boxid,
        "search": "workflowname",
        "conts": keyword,
        "startdate": "2025-07-20",
        "enddate": datetime.now().strftime("%Y-%m-%d"),
        "searchPeriod": "1y",
        "listnum": "50",
    }
    url = DOCBOX_OFFICIAL_URL + "?" + urlencode(params, encoding="utf-8")
    r = session.get(url, timeout=60)
    r.raise_for_status()
    return r.text


def merge_gw_docs(*doc_lists: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for docs in doc_lists:
        for d in docs:
            key = d.get("worklistid") or d["sender"]
            if key not in merged:
                merged[key] = d
                continue
            prev = merged[key]
            for field in ("worklistid", "workflowid", "dept", "gwSource"):
                if not prev.get(field) and d.get(field):
                    prev[field] = d[field]
            if d.get("gwSource") and prev.get("gwSource") and d["gwSource"] not in prev["gwSource"]:
                prev["gwSource"] = prev["gwSource"] + "+" + d["gwSource"]
    return sorted(merged.values(), key=lambda x: (x.get("worklistid") or "", x["sender"]), reverse=True)


def fetch_yeoncha_docs(session: requests.Session, *, docbox_id: str = INTEGRATED_DOCBOX_ID) -> list[dict]:
    """결재할·결재한 공문 + 통합문서함에서 연차보고서 공문 수집."""
    all_docs: list[dict] = []

    for kw in GW_SEARCH_KEYWORDS:
        html = fetch_inbox(session, "SCHED", kw, boxid="202")
        found = parse_inbox_docs(html, source="결재할문서함")
        all_docs = merge_gw_docs(all_docs, found)

    for kw in GW_SEARCH_KEYWORDS:
        html = fetch_inbox(session, "SENT", kw)
        found = parse_inbox_docs(html, source="결재한문서함")
        all_docs = merge_gw_docs(all_docs, found)

    html = fetch_inbox(session, "SENT", "")
    found = parse_inbox_docs(html, source="결재한문서함")
    all_docs = merge_gw_docs(all_docs, found)

    for kw in GW_SEARCH_KEYWORDS:
        html = fetch_docbox(session, docbox_id, kw)
        found = parse_inbox_docs(html, source="통합문서함")
        all_docs = merge_gw_docs(all_docs, found)

    html = fetch_docbox(session, docbox_id, "")
    found = parse_inbox_docs(html, source="통합문서함")
    all_docs = merge_gw_docs(all_docs, found)

    return all_docs


def download_submission_pdf(
    session: requests.Session,
    worklistid: str,
    out_path: Path,
    *,
    phpsessid: str,
    sekey: str = "",
) -> bool:
    import zipfile
    from io import BytesIO
    from urllib.parse import quote

    url = f"https://gw.syu.ac.kr/workflow/sign_download_zip.html?worklistid={worklistid}&PHPSESSID={phpsessid}"
    if sekey:
        url += f"&sekey={quote(sekey, safe='')}"
    r = session.get(url, timeout=60)
    if r.status_code != 200 or not r.content.startswith(b"PK"):
        return False
    with zipfile.ZipFile(BytesIO(r.content)) as zf:
        pdfs = [n for n in zf.namelist() if n.lower().endswith(".pdf")]
        if not pdfs:
            return False
        with zf.open(pdfs[0]) as src, out_path.open("wb") as dst:
            dst.write(src.read())
    return True


def fetch_pending_yeoncha_docs(session: requests.Session) -> list[dict]:
    merged: dict[str, dict] = {}
    for kw in GW_SEARCH_KEYWORDS:
        html = fetch_inbox(session, "SCHED", kw, boxid="202")
        for doc in parse_inbox_docs(html):
            key = doc.get("worklistid") or doc["sender"]
            merged[key] = doc
    return sorted(merged.values(), key=lambda x: x.get("worklistid") or "", reverse=True)


def parse_form_fields(soup: BeautifulSoup) -> dict[str, str]:
    form = soup.find("form", id="wform")
    if not form:
        raise RuntimeError("wform not found on document view page")
    data: dict[str, str] = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        itype = (inp.get("type") or "text").lower()
        if itype in ("checkbox", "radio"):
            if inp.has_attr("checked"):
                data[name] = inp.get("value", "on")
        else:
            data[name] = inp.get("value", "")
    for ta in form.find_all("textarea"):
        name = ta.get("name")
        if name:
            data[name] = ta.get_text()
    for sel in form.find_all("select"):
        name = sel.get("name")
        if not name:
            continue
        opt = sel.find("option", selected=True) or sel.find("option")
        if opt:
            data[name] = opt.get("value", "")
    return data


def fetch_document_view(
    session: requests.Session,
    *,
    worklistid: str,
    workflowid: str,
    targetid: str = "3",
    boxid: str = "202",
) -> BeautifulSoup:
    url = VIEW_URL + "?" + urlencode(
        {
            "pagetype": "SCHED",
            "boxid": boxid,
            "workflowid": workflowid,
            "worklistid": worklistid,
            "doctype": "",
            "targetid": targetid,
        },
        encoding="utf-8",
    )
    r = session.get(url, timeout=60)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def fetch_workpath(
    session: requests.Session,
    pathgroupid: str,
    worklistid: str,
    workflowid: str,
) -> dict:
    r = session.get(
        WORKPATH_URL,
        params={
            "pathgroupid": pathgroupid,
            "worklistid": worklistid,
            "workflowid": workflowid,
            "pageType": "read",
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def build_workpath_fields(workpath: dict) -> dict[str, str]:
    fields: dict[str, str] = {}
    show = workpath.get("show") or {}
    hidden = workpath.get("hidden") or {}

    def add_items(items: list, signcode: str) -> None:
        for idx, item in enumerate(items):
            if str(item.get("signuse", "1")) == "0":
                continue
            if not item.get("name") and not item.get("userid"):
                continue
            pid = str(item.get("no", idx + 1))
            fields[f"username_{pid}"] = item.get("name", "")
            fields[f"userid_{pid}"] = item.get("userid", "")
            fields[f"jobtitle_{pid}"] = item.get("jobtitle", "")
            fields[f"signuse_{pid}"] = str(item.get("signuse", "1"))
            fields[f"signflag_{pid}"] = str(item.get("signflag", "0"))
            fields[f"blind_{pid}"] = str(item.get("blind", "0"))
            fields[f"edit_{pid}"] = str(item.get("edit", "0"))
            fields[f"signcode_{pid}"] = signcode or item.get("signcode", "")

    for signcode in ("01", "02", "03", "04", "05", "06"):
        if signcode in show:
            add_items(show[signcode], signcode)
        if signcode in hidden:
            add_items(hidden[signcode], signcode)
    return fields


def approve_document(
    session: requests.Session,
    doc: dict,
    *,
    signreason: str = "",
    docboxid: str = "",
) -> tuple[bool, str]:
    worklistid = doc.get("worklistid")
    workflowid = doc.get("workflowid")
    if not worklistid or not workflowid:
        return False, "missing worklistid/workflowid"

    soup = fetch_document_view(
        session,
        worklistid=worklistid,
        workflowid=workflowid,
        targetid=doc.get("targetid", "3"),
        boxid=doc.get("boxid", "202"),
    )
    if not soup.select_one("#signconfirm"):
        return False, "signconfirm button not found (already approved or no permission)"

    fields = parse_form_fields(soup)
    workpath = fetch_workpath(
        session,
        fields.get("pathgroupid", ""),
        worklistid,
        workflowid,
    )
    if workpath.get("ret") != 0:
        return False, f"workpathjson ret={workpath.get('ret')}"

    fields.update(build_workpath_fields(workpath))
    fields["signtype"] = "102"
    fields["signreason"] = signreason
    if docboxid:
        fields["docboxid"] = docboxid
    elif not fields.get("docboxid"):
        selected = soup.select_one("#docboxid option[selected]")
        fields["docboxid"] = selected.get("value", "") if selected else ""

    r = session.post(APPROVE_URL, data=fields, timeout=60, allow_redirects=True)
    body = r.text
    if "sign_write_process.html" in r.url and "sForm" not in body:
        return False, "unexpected response"
    if m := re.search(r"alert\s*\(\s*['\"]([^'\"]+)", body):
        return False, m.group(1)
    return True, "approved"
