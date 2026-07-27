# -*- coding: utf-8 -*-
"""Merge groupware submission status into IR report data."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from submission_checks import analyze_remarks, plan_meta
from submission_utils import infer_dept, match_submitted_for_dept

DEPT_CONTACTS: dict[str, dict[str, str]] = {
    "IR센터": {"name": "정진수", "email": "positive@syu.ac.kr"},
    "SUPREME센터": {"name": "최정원", "email": "asokiu@syu.ac.kr"},
    "건축・안전관리팀": {"name": "김진현", "email": "kjh@syu.ac.kr"},
    "경영대학원(교학)": {"name": "김영글", "email": "jamie@syu.ac.kr"},
    "공통기기실험실": {"name": "이성언", "email": "selee@syu.ac.kr"},
    "교수지원": {"name": "손희은", "email": "heeny@syu.ac.kr"},
    "교수학습개발팀": {"name": "조유상", "email": "choyoosang@syu.ac.kr"},
    "교양교육원": {"name": "이성희", "email": "hiyi1212@syu.ac.kr"},
    "교원인사": {"name": "손희은", "email": "heeny@syu.ac.kr"},
    "교육미디어지원팀": {"name": "유영상", "email": "yooys@syu.ac.kr"},
    "국제교육원": {"name": "김두한", "email": "doohk@syu.ac.kr"},
    "글로컬사회혁신원": {"name": "심은하", "email": "shimeh@syu.ac.kr"},
    "금연금주클리닉": {"name": "김진현", "email": "k.jhyeon@syu.ac.kr"},
    "기획처": {"name": "조재림", "email": "adventistcho@syu.ac.kr"},
    "대외국제처": {"name": "김두한", "email": "doohk@syu.ac.kr"},
    "부속실": {"name": "김성희", "email": "kimsh@syu.ac.kr"},
    "비교과통합센터": {"name": "조유상", "email": "choyoosang@syu.ac.kr"},
    "생활교육원": {"name": "최정환", "email": "cjh629@syu.ac.kr"},
    "소프트웨어중심대학사업단": {"name": "문효석", "email": "hseok@syu.ac.kr"},
    "신학대학원(교학)": {"name": "김영글", "email": "jamie@syu.ac.kr"},
    "원격교육지원센터": {"name": "박성도", "email": "nicepsd@syu.ac.kr"},
    "인성교육원": {"name": "황수민", "email": "8603sm@syu.ac.kr"},
    "일반대학원(교학)": {"name": "김영글", "email": "jamie@syu.ac.kr"},
    "임상간호대학원(교학)": {"name": "김영글", "email": "jamie@syu.ac.kr"},
    "입학관리본부": {"name": "김원구", "email": "kwg8917@syu.ac.kr"},
    "전기통신팀": {"name": "권현섭", "email": "khs84@syu.ac.kr"},
    "조경미화팀": {"name": "전규성", "email": "jks7328@syu.ac.kr"},
    "창업교육센터": {"name": "조재성", "email": "xchoz@syu.ac.kr"},
    "체육문화센터": {"name": "한영민", "email": "socks@syu.ac.kr"},
    "최고경영자과정": {"name": "송낙준", "email": "jun@syu.ac.kr"},
    "취업진로지원센터": {"name": "신수미", "email": "ssm@syu.ac.kr"},
    "콘서바토리": {"name": "황수민", "email": "8603sm@syu.ac.kr"},
    "평생교육원": {"name": "김논중", "email": "nonjoong@syu.ac.kr"},
}


def _file_href(path: Path) -> str:
    if path.exists():
        return path.resolve().as_uri()
    return ""


def _load_approved(
    submission_dir: Path,
    dept_names: list[str],
) -> tuple[dict[str, Any], list[dict], dict[str, list[str]]]:
    approved_json = submission_dir / "approved_submissions.json"
    meta: dict[str, Any] = {"approved": [], "updated": "-", "source": "-"}
    approved_list: list[dict] = []
    approved_by_dept: dict[str, list[str]] = {}

    if not approved_json.is_file():
        return meta, approved_list, approved_by_dept

    with approved_json.open(encoding="utf-8") as f:
        meta = json.load(f)

    for item in meta.get("approved", []):
        sender = item.get("sender", "")
        dept = item.get("dept") or infer_dept(item.get("title", ""), sender, dept_names)
        pdf_path = submission_dir / f"{sender}.pdf"
        enriched = {
            **item,
            "dept": dept,
            "hasPdf": pdf_path.is_file(),
            "pdfHref": _file_href(pdf_path),
        }
        approved_list.append(enriched)
        if dept:
            approved_by_dept.setdefault(dept, []).append(sender)

    return meta, approved_list, approved_by_dept


def merge_submission_into_report(report: dict, cfg: dict) -> dict:
    submission_dir = Path(cfg["paths"]["submissionDir"])
    ir_pdf_root = Path(cfg["paths"]["irPdfRoot"])

    dept_names = [d["name"] for d in report.get("departments", [])]
    submitted_files = [
        os.path.splitext(f)[0]
        for f in os.listdir(submission_dir)
        if f.lower().endswith(".pdf")
    ] if submission_dir.is_dir() else []

    approved_meta, approved_docs, approved_by_dept = _load_approved(submission_dir, dept_names)

    submitted_count = 0
    for dept in report.get("departments", []):
        name = dept["name"]
        matches = match_submitted_for_dept(name, submitted_files, approved_by_dept)
        files = []
        for base in sorted(matches):
            pdf_path = submission_dir / f"{base}.pdf"
            files.append({
                "name": f"{base}.pdf",
                "href": _file_href(pdf_path),
            })

        contact = DEPT_CONTACTS.get(name, {})
        status = "submitted" if matches else "not_submitted"
        if status == "submitted":
            submitted_count += 1

        submission = {
            "status": status,
            "files": files,
            "contact": {
                "name": contact.get("name", ""),
                "email": contact.get("email", ""),
            },
        }
        remarks = analyze_remarks(name, dept.get("evaluation", {}), submission, submission_dir)
        submission["remarks"] = remarks
        submission["hasAnomaly"] = len(remarks) > 0
        if files:
            submission["annualReport2025PdfHref"] = files[0].get("href", "")
        else:
            submission["annualReport2025PdfHref"] = ""
        dept["submission"] = submission

        annual_rel = dept.get("annualReport2024PdfPath")
        if annual_rel:
            annual_full = ir_pdf_root / annual_rel.replace("/", os.sep)
            dept["annualReport2024PdfHref"] = _file_href(annual_full)
        else:
            dept["annualReport2024PdfHref"] = ""

        pm = plan_meta(dept.get("evaluation", {}).get("performancePlan2026"))
        dept.setdefault("evaluation", {})["performancePlan2026Meta"] = pm

        for project in dept.get("projects", []):
            for key in ("planHtmlPath", "plan2026HtmlPath", "resultHtmlPath", "pdfPath"):
                rel = project.get(key)
                if not rel:
                    continue
                full = ir_pdf_root / rel.replace("/", os.sep)
                href = _file_href(full)
                if href:
                    project[key] = href

    report["submissionMeta"] = {
        "updated": approved_meta.get("updated", "-"),
        "source": approved_meta.get("source", "-"),
        "submissionDir": str(submission_dir),
        "submittedCount": submitted_count,
        "notSubmittedCount": len(dept_names) - submitted_count,
        "approvedCount": len(approved_docs),
        "approvedPdfCount": sum(1 for d in approved_docs if d.get("hasPdf")),
        "anomalyCount": sum(
            1 for d in report.get("departments", []) if d.get("submission", {}).get("hasAnomaly")
        ),
    }
    report["approvedDocuments"] = sorted(approved_docs, key=lambda x: x.get("sender", ""))
    return report
