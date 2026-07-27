# -*- coding: utf-8 -*-
"""Shared dept mapping and submission matching for 연차보고서 checklist."""
from __future__ import annotations

import re
from typing import Iterable

DEPT_FILE_ALIASES: dict[str, list[str]] = {
    "건축・안전관리팀": ["건축안전관리팀", "건축・안전관리", "건축안전"],
    "관재팀": ["시설과 관재", "관재팀"],
    "교목처": ["교목팀", "리더십센터", "리더십"],
    "교육미디어지원팀": ["시설관리팀", "교육미디어지원"],
    "교수학습개발팀": ["교수학습개발센터", "교수학습개발"],
    "커뮤니케이션팀": ["커뮤니케이션"],
    "학사지원팀": ["학사지원"],
}

SENDER_SUBUNIT_TO_DEPT: dict[str, str] = {
    "리더십센터": "교목처",
    "교목팀": "교목처",
    "시설관리팀": "교육미디어지원팀",
    "시설과 관재팀": "관재팀",
    "건축・안전관리팀": "건축・안전관리팀",
    "건축안전관리팀": "건축・안전관리팀",
}

GW_SEARCH_KEYWORDS = ("연차보고서", "연차보고", "부서연차", "부서 연차")


def core_name(name: str) -> str:
    n = re.sub(r"-\d+$", "", name)
    parts = n.split()
    return parts[-1] if parts else n


def infer_dept(title: str, sender: str, ir_departments: Iterable[str]) -> str | None:
    text = f"{title} {sender}"
    depts = sorted(set(ir_departments), key=len, reverse=True)

    for dept in depts:
        if dept in text:
            return dept

    for alias, dept in SENDER_SUBUNIT_TO_DEPT.items():
        if alias in sender or alias in title:
            if dept in depts:
                return dept

    for dept, aliases in DEPT_FILE_ALIASES.items():
        if dept not in depts:
            continue
        for alias in aliases:
            if alias in text:
                return dept

    m = re.search(r"\[([^\]]+)\]", title)
    if m:
        tag = m.group(1)
        for dept in depts:
            if tag in dept or dept in tag:
                return dept

    return None


def match_submitted_for_dept(
    dept: str,
    submitted_files: list[str],
    approved_by_dept: dict[str, list[str]] | None = None,
) -> list[str]:
    approved_by_dept = approved_by_dept or {}
    matches: list[str] = []
    search_terms = [dept] + DEPT_FILE_ALIASES.get(dept, [])

    for file in submitted_files:
        c = core_name(file)
        if any(term in file or c in term or term == c for term in search_terms):
            matches.append(file)

    for sender in approved_by_dept.get(dept, []):
        base = sender[:-4] if sender.lower().endswith(".pdf") else sender
        if base in submitted_files and base not in matches:
            matches.append(base)

    return matches
