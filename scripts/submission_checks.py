# -*- coding: utf-8 -*-
"""Validation rules for submission vs IR performance plan consistency."""
from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

MIN_PLAN_LENGTH = 20
MIN_KOREAN_CHARS_FOR_READABLE_PDF = 50
PLAN_SECTION_MARKERS = (
    "부서연차평가성과관리계획",
    "부서연차평가성과관리계획(안)",
)

PLAN_SECTION_START_RE = re.compile(
    r"부서연차평가\s*성과관리계획\s*(?:\(\s*안\s*\))?",
    re.IGNORECASE,
)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def count_korean_chars(text: str) -> int:
    return len(re.findall(r"[\uac00-\ud7a3]", text or ""))


def pdf_text_is_readable(text: str) -> bool:
    """Detect PDFs where text extraction failed (image/custom font encoding)."""
    if not (text or "").strip():
        return False
    return count_korean_chars(text) >= MIN_KOREAN_CHARS_FOR_READABLE_PDF


def extract_pdf_text(pdf_path: Path) -> str:
    if not pdf_path.is_file():
        return ""
    try:
        reader = PdfReader(str(pdf_path))
        return "".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


def extract_plan_section_from_pdf(pdf_path: Path) -> str | None:
    """Extract 성과관리계획 body text from a submitted 연차보고서25 PDF."""
    if not pdf_path.is_file():
        return None
    text = extract_pdf_text(pdf_path)
    if not pdf_text_is_readable(text):
        return None

    match = None
    for pattern in (
        PLAN_SECTION_START_RE,
        re.compile(r"성과관리계획\s*\(\s*2026", re.IGNORECASE),
    ):
        match = pattern.search(text)
        if match:
            break
    if not match:
        return None

    section = text[match.end() :].strip()
    section = re.split(
        r"\n\s*□\s*부서연차보고|\n\s*□\s*성과지표관리|\n\s*□\s*사업환류",
        section,
        maxsplit=1,
    )[0].strip()
    section = re.sub(r"\n{3,}", "\n\n", section)
    if len(section) < MIN_PLAN_LENGTH:
        return None
    if re.fullmatch(r"[\d.\s]+", section):
        return None
    return section


def pdf_has_plan_section(pdf_path: Path) -> bool | None:
    """Return True/False if readable, None if PDF missing or text unreadable."""
    if not pdf_path.is_file():
        return None
    text = extract_pdf_text(pdf_path)
    if not pdf_text_is_readable(text):
        return None
    norm = normalize_text(text)
    for marker in PLAN_SECTION_MARKERS:
        if marker in norm:
            return True
    if "성과관리계획" in norm:
        return True
    return "부서연차평가" in norm and "성과관리계획" in norm


def plan_meta(plan: str | None) -> dict:
    raw = (plan or "-").strip()
    has_content = raw not in ("", "-")
    is_substantive = (
        has_content
        and len(raw) >= MIN_PLAN_LENGTH
        and not re.fullmatch(r"[\d.\s]+", raw)
    )
    return {
        "raw": raw if has_content else "-",
        "hasContent": has_content,
        "isSubstantive": is_substantive,
    }


def analyze_remarks(
    dept_name: str,
    evaluation: dict,
    submission: dict,
    submission_dir: Path,
) -> list[str]:
    remarks: list[str] = []
    meta = plan_meta(evaluation.get("performancePlan2026"))
    plan_source = (evaluation.get("performancePlan2026Source") or "ir_comment").strip()
    status = submission.get("status")
    files = submission.get("files") or []

    if status == "submitted":
        for f in files:
            pdf_name = f.get("name", "")
            if not pdf_name.lower().endswith(".pdf"):
                continue
            pdf_path = submission_dir / pdf_name
            has_section = pdf_has_plan_section(pdf_path)
            if has_section is False:
                remarks.append(
                    f"제출 PDF({pdf_name})에 '부서연차평가 성과관리계획' 항목이 없음"
                )
            elif has_section is None and not pdf_path.is_file():
                remarks.append(f"제출 PDF({pdf_name}) 파일을 확인할 수 없음")
            elif has_section is None and not meta["isSubstantive"]:
                remarks.append(
                    f"제출 PDF({pdf_name}) 텍스트 자동확인 불가 "
                    "(스캔/이미지 PDF일 수 있음, IR 성과관리계획도 없음)"
                )

        if meta["hasContent"] and not meta["isSubstantive"]:
            remarks.append(
                f"IR 성과관리계획(2026) 내용이 비정상적으로 짧음 ('{meta['raw']}')"
            )
        elif not meta["hasContent"]:
            if plan_source == "submission_pdf":
                pass
            else:
                remarks.append("공문 제출했으나 IR 성과관리계획(2026) 미입력")
        elif plan_source == "submission_pdf" and meta["isSubstantive"]:
            pass

    elif status == "not_submitted":
        if meta["isSubstantive"]:
            remarks.append(
                "미제출인데 IR 성과관리계획(2026)에 실질 내용이 입력되어 있음 "
                "(보기 버튼과 제출 상태 불일치)"
            )
        elif meta["hasContent"] and not meta["isSubstantive"]:
            remarks.append(
                f"미제출인데 IR 성과관리계획(2026)에 '{meta['raw']}'만 입력됨 "
                "(실질 내용 없음, 보기 버튼 활성화는 IR 데이터 오류로 보임)"
            )

    return remarks
