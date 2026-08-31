# -*- coding: utf-8 -*-
"""Validate the generated annual-evaluation HTML/PDF compilation."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_MARKER = '<script id="report-data" type="application/json">'
DISPLAY_NAMES = {
    "총무과": "총무인사팀",
    "대외국제처": "대외협력팀",
    "인성교육원": "리더십센터",
    "부속실": "부속팀",
}
EXCLUDED_DEPTS = {"예산팀", "구매팀"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="부서연차평가 합본 검증")
    parser.add_argument("--index", type=Path, default=ROOT / "dashboard.html")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("--pdf", type=Path, default=None, help="검증할 PDF 경로")
    return parser.parse_args()


def embedded_report(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    start = text.index(REPORT_MARKER) + len(REPORT_MARKER)
    end = text.index("</script>", start)
    return json.loads(text[start:end])


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> None:
    args = parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    source = embedded_report(args.index)
    year = int(source.get("year") or 2025)
    stem = f"{year}학년도_부서연차평가_보고서_합본"
    report_dir = args.report_dir.resolve()
    html_path = report_dir / f"{stem}.html"
    pdf_path = args.pdf.resolve() if args.pdf else report_dir / f"{stem}.pdf"
    audit_path = report_dir / f"{stem}_데이터검증.json"
    validation_path = report_dir / f"{stem}_출력검증.json"

    failures: list[str] = []
    warnings: list[str] = []
    department_names = [
        d.get("name", "")
        for d in source.get("departments", [])
        if d.get("name", "") not in EXCLUDED_DEPTS
    ]
    display_names = [DISPLAY_NAMES.get(name, name) for name in department_names]

    check(html_path.is_file(), f"HTML 없음: {html_path}", failures)
    check(pdf_path.is_file(), f"PDF 없음: {pdf_path}", failures)
    check(audit_path.is_file(), f"데이터 검증 JSON 없음: {audit_path}", failures)

    html_text = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""
    section_count = html_text.count('class="department-section"')
    check(
        section_count == len(department_names),
        f"부서 섹션 수 불일치: {section_count}/{len(department_names)}",
        failures,
    )
    org = json.loads((ROOT / "data" / "dept_parents.json").read_text(encoding="utf-8"))
    configured_order = org.get("departmentOrder") or []
    expected_order = [name for name in configured_order if name in department_names]
    actual_order = re.findall(
        r'<section class="department-section" data-dept="([^"]+)"',
        html_text,
    )
    check(
        len(expected_order) == len(department_names),
        "전화번호부 기준 부서 순서에 일부 부서가 누락됨",
        failures,
    )
    check(
        actual_order == expected_order,
        "부서별 보고서 순서가 전화번호부 기준과 일치하지 않음",
        failures,
    )
    for source_name in department_names:
        marker = f'data-dept="{source_name}"'
        check(html_text.count(marker) == 1, f"HTML 부서 누락/중복: {source_name}", failures)
        toc_marker = f'data-toc-dept="{source_name}"'
        check(
            html_text.count(toc_marker) == 1,
            f"부서별 연차보고서 목차 누락/중복: {source_name}",
            failures,
        )
    divider_pos = html_text.find('<section class="department-divider">')
    detail_toc_pos = html_text.find('<section class="department-toc-section">')
    first_dept_pos = html_text.find('<section class="department-section"')
    feedback_pos = html_text.find('<section class="feedback-summary-section">')
    check(
        -1 not in (feedback_pos, divider_pos, detail_toc_pos, first_dept_pos)
        and feedback_pos < divider_pos < detail_toc_pos < first_dept_pos,
        "환류 내역 이후 간지·부서 목차·부서별 보고서 순서가 잘못됨",
        failures,
    )
    check(
        "<h1>부서별 연차보고서</h1>" in html_text
        and "부서별 연차보고서 목차" in html_text,
        "부서별 연차보고서 간지 또는 목차 제목이 누락됨",
        failures,
    )
    check("<thead>" in html_text, "반복 표 머리글이 없음", failures)
    check("@page { size: A4;" in html_text, "A4 인쇄 규칙이 없음", failures)
    check(
        not re.search(r"해당없음\s*→\s*해당없음", html_text),
        "사업이행률의 해당없음 → 해당없음 표기가 축약되지 않음",
        failures,
    )
    check(
        html_text.count('class="rate-meta"') >= len(department_names) * 2,
        "요약표 또는 부서실적에 항례·성과 사업 건수 설명이 누락됨",
        failures,
    )
    check(
        not re.search(
            r'<tr><td>[^<]*</td><td class="project-name">.*?</td><td>[^<]*</td>'
            r'<td class="num">자료없음</td>',
            html_text,
            re.S,
        ),
        "세부실적표에 예산이 자료없음인 사업이 남아 있음",
        failures,
    )
    check(
        html_text.count('class="calculation-note"') >= len(department_names) + 1,
        "요약표 또는 부서실적 위에 평가 산정 기준이 누락됨",
        failures,
    )
    feedback_summary_html = html_text.split("부서별 연간 환류 내역", 1)[-1].split(
        "</section>", 1
    )[0]
    check(
        "각 부서가 직접 작성·제출한 내용을 기반으로 하며" in feedback_summary_html
        and "문체와 구조만 정리함" in feedback_summary_html,
        "부서별 연간 환류 내역의 작성 주체 안내문이 누락됨",
        failures,
    )
    check(
        "…" not in feedback_summary_html,
        "부서별 연간 환류 내역에 잘린 문장(…)이 남아 있음",
        failures,
    )
    check(
        feedback_summary_html.count('class="feedback-content ') >= len(department_names),
        "부서별 연간 환류 내역의 구조화 블록이 누락됨",
        failures,
    )
    check(
        all(
            label in feedback_summary_html
            for label in ("운영 결과", "취약요인", "개선계획", "연간 환류 내용")
        ),
        "환류 내역의 내용별 구분 표지가 누락됨",
        failures,
    )
    check(
        not re.search(
            r"(?:습니다|합니다|됩니다|하였다|한다|있다|필요하다|높인다|보인다)"
            r"\s*[.!?]",
            feedback_summary_html,
        ),
        "환류 내역에 간결체로 변환되지 않은 문장 종결이 남아 있음",
        failures,
    )
    check(
        feedback_summary_html.count("게스트하우스 운영 활성화") <= 1,
        "부속실 게스트하우스 환류 문구가 다른 부서에 중복 배정됨",
        failures,
    )
    for dept_name in ("입학처",):
        row_match = re.search(
            rf"<tr>(?:(?!</tr>).)*<td>{re.escape(dept_name)}</td>"
            rf"(?:(?!</tr>).)*</tr>",
            feedback_summary_html,
            re.S,
        )
        check(row_match is not None, f"환류 내역 행 누락: {dept_name}", failures)
        check(
            not row_match or "게스트하우스 운영 활성화" not in row_match.group(0),
            f"{dept_name}에 부속실 환류 문구가 잘못 배정됨",
            failures,
        )
    check(
        "사업이행률 = 성과관리사업별 이행률 합계 ÷ 성과관리사업 수" in html_text
        and "종합평균 = (IR 예산집행률 + IR 사업이행률) ÷ 2"
        in html_text
        and "95 이상 A+ · 85 이상 A · 75 이상 B+ · 65 이상 B · 55 이상 C · 55 미만 D"
        in html_text,
        "사업이행률·종합평균·종합등급 산식이 누락됨",
        failures,
    )
    check(
        bool(
            re.search(
                r'<section class="department-section" data-dept="교목처".*?'
                r"<th>사업이행률</th>.*?<td class=\"num\">해당없음</td>",
                html_text,
                re.S,
            )
        ),
        "교목처 사업이행률이 최종 발간 PDF 확정값 해당없음으로 표시되지 않음",
        failures,
    )
    check(
        "99.82%" in html_text,
        "시설관리팀 평가 의견의 교육미디어지원팀 예산집행률 99.82%가 반영되지 않음",
        failures,
    )
    check(
        "377,220" in html_text,
        "교육미디어지원팀 확정 조정예산 377,220천원이 반영되지 않음",
        failures,
    )
    check(
        "총무인사팀</td><td class=\"num\">4,177,650</td>" in html_text,
        "총무인사팀 2025 조정예산이 반영되지 않음",
        failures,
    )
    personnel_section = re.search(
        r'<section class="department-section" data-dept="총무과">(.*?)</section>',
        html_text,
        re.S,
    )
    personnel_html = personnel_section.group(1) if personnel_section else ""
    check(
        "법정부담금(총무과)" in personnel_html
        and "3,559,000,000" in personnel_html
        and "93.18%" in personnel_html,
        "총무인사팀 세부실적의 사업별 예산·집행률이 반영되지 않음",
        failures,
    )
    check(
        "96.36% → 92.8%" in html_text and "A+ → D" in html_text,
        "총무인사팀 2025 종합등급 산식 결과가 반영되지 않음",
        failures,
    )
    check(
        bool(
            re.search(
                r'rowspan="3" class="group-cell">기획처</td>.*?대학혁신지원사업단'
                r'.*?rowspan="6" class="group-cell">사무처</td>.*?조경미화팀',
                html_text,
                re.S,
            )
        ),
        "요약표에서 기획처·사무처 행 순서 또는 병합 범위가 잘못됨",
        failures,
    )
    for dept_name, parent in (("예산팀", "기획처"), ("구매팀", "재무처")):
        check(
            f'data-dept="{dept_name}"' not in html_text
            and f'data-toc-dept="{dept_name}"' not in html_text
            and not re.search(rf'class="dept-cell">{re.escape(dept_name)}<', html_text)
            and not re.search(
                rf"<strong>{re.escape(parent)}</strong><span>[^<]*{re.escape(dept_name)}",
                html_text,
            ),
            f"{dept_name}이 부서연차평가 보고서에 남아 있음",
            failures,
        )
    expected_group_members = {
        "기획처": ["IR센터", "대학혁신지원사업단"],
        "교육혁신원": ["SUPREME센터"],
        "연구처": ["공통기기실험실"],
        "교무처": ["교양교육원"],
        "평생교육원": ["노원어린이영어교실", "평생교육원", "체육문화센터"],
        "대학원": ["최고경영자과정"],
        "입학처": ["입학처"],
        "국제처": ["국제처"],
        "대학일자리본부": ["스타트업지원센터"],
    }
    for group, members in expected_group_members.items():
        toc_match = re.search(
            rf"<strong>{re.escape(group)}</strong><span>([^<]*)</span>",
            html_text,
        )
        check(toc_match is not None, f"목차 구분 누락: {group}", failures)
        toc_members = toc_match.group(1) if toc_match else ""
        for member in members:
            check(
                member in toc_members,
                f"{member}이(가) {group} 산하로 표시되지 않음",
                failures,
            )
    for source_name, report_name in {
        "창업교육센터": "스타트업지원센터",
        "국제교육원": "국제처",
        "입학관리본부": "입학처",
    }.items():
        check(
            bool(
                re.search(
                    rf'data-dept="{re.escape(source_name)}".*?'
                    rf"<h2>{re.escape(report_name)} 연차보고서</h2>",
                    html_text,
                    re.S,
                )
            ),
            f"보고서 명칭 변환 누락: {source_name} → {report_name}",
            failures,
        )

    pdf_page_count = 0
    blank_pages: list[int] = []
    sample_hits: dict[str, bool] = {}
    a4_page_count = 0
    if pdf_path.is_file():
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdf_path))
            pdf_page_count = len(reader.pages)
            check(pdf_page_count >= len(department_names) + 2, "PDF 페이지 수가 비정상적으로 적음", failures)

            extracted: list[str] = []
            for idx, page in enumerate(reader.pages):
                text = (page.extract_text() or "").strip()
                extracted.append(text)
                if len(re.sub(r"\s+", "", text)) < 4:
                    blank_pages.append(idx + 1)
                width_mm = float(page.mediabox.width) * 25.4 / 72
                height_mm = float(page.mediabox.height) * 25.4 / 72
                if abs(width_mm - 210) < 2 and abs(height_mm - 297) < 2:
                    a4_page_count += 1

            all_text = "\n".join(extracted)
            for name in ("총무인사팀", "교육미디어지원팀", "기획처", "일반대학원(교학)"):
                sample_hits[name] = name in all_text
                check(sample_hits[name], f"PDF 표본 부서명 누락: {name}", failures)

            check(a4_page_count == pdf_page_count, "A4가 아닌 PDF 페이지가 있음", failures)
            if blank_pages:
                warnings.append(f"텍스트가 거의 없는 페이지: {blank_pages}")
        except ImportError:
            warnings.append("pypdf가 없어 PDF 내용 검증을 건너뜀")
        except Exception as exc:  # pragma: no cover - diagnostic boundary
            failures.append(f"PDF 검증 오류: {exc}")

    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.is_file() else {}
    check(
        audit.get("departmentCount") == len(department_names),
        "audit 부서 수 불일치",
        failures,
    )
    check(
        (audit.get("coverage") or {}).get("previousYearGrade", 0) > 0,
        "2024 확정 종합등급이 연결되지 않음",
        failures,
    )

    result = {
        "ok": not failures,
        "sourceDepartmentCount": len(department_names),
        "htmlDepartmentSectionCount": section_count,
        "pdfPageCount": pdf_page_count,
        "pdfSizeBytes": pdf_path.stat().st_size if pdf_path.is_file() else 0,
        "a4PageCount": a4_page_count,
        "blankPages": blank_pages,
        "sampleDepartmentHits": sample_hits,
        "failures": failures,
        "warnings": warnings,
    }
    validation_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Validation: {validation_path}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
