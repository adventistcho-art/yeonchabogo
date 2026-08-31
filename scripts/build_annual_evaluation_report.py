# -*- coding: utf-8 -*-
"""Build the formal department annual-evaluation HTML/PDF compilation.

The report is generated from the JSON embedded in dashboard.html. Historical
performance snapshots are optional: when unavailable, current-year content is
still produced and missing comparison values are recorded in the audit file.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "dashboard.html"
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
ORG_PATH = ROOT / "data" / "dept_parents.json"
CURRENT_OVERRIDES_PATH = ROOT / "data" / "annual_evaluation_overrides.json"
FINALIZED_2024_OVERRIDES_PATH = ROOT / "data" / "finalized_2024_overrides.json"
CURRENT_BUDGET_EXEC_PATH = ROOT / "data" / "budget_exec_2025.json"
DEFAULT_OUTPUT_DIR = ROOT / "reports"
REPORT_MARKER = '<script id="report-data" type="application/json">'
# 자료 미제출·해당없음 부서는 발간 합본에서 빼 둔다.
EXCLUDED_DEPTS = {"예산팀", "구매팀"}
PLAN_TEXT_OWNER_HINTS = {
    "게스트하우스 운영 활성화": "부속실",
}
FINALIZED_HISTORY_FILES = {
    2024: Path(r"F:\기획평가\2025\2024연차보고\2024부서별데이터.xlsx"),
}

# Report names stay faithful to the current organization while source lookup
# continues to use the names stored by IR.
DISPLAY_NAMES = {
    "총무과": "총무인사팀",
    "대외국제처": "대외협력팀",
    "인성교육원": "리더십센터",
    "부속실": "부속팀",
    "창업교육센터": "스타트업지원센터",
    "국제교육원": "국제처",
    "입학관리본부": "입학처",
}

PERF_LOOKUP_ALIASES = {
    "인성교육원": ("인성교육원", "리더십센터"),
    "부속실": ("부속실", "부속팀"),
    "대외국제처": ("대외국제처", "대외협력팀", "대외협력처"),
    "교육미디어지원팀": ("교육미디어지원팀", "시설관리팀"),
    "교수지원": ("교수지원", "교수지원팀"),
    "건축・안전관리팀": ("건축・안전관리팀", "건축·안전관리팀", "건축안전관리팀"),
    "총무과": ("총무과", "총무인사팀", "인사총무팀"),
}

FINALIZED_LOOKUP_ALIASES = {
    "총무과": "총무인사팀",
    "대외국제처": "대외협력팀",
    "인성교육원": "인성교육원",
    "건축・안전관리팀": "건축·안전관리팀",
    "창업교육센터": "스타트업지원센터",
    "소프트웨어중심대학사업단": "소프트웨어중심사업단",
    "입학관리본부": "입학처",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="부서별 연차평가 합본 HTML/PDF 생성")
    parser.add_argument("--index", type=Path, default=INDEX_PATH, help="데이터가 embed된 dashboard.html")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="HTML/PDF/검증 파일 출력 폴더",
    )
    parser.add_argument("--html-only", action="store_true", help="PDF를 만들지 않고 HTML만 생성")
    return parser.parse_args()


def read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def load_embedded_report(index_path: Path) -> dict:
    text = index_path.read_text(encoding="utf-8")
    if REPORT_MARKER not in text:
        raise RuntimeError(f"report-data marker not found: {index_path}")
    start = text.index(REPORT_MARKER) + len(REPORT_MARKER)
    end = text.index("</script>", start)
    return json.loads(text[start:end])


def load_config() -> dict:
    return read_json(CONFIG_PATH, {})


def load_perf_snapshot(config: dict, year: int) -> dict[str, dict]:
    raw_path = (config.get("paths", {}).get("perfSnapshots") or {}).get(str(year))
    if not raw_path:
        return {}
    rows = read_json(Path(raw_path), [])
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("budgOrgnNm") or row.get("deptNm") or "").strip(): row
        for row in rows
        if row.get("budgOrgnNm") or row.get("deptNm")
    }


def lookup_perf(perf_map: dict[str, dict], dept_name: str) -> dict | None:
    candidates = PERF_LOOKUP_ALIASES.get(dept_name, (dept_name,))
    for candidate in candidates:
        if candidate in perf_map:
            return perf_map[candidate]
    return None


def parse_grade_rate(value: Any) -> tuple[str | None, float | None, bool]:
    text = str(value or "").strip()
    if not text or text == "해당없음":
        return None, None, False
    match = re.match(r"\s*([^()]+?)(?:\(([-\d,.]+)%\))?\s*$", text)
    if not match:
        return text, None, True
    grade = match.group(1).strip() or None
    rate = parse_number(match.group(2))
    return grade, rate, True


def load_finalized_history(year: int) -> dict[str, dict]:
    path = FINALIZED_HISTORY_FILES.get(year)
    if not path or not path.is_file():
        return {}
    try:
        import openpyxl
    except ImportError:
        return {}

    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheet = workbook.active
    rows: dict[str, dict] = {}
    for index, values in enumerate(sheet.iter_rows(values_only=True)):
        if index == 0:
            continue
        parent, name, budget_thousands, budget_value, project_value, total_grade = values[:6]
        if not name:
            continue
        budget_grade, budget_rate, _ = parse_grade_rate(budget_value)
        project_grade, project_rate, project_applicable = parse_grade_rate(project_value)
        rows[str(name).strip()] = {
            "parent": str(parent or "").strip(),
            "adjustedBudget": (
                float(budget_thousands) * 1000 if budget_thousands is not None else None
            ),
            "budgetExecRate": budget_rate,
            "budgetGrade": budget_grade,
            "projectExecRate": project_rate,
            "projectGrade": project_grade,
            "projectApplicable": project_applicable,
            "totalGrade": str(total_grade or "").strip() or None,
            "source": str(path),
        }
    workbook.close()
    if year == 2024:
        overrides = read_json(FINALIZED_2024_OVERRIDES_PATH, {})
        for name, values in overrides.items():
            if name.startswith("_") or not isinstance(values, dict):
                continue
            rows.setdefault(name, {}).update(values)
            rows[name]["source"] = str(FINALIZED_2024_OVERRIDES_PATH)
    return rows


def lookup_finalized(history: dict[str, dict], dept_name: str) -> dict | None:
    lookup_name = FINALIZED_LOOKUP_ALIASES.get(dept_name, dept_name)
    return history.get(lookup_name)


def lookup_current_budget(rows: dict[str, dict], dept_name: str) -> dict:
    aliases = PERF_LOOKUP_ALIASES.get(dept_name, (dept_name,))
    for alias in aliases:
        if alias in rows:
            return rows[alias]
    return {}


def clean_text(value: Any, fallback: str = "자료없음") -> str:
    if value is None:
        return fallback
    text = re.sub(r"\r\n?", "\n", str(value)).strip()
    return text if text and text not in {"-", "None", "null"} else fallback


def parse_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?[\d,.]+", str(value))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def format_money(value: Any, *, thousands: bool = False) -> str:
    number = parse_number(value)
    if number is None:
        return "자료없음"
    if thousands:
        number /= 1000
    return f"{number:,.0f}"


def format_rate(value: Any) -> str:
    number = parse_number(value)
    if number is None:
        return "해당없음"
    return f"{number:.2f}".rstrip("0").rstrip(".") + "%"


def transition(
    previous: Any,
    current: Any,
    *,
    previous_applicable: bool | None = None,
    current_applicable: bool | None = None,
) -> str:
    prev_num = parse_number(previous)
    curr_num = parse_number(current)
    prev_label = (
        "해당없음"
        if previous_applicable is False
        else ("자료없음" if prev_num is None else format_rate(prev_num))
    )
    curr_label = (
        "해당없음"
        if current_applicable is False
        else ("해당없음" if curr_num is None else format_rate(curr_num))
    )
    if prev_num is None or curr_num is None:
        if prev_label == "해당없음" and curr_label == "해당없음":
            return "해당없음"
        return f"{prev_label} → {curr_label}"
    delta = curr_num - prev_num
    sign = "+" if delta >= 0 else ""
    return f"{format_rate(prev_num)} → {format_rate(curr_num)} ({sign}{delta:.2f}%p)"


def grade_transition(previous: Any, current: Any) -> str:
    prev_text = clean_text(previous)
    curr_text = clean_text(current)
    if prev_text == "자료없음" and curr_text == "자료없음":
        return "자료없음"
    return f"{prev_text} → {curr_text}"


def total_grade_from_average(value: Any) -> str | None:
    score = parse_number(value)
    if score is None:
        return None
    if score >= 95:
        return "A+"
    if score >= 85:
        return "A"
    if score >= 75:
        return "B+"
    if score >= 65:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def text_block(value: Any, fallback: str = "자료없음") -> str:
    return esc(clean_text(value, fallback)).replace("\n", "<br>")


def compact_text(value: Any, limit: int | None = 180) -> str:
    text = re.sub(r"\s+", " ", clean_text(value)).strip()
    if limit is None or len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def concise_korean_style(value: Any) -> str:
    text = clean_text(value)
    boundary = r"(?=\s*[.!?]|$)"
    replacements = [
        (rf"([가-힣]+)하고자\s+한다{boundary}", r"\1하고자 함"),
        (rf"([가-힣]+)할\s+예정이다{boundary}", r"\1할 예정임"),
        (rf"([가-힣]+)하였습니다{boundary}", r"\1함"),
        (rf"([가-힣]+)하였음{boundary}", r"\1함"),
        (rf"([가-힣]+)하였다{boundary}", r"\1함"),
        (rf"([가-힣]+)했습니다{boundary}", r"\1함"),
        (rf"([가-힣]+)했다{boundary}", r"\1함"),
        (rf"([가-힣]+)합니다{boundary}", r"\1함"),
        (rf"([가-힣]+)한다{boundary}", r"\1함"),
        (rf"([가-힣]+)하겠습니다{boundary}", r"\1하겠음"),
        (rf"([가-힣]+)겠습니다{boundary}", r"\1겠음"),
        (rf"([가-힣]+)되었습니다{boundary}", r"\1됨"),
        (rf"([가-힣]+)되었다{boundary}", r"\1됨"),
        (rf"([가-힣]+)됩니다{boundary}", r"\1됨"),
        (rf"([가-힣]+)된다{boundary}", r"\1됨"),
        (rf"([가-힣]+)시켰다{boundary}", r"\1시킴"),
        (rf"([가-힣]+)냈다{boundary}", r"\1냄"),
        (rf"([가-힣]+)높인다{boundary}", r"\1높임"),
        (rf"([가-힣]+)보인다{boundary}", r"\1보임"),
        (rf"([가-힣]+)이었다{boundary}", r"\1이었음"),
        (rf"([가-힣]+)입니다{boundary}", r"\1임"),
        (rf"([가-힣]+)이다{boundary}", r"\1임"),
        (rf"있었습니다{boundary}", "있었음"),
        (rf"있습니다{boundary}", "있음"),
        (rf"있었다{boundary}", "있었음"),
        (rf"있다{boundary}", "있음"),
        (rf"없었습니다{boundary}", "없었음"),
        (rf"없습니다{boundary}", "없음"),
        (rf"없었다{boundary}", "없었음"),
        (rf"없다{boundary}", "없음"),
        (rf"필요하다{boundary}", "필요함"),
        (rf"어렵다{boundary}", "어려움"),
        (rf"같습니다{boundary}", "같음"),
        (rf"않다{boundary}", "않음"),
        (rf"한다{boundary}", "함"),
        (rf"높인다{boundary}", "높임"),
        (rf"보인다{boundary}", "보임"),
        (rf"됩니다{boundary}", "됨"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    return text


def display_name(name: str) -> str:
    return DISPLAY_NAMES.get(name, name)


def sorted_departments(report: dict, org: dict) -> list[dict]:
    group_order = org.get("groupOrder") or []
    department_order = org.get("departmentOrder") or []
    parents = org.get("parents") or {}
    group_index = {name: idx for idx, name in enumerate(group_order)}
    department_index = {name: idx for idx, name in enumerate(department_order)}

    def sort_key(dept: dict) -> tuple[int, int, str]:
        name = dept.get("name", "")
        parent = parents.get(name, "기타")
        return (
            group_index.get(parent, 999),
            department_index.get(name, 999),
            display_name(name),
        )

    return sorted(report.get("departments", []), key=sort_key)


def normalize_departments(
    report: dict,
    org: dict,
    perf_previous: dict[str, dict],
    finalized_previous: dict[str, dict],
    current_overrides: dict[str, dict],
    current_budget_rows: dict[str, dict],
    current_report_rows: dict[str, dict],
) -> list[dict]:
    parents = org.get("parents") or {}
    plan_text_counts = Counter(
        str((dept.get("evaluation") or {}).get("performancePlan2026") or "").strip()
        for dept in report.get("departments", [])
        if str((dept.get("evaluation") or {}).get("performancePlan2026") or "").strip()
        not in {"", "-"}
    )
    normalized: list[dict] = []
    for source in sorted_departments(report, org):
        name = source.get("name", "")
        if name in EXCLUDED_DEPTS:
            continue
        raw_current = current_report_rows.get(name) or {}
        performance = source.get("performance") or {}
        evaluation = source.get("evaluation") or {}
        summary = source.get("summary") or {}
        use_raw_current = (
            performance.get("adjustedBudget") is None
            and (raw_current.get("performance") or {}).get("adjustedBudget") is not None
        )
        if use_raw_current:
            performance = raw_current.get("performance") or performance
            raw_evaluation = raw_current.get("evaluation") or {}
            current_plan = evaluation.get("performancePlan2026")
            evaluation = {**evaluation, **raw_evaluation}
            if current_plan not in (None, "", "-"):
                evaluation["performancePlan2026"] = current_plan
            summary = raw_current.get("summary") or summary
        finalized = lookup_finalized(finalized_previous, name) or {}
        previous = lookup_perf(perf_previous, name) or {}
        current_budget = lookup_current_budget(current_budget_rows, name)
        source_projects = (
            raw_current.get("projects") or []
            if use_raw_current
            else source.get("projects") or []
        )
        source_feedback = (
            raw_current.get("feedback") or source.get("feedback") or []
            if use_raw_current
            else source.get("feedback") or []
        )
        feedback_map = {
            row.get("projectName"): row
            for row in source_feedback
            if row.get("projectName")
        }
        projects = []
        for project in source_projects:
            feedback = feedback_map.get(project.get("name"), {})
            projects.append(
                {
                    **project,
                    "weakness": clean_text(feedback.get("weakness")),
                    "improvement": clean_text(feedback.get("improvement")),
                }
            )
        projects = [
            project
            for project in projects
            if parse_number(project.get("budget")) is not None
        ]
        type_overrides = (current_overrides.get(name) or {}).get("projectTypes") or {}
        if type_overrides:
            for project in projects:
                project_name = project.get("name") or ""
                new_type = type_overrides.get(project_name)
                if new_type is None:
                    new_type = next(
                        (
                            value
                            for key, value in type_overrides.items()
                            if key and key in project_name
                        ),
                        None,
                    )
                if not new_type:
                    continue
                project["mgmtType"] = new_type
                if new_type != "성과관리사업":
                    project["projectExecRate"] = None

        adjusted_budget = performance.get("adjustedBudget")
        if adjusted_budget is None:
            project_budgets = [
                parse_number(project.get("budget"))
                for project in source_projects
            ]
            known_budgets = [value for value in project_budgets if value is not None]
            if known_budgets:
                adjusted_budget = sum(known_budgets)
        if adjusted_budget is None:
            adjusted_budget = current_budget.get("adjustedBudget")

        parent = parents.get(name, "기타")
        # The reference compilation places the renamed 총무인사팀 under 사무처.
        if name == "총무과":
            parent = "사무처"

        by_type = dict(Counter(project.get("mgmtType") or "지정안됨" for project in projects))
        budget_exec_rate = performance.get("budgetExecRate")
        if budget_exec_rate is None:
            budget_exec_rate = current_budget.get("budgetExecRateAvg")
        project_exec_rate = performance.get("projectExecRate")
        budget_grade = evaluation.get("budgetExecRate")
        project_grade = evaluation.get("projectExecRate")
        total_grade = evaluation.get("totalScore")

        # IR can store departments without a finalized performance metric as
        # 0%, and plan2026-only rows can inflate byType after the annual close.
        # A missing finalized average plus the 0% evaluation marker is treated
        # as 해당없음 (e.g. 교목처 2025).
        project_not_applicable = int(by_type.get("성과관리사업") or 0) == 0 or (
            parse_number(project_exec_rate) == 0
            and summary.get("avgProjectExecRate") is None
            and str(project_grade or "").strip() in {"", "-", "0", "0%"}
        )
        if project_not_applicable:
            project_exec_rate = None
            project_grade = "해당없음"

        # 교육미디어지원팀's current narrative is registered under 시설관리팀.
        # Its confirmed 2025 execution rate is embedded in that IR comment.
        if name == "교육미디어지원팀" and budget_exec_rate is None:
            narrative = str(evaluation.get("performancePlan2026") or "")
            rate_match = re.search(r"예산집행률\s*([\d.]+)%", narrative)
            if rate_match:
                budget_exec_rate = float(rate_match.group(1))
                if budget_exec_rate >= 95:
                    budget_grade = "A+"
                    if total_grade in (None, "", "-") and project_exec_rate is None:
                        total_grade = "A+"

        override = current_overrides.get(name) or {}
        if override:
            adjusted_budget = override.get("adjustedBudget", adjusted_budget)
            budget_exec_rate = override.get("budgetExecRate", budget_exec_rate)
            project_exec_rate = override.get("projectExecRate", project_exec_rate)
            budget_grade = override.get("budgetGrade", budget_grade)
            project_grade = override.get("projectGrade", project_grade)
            total_grade = override.get("totalGrade", total_grade)
            if "projectGrade" in override:
                project_not_applicable = override.get("projectGrade") == "해당없음"

        budget_score = parse_number(budget_exec_rate)
        project_score = parse_number(project_exec_rate)
        total_average = None
        if budget_score is not None:
            if project_not_applicable:
                total_average = budget_score
            elif project_score is not None:
                total_average = (budget_score + project_score) / 2
        total_grade = total_grade_from_average(total_average)
        plan2026 = evaluation.get("performancePlan2026")
        normalized_plan = str(plan2026 or "").strip()
        if normalized_plan not in {"", "-"} and plan_text_counts[normalized_plan] > 1:
            owner = next(
                (
                    dept_name
                    for signature, dept_name in PLAN_TEXT_OWNER_HINTS.items()
                    if signature in normalized_plan
                ),
                None,
            )
            if owner != name:
                plan2026 = None

        normalized.append(
            {
                "sourceName": name,
                "name": display_name(name),
                "parent": parent,
                "adjustedBudget": adjusted_budget,
                "budgetExecRate": budget_exec_rate,
                "projectExecRate": project_exec_rate,
                "previousBudgetExecRate": (
                    finalized.get("budgetExecRate")
                    if finalized
                    else previous.get("sumExpAmtRate")
                ),
                "previousProjectExecRate": (
                    finalized.get("projectExecRate")
                    if finalized
                    else previous.get("fuflRate")
                ),
                "previousProjectApplicable": finalized.get("projectApplicable"),
                "currentProjectApplicable": not project_not_applicable,
                "totalAverage": total_average,
                "totalGrade": total_grade,
                "budgetGrade": budget_grade,
                "projectGrade": project_grade,
                "previousGrade": finalized.get("totalGrade"),
                "projectCount": len(projects),
                "byType": by_type,
                "projects": projects,
                "plan2026": plan2026,
                "plan2026Source": evaluation.get("performancePlan2026Source"),
                "submissionStatus": (source.get("submission") or {}).get("status"),
                "budgetHistory": source.get("budgetHistory") or {},
                "metricOverrideSource": override.get("source"),
            }
        )
    return normalized


def make_audit(report: dict, departments: list[dict]) -> dict:
    missing_parent = [d["sourceName"] for d in departments if d["parent"] == "기타"]
    missing_previous = [
        d["sourceName"]
        for d in departments
        if d.get("previousBudgetExecRate") is None
        and d.get("previousProjectExecRate") is None
    ]
    missing_previous_grade = [
        d["sourceName"] for d in departments if d.get("previousGrade") is None
    ]
    missing_plan = [
        d["sourceName"] for d in departments if clean_text(d.get("plan2026")) == "자료없음"
    ]
    missing_weakness = sum(
        1 for d in departments for p in d["projects"] if p["weakness"] == "자료없음"
    )
    missing_improvement = sum(
        1 for d in departments for p in d["projects"] if p["improvement"] == "자료없음"
    )
    project_count = sum(len(d["projects"]) for d in departments)
    grade_counts = Counter(clean_text(d.get("totalGrade")) for d in departments)
    missing_current_metrics = [
        d["sourceName"]
        for d in departments
        if d.get("adjustedBudget") is None
        or d.get("budgetExecRate") is None
        or d.get("totalGrade") in (None, "", "-")
    ]

    return {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "reportYear": report.get("year"),
        "departmentCount": len(departments),
        "projectCount": project_count,
        "groupCount": len({d["parent"] for d in departments}),
        "gradeCounts": dict(sorted(grade_counts.items())),
        "coverage": {
            "currentDepartmentMetrics": sum(
                1
                for d in departments
                if d.get("adjustedBudget") is not None
                and d.get("budgetExecRate") is not None
                and d.get("totalGrade") not in (None, "", "-")
            ),
            "previousYearPerformance": len(departments) - len(missing_previous),
            "nextYearNarrative": len(departments) - len(missing_plan),
            "feedbackWeakness": project_count - missing_weakness,
            "feedbackImprovement": project_count - missing_improvement,
            "previousYearGrade": len(departments) - len(missing_previous_grade),
        },
        "missing": {
            "parentOrganization": missing_parent,
            "currentDepartmentMetrics": missing_current_metrics,
            "previousYearPerformance": missing_previous,
            "nextYearNarrative": missing_plan,
            "feedbackWeaknessCount": missing_weakness,
            "feedbackImprovementCount": missing_improvement,
            "previousYearGrade": missing_previous_grade,
        },
        "notes": [
            "전년도 실적·등급은 2024부서별데이터.xlsx를 불러오고 최종 발간 PDF의 확정값을 우선 적용했습니다.",
            "성과관리사업이 0건인 현재 부서는 사업이행률을 해당없음으로 표시했습니다.",
            "예산 값이 없는 사업은 세부실적·사업환류 표에서 제외했습니다.",
            "교육미디어지원팀의 2025 예산집행률은 시설관리팀 IR 평가 의견의 99.82%를 적용했습니다.",
            "교육미디어지원팀의 덮어쓰기 전 확정 실적은 annual_evaluation_overrides.json에서 복원했습니다.",
            "노원어린이영어교실의 사업이행률 79.56%는 결과보고서 목표·실적으로 재산정했습니다.",
            "총무인사팀 교직원복지 지원(직원근무복)은 항례적사업으로 재분류했습니다.",
            "부서 표기명은 보고서용 별칭을 적용하되 원천 부서명은 audit에 보존했습니다.",
        ],
    }


def project_type_note(dept: dict) -> str:
    by_type = dept.get("byType") or {}
    projects = dept.get("projects") or []
    routine = sum(project.get("mgmtType") == "항례적사업" for project in projects)
    performance = sum(project.get("mgmtType") == "성과관리사업" for project in projects)
    if not projects:
        routine = int(by_type.get("항례적사업") or 0)
        performance = int(by_type.get("성과관리사업") or 0)
    return f"항례 {routine}건 · 성과 {performance}건"


def summary_rows(departments: list[dict]) -> str:
    rows: list[str] = []
    seen_group = None
    group_counts = Counter(d["parent"] for d in departments)
    for dept in departments:
        cells = []
        if dept["parent"] != seen_group:
            cells.append(
                f'<td rowspan="{group_counts[dept["parent"]]}" class="group-cell">'
                f'{esc(dept["parent"])}</td>'
            )
            seen_group = dept["parent"]
        grade_change = grade_transition(dept.get("previousGrade"), dept.get("totalGrade"))
        cells.extend(
            [
                f'<td class="dept-cell">{esc(dept["name"])}</td>',
                f'<td class="num">{format_money(dept["adjustedBudget"], thousands=True)}</td>',
                f'<td>{esc(transition(dept["previousBudgetExecRate"], dept["budgetExecRate"]))}</td>',
                f'<td>{esc(transition(dept["previousProjectExecRate"], dept["projectExecRate"], previous_applicable=dept.get("previousProjectApplicable"), current_applicable=dept.get("currentProjectApplicable")))}'
                f'<br><span class="rate-meta">{esc(project_type_note(dept))}</span></td>',
                f'<td class="grade">{esc(grade_change)}</td>',
            ]
        )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "".join(rows)


def annual_feedback_rows(departments: list[dict]) -> str:
    rows: list[str] = []
    for dept in departments:
        weakness = next(
            (
                project["weakness"]
                for project in dept["projects"]
                if project["weakness"] != "자료없음"
            ),
            None,
        )
        improvement = next(
            (
                project["improvement"]
                for project in dept["projects"]
                if project["improvement"] != "자료없음"
            ),
            None,
        )
        blocks: list[str] = []
        if weakness or improvement:
            performance_text = (
                f"{dept['name']}은(는) {dept['projectCount']}개 사업을 수행하여 "
                f"예산집행률 {format_rate(dept['budgetExecRate'])}, "
                f"사업이행률 {format_rate(dept['projectExecRate'])}을 기록함."
            )
            blocks.append(
                '<div class="feedback-content feedback-performance">'
                '<strong class="feedback-label">운영 결과</strong>'
                f"<div>{text_block(concise_korean_style(performance_text))}</div></div>"
            )
            if weakness:
                weakness_text = f"주요 취약요인은 {compact_text(weakness, None)}"
                blocks.append(
                    '<div class="feedback-content feedback-weakness">'
                    '<strong class="feedback-label">취약요인</strong>'
                    f"<div>{text_block(concise_korean_style(weakness_text))}</div></div>"
                )
            if improvement:
                improvement_text = (
                    f"차년도 개선계획은 {compact_text(improvement, None)}"
                )
                blocks.append(
                    '<div class="feedback-content feedback-improvement">'
                    '<strong class="feedback-label">개선계획</strong>'
                    f"<div>{text_block(concise_korean_style(improvement_text))}</div></div>"
                )
        else:
            narrative = compact_text(dept.get("plan2026"), None)
            blocks.append(
                '<div class="feedback-content feedback-full">'
                '<strong class="feedback-label">연간 환류 내용</strong>'
                f"<div>{text_block(concise_korean_style(narrative))}</div></div>"
            )
        rows.append(
            "<tr>"
            f"<td>{esc(dept['parent'])}</td>"
            f"<td>{esc(dept['name'])}</td>"
            f'<td class="narrative">{"".join(blocks)}</td>'
            "</tr>"
        )
    return "".join(rows)


def project_rows(dept: dict) -> str:
    rows = []
    for project in dept["projects"]:
        rows.append(
            "<tr>"
            f'<td>{esc(dept["name"])}</td>'
            f'<td class="project-name">{esc(project.get("name", "자료없음"))}</td>'
            f'<td>{esc(clean_text(project.get("mgmtType"), "지정안됨"))}</td>'
            f'<td class="num">{format_money(project.get("budget"))}</td>'
            f'<td class="num">{esc(format_rate(project.get("budgetExecRate")))}</td>'
            f'<td class="num">{esc(format_rate(project.get("projectExecRate")))}</td>'
            "</tr>"
        )
    if not rows:
        return '<tr><td colspan="6" class="empty-cell">등록된 사업 없음</td></tr>'
    return "".join(rows)


def feedback_rows(dept: dict) -> str:
    rows = []
    for project in dept["projects"]:
        rows.append(
            "<tr>"
            f'<td>{esc(dept["name"])}</td>'
            f'<td class="project-name">{esc(project.get("name", "자료없음"))}</td>'
            f'<td class="narrative">{text_block(project.get("weakness"))}</td>'
            f'<td class="narrative">{text_block(project.get("improvement"))}</td>'
            "</tr>"
        )
    if not rows:
        return '<tr><td colspan="4" class="empty-cell">등록된 사업환류 없음</td></tr>'
    return "".join(rows)


def dept_section(dept: dict, year: int) -> str:
    by_type = dept.get("byType") or {}
    type_summary = " / ".join(
        [
            f"성과관리 {by_type.get('성과관리사업', 0)}",
            f"항례적 {by_type.get('항례적사업', 0)}",
            f"지정안됨 {by_type.get('지정안됨', 0)}",
        ]
    )
    return f"""
    <section class="department-section" data-dept="{esc(dept['sourceName'])}">
      <header class="department-title">
        <span>{esc(dept['parent'])}</span>
        <h2>{esc(dept['name'])} 연차보고서</h2>
      </header>

      <h3>■ 부서실적</h3>
      <div class="calculation-note">
        <strong>평가 산정 기준</strong>
        <span>① 항례적사업은 사업이행률을 적용하지 않으며, 성과관리사업만 사업이행률을 산출함.</span>
        <span>② 사업이행률 = 성과관리사업별 이행률 합계 ÷ 성과관리사업 수</span>
        <span>③ 성과관리사업이 있는 경우 종합평균 = (IR 예산집행률 + IR 사업이행률) ÷ 2</span>
        <span>④ 종합등급: 95 이상 A+ · 85 이상 A · 75 이상 B+ · 65 이상 B · 55 이상 C · 55 미만 D</span>
        <span>⑤ 성과관리사업이 없는 경우 사업이행률은 ‘해당없음’, 종합등급은 예산집행률 등급을 적용함.</span>
      </div>
      <table class="metric-table">
        <thead><tr>
          <th>구분</th><th>조정예산(원)</th><th>예산집행률</th>
          <th>사업이행률</th><th>사업수</th>
        </tr></thead>
        <tbody><tr>
          <td>{esc(dept['name'])}</td>
          <td class="num">{format_money(dept['adjustedBudget'])}</td>
          <td class="num">{esc(format_rate(dept['budgetExecRate']))}</td>
          <td class="num">{esc(format_rate(dept['projectExecRate']))}<br>
            <span class="rate-meta">{esc(project_type_note(dept))}</span>
          </td>
          <td>{dept['projectCount']}건<br><span class="small">{esc(type_summary)}</span></td>
        </tr></tbody>
      </table>

      <h3>■ 세부실적</h3>
      <table class="project-table">
        <thead><tr>
          <th>구분</th><th>사업명</th><th>성과구분</th>
          <th>예산(조정)</th><th>예산집행률</th><th>사업이행률</th>
        </tr></thead>
        <tbody>{project_rows(dept)}</tbody>
      </table>

      <h3>■ 사업환류</h3>
      <table class="feedback-table">
        <thead><tr><th>구분</th><th>사업명</th><th>취약요인</th><th>개선계획</th></tr></thead>
        <tbody>{feedback_rows(dept)}</tbody>
      </table>

      <h3>■ 평가결과</h3>
      <table class="grade-table">
        <thead><tr>
          <th>예산집행률 등급</th><th>사업이행률 등급</th><th>종합등급</th>
          <th>{year - 1}→{year} 종합등급</th>
        </tr></thead>
        <tbody><tr>
          <td>{esc(clean_text(dept.get('budgetGrade')))}</td>
          <td>{esc(clean_text(dept.get('projectGrade')))}</td>
          <td class="grade-current">{esc(clean_text(dept.get('totalGrade')))}<br>
            <span class="rate-meta">종합평균 {esc(format_rate(dept.get('totalAverage')))}</span>
          </td>
          <td>{esc(grade_transition(dept.get('previousGrade'), dept.get('totalGrade')))}</td>
        </tr></tbody>
      </table>

      <h3>■ {year}학년도 평가 결과 및 {year + 1}학년도 성과관리계획</h3>
      <div class="plan-narrative">{text_block(dept.get('plan2026'))}</div>
    </section>
    """


def build_html(report: dict, departments: list[dict], audit: dict) -> str:
    year = int(report.get("year") or 2025)
    generated_date = datetime.now().astimezone().strftime("%Y. %m. %d.")
    groups: dict[str, list[dict]] = defaultdict(list)
    for dept in departments:
        groups[dept["parent"]].append(dept)

    toc = "".join(
        f"<li><strong>{esc(group)}</strong><span>"
        + ", ".join(esc(d["name"]) for d in members)
        + "</span></li>"
        for group, members in groups.items()
    )
    detail_toc_parts: list[str] = []
    detail_index = 1
    for group, members in groups.items():
        items = []
        for dept in members:
            items.append(
                f'<li data-toc-dept="{esc(dept["sourceName"])}">'
                f'<span class="toc-number">{detail_index:02d}</span>'
                f'<span class="toc-dept-name">{esc(dept["name"])}</span></li>'
            )
            detail_index += 1
        detail_toc_parts.append(
            '<div class="department-toc-group">'
            f"<h2>{esc(group)}</h2><ul>{''.join(items)}</ul></div>"
        )
    detail_toc = "".join(detail_toc_parts)
    sections = "".join(dept_section(dept, year) for dept in departments)

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>{year}학년도 부서연차평가 보고서</title>
  <style>
    @page {{ size: A4; margin: 14mm 11mm 16mm; }}
    * {{ box-sizing: border-box; }}
    html {{ font-family: "Malgun Gothic", "Noto Sans KR", sans-serif; color: #111; }}
    body {{ margin: 0; font-size: 9.2pt; line-height: 1.48; }}
    .cover {{
      height: 255mm; display: flex; flex-direction: column;
      align-items: center; justify-content: center; text-align: center;
      break-after: page;
    }}
    .cover .year {{ font-size: 15pt; letter-spacing: .12em; margin-bottom: 12mm; }}
    .cover h1 {{ font-size: 27pt; margin: 0; letter-spacing: -.04em; }}
    .cover .date {{ margin-top: 64mm; font-size: 13pt; }}
    .cover .office {{ margin-top: 7mm; font-size: 16pt; font-weight: 700; }}
    .intro-page {{ break-after: page; }}
    .department-divider {{
      height: 255mm; display: flex; flex-direction: column;
      align-items: center; justify-content: center; text-align: center;
      break-before: page; break-after: page;
    }}
    .department-divider .divider-kicker {{
      margin-bottom: 8mm; font-size: 12pt; letter-spacing: .16em; color: #555;
    }}
    .department-divider h1 {{
      margin: 0; padding: 8mm 14mm; border-top: 1mm solid #222;
      border-bottom: 1mm solid #222; font-size: 28pt; letter-spacing: -.04em;
    }}
    .department-divider .divider-year {{ margin-top: 12mm; font-size: 12pt; color: #555; }}
    .department-toc-section {{ break-before: page; break-after: page; }}
    .department-toc {{
      columns: 2; column-gap: 12mm; margin: 0;
    }}
    .department-toc-group {{
      break-inside: avoid; margin: 0 0 5mm; padding-bottom: 2mm;
      border-bottom: .3mm solid #aaa;
    }}
    .department-toc-group h2 {{ margin: 0 0 1.5mm; font-size: 10.5pt; }}
    .department-toc-group ul {{ margin: 0; padding: 0; list-style: none; }}
    .department-toc-group li {{
      display: flex; gap: 2.5mm; padding: .7mm 0; font-size: 8.5pt;
    }}
    .toc-number {{ width: 7mm; color: #777; font-variant-numeric: tabular-nums; }}
    .toc-dept-name {{ flex: 1; }}
    h2 {{ margin: 0; font-size: 17pt; }}
    h3 {{ margin: 6mm 0 2.5mm; font-size: 11.5pt; }}
    .report-title {{ text-align: center; font-size: 19pt; margin-bottom: 8mm; }}
    .toc {{ margin: 0; padding: 0; list-style: none; columns: 2; column-gap: 12mm; }}
    .toc li {{ break-inside: avoid; margin: 0 0 4mm; border-bottom: .3mm solid #aaa; padding-bottom: 2mm; }}
    .toc strong {{ display: block; font-size: 10pt; }}
    .toc span {{ display: block; margin-top: 1mm; color: #444; font-size: 8.5pt; }}
    .summary-section {{ break-before: page; }}
    .feedback-summary-section {{ break-before: page; }}
    .department-section {{ break-before: page; }}
    .department-title {{
      display: flex; align-items: baseline; gap: 4mm;
      border-bottom: .7mm solid #111; padding-bottom: 2.5mm; margin-bottom: 5mm;
    }}
    .department-title span {{ font-size: 9pt; color: #555; min-width: 24mm; }}
    .notice {{ margin: 0 0 3mm; font-size: 8.3pt; color: #333; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin: 0 0 4mm; }}
    thead {{ display: table-header-group; }}
    th, td {{ border: .25mm solid #555; padding: 1.7mm 1.5mm; vertical-align: middle; word-break: keep-all; overflow-wrap: anywhere; }}
    th {{ background: #ececec; text-align: center; font-weight: 700; }}
    tbody tr {{ break-inside: avoid-page; }}
    .summary-table {{ font-size: 7.7pt; }}
    .summary-table th:nth-child(1) {{ width: 14%; }}
    .summary-table th:nth-child(2) {{ width: 16%; }}
    .summary-table th:nth-child(3) {{ width: 13%; }}
    .summary-table th:nth-child(4), .summary-table th:nth-child(5) {{ width: 23%; }}
    .summary-table th:nth-child(6) {{ width: 11%; }}
    .feedback-summary-table {{ font-size: 8.5pt; }}
    .feedback-summary-table th:nth-child(1) {{ width: 15%; }}
    .feedback-summary-table th:nth-child(2) {{ width: 18%; }}
    .feedback-summary-table th:nth-child(3) {{ width: 67%; }}
    .feedback-summary-table tbody tr,
    .feedback-summary-table tbody td {{
      break-inside: auto; page-break-inside: auto;
    }}
    .feedback-content {{
      display: grid; grid-template-columns: 17mm 1fr; gap: 2mm;
      padding: 2mm 0; border-bottom: 1px solid #e2e2e2;
      break-inside: auto; page-break-inside: auto;
    }}
    .feedback-content:first-child {{ padding-top: 0; }}
    .feedback-content:last-child {{ padding-bottom: 0; border-bottom: 0; }}
    .feedback-label {{
      align-self: start; padding: 0.8mm 1mm; border-radius: 1mm;
      text-align: center; font-size: 7.2pt; line-height: 1.3;
      background: #ececec; color: #333;
    }}
    .feedback-performance .feedback-label {{ background: #e8f1f7; color: #24506b; }}
    .feedback-weakness .feedback-label {{ background: #f8ece8; color: #7a3e2e; }}
    .feedback-improvement .feedback-label {{ background: #eaf3e8; color: #355f32; }}
    .feedback-full .feedback-label {{ background: #efedf7; color: #514477; }}
    .source-note {{
      margin: 0 0 3mm; padding: 2.5mm 3mm; border-left: 3px solid #777;
      background: #f4f4f4; color: #444; font-size: 8pt; line-height: 1.5;
    }}
    .group-cell {{ text-align: center; font-weight: 700; background: #f7f7f7; }}
    .dept-cell {{ font-weight: 700; }}
    .metric-table th:nth-child(1) {{ width: 18%; }}
    .metric-table th:nth-child(2) {{ width: 23%; }}
    .project-table {{ font-size: 8pt; }}
    .project-table th:nth-child(1) {{ width: 12%; }}
    .project-table th:nth-child(2) {{ width: 36%; }}
    .project-table th:nth-child(3) {{ width: 15%; }}
    .project-table th:nth-child(4) {{ width: 17%; }}
    .project-table th:nth-child(5), .project-table th:nth-child(6) {{ width: 10%; }}
    .feedback-table {{ font-size: 8pt; }}
    .feedback-table th:nth-child(1) {{ width: 11%; }}
    .feedback-table th:nth-child(2) {{ width: 25%; }}
    .feedback-table th:nth-child(3), .feedback-table th:nth-child(4) {{ width: 32%; }}
    .feedback-table tbody tr {{ break-inside: auto; }}
    .narrative {{ vertical-align: top; white-space: normal; }}
    .grade-table th {{ width: 25%; }}
    .grade-table td {{ text-align: center; font-size: 10pt; }}
    .grade-current {{ font-size: 14pt !important; font-weight: 700; }}
    .plan-narrative {{
      min-height: 35mm; border: .25mm solid #555; padding: 4mm;
      white-space: normal; font-size: 9pt; line-height: 1.65;
    }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .grade {{ text-align: center; font-weight: 700; }}
    .project-name {{ font-weight: 600; }}
    .small {{ font-size: 7.4pt; color: #555; }}
    .rate-meta {{ font-size: 6.5pt; color: #666; font-weight: 400; white-space: nowrap; }}
    .calculation-note {{
      margin: 0 0 2.5mm; padding: 2.5mm 3mm; border: 1px solid #c9c9c9;
      background: #f7f7f7; font-size: 7.5pt; line-height: 1.45;
    }}
    .calculation-note strong {{ display: block; margin-bottom: 0.7mm; }}
    .calculation-note span {{ display: block; }}
    .calculation-note .formula-caution {{ margin-top: 0.7mm; color: #555; }}
    .empty-cell {{ text-align: center; color: #666; padding: 5mm; }}
    .audit-note {{ margin-top: 6mm; padding: 3mm; background: #f5f5f5; font-size: 8.2pt; }}
    @media screen {{
      body {{ max-width: 210mm; margin: 0 auto; padding: 12mm; background: white; }}
      .department-section, .summary-section, .feedback-summary-section,
      .intro-page, .cover, .department-divider, .department-toc-section {{
        border-bottom: 1px dashed #aaa;
      }}
    }}
  </style>
</head>
<body>
  <section class="cover">
    <div class="year">{year}학년도</div>
    <h1>부서연차평가 보고서</h1>
    <div class="date">{generated_date}</div>
    <div class="office">기획처</div>
  </section>

  <section class="intro-page">
    <h1 class="report-title">목차</h1>
    <ul class="toc">{toc}</ul>
    <div class="audit-note">
      생성 기준: {esc(str(report.get('builtAt') or report.get('generatedAt') or '-'))}<br>
      수록 범위: {len(departments)}개 부서 · {audit['projectCount']}개 사업<br>
      전년도 실적·등급: 2024 데이터와 최종 발간 PDF 대조값 적용
    </div>
  </section>

  <section class="summary-section">
    <h1 class="report-title">부서별 연차평가 결과</h1>
    <div class="calculation-note">
      <strong>평가 산정 기준</strong>
      <span>① 항례적사업은 사업이행률을 적용하지 않으며, 성과관리사업만 사업이행률을 산출함.</span>
      <span>② 사업이행률 = 성과관리사업별 이행률 합계 ÷ 성과관리사업 수</span>
      <span>③ 성과관리사업이 있는 경우 종합평균 = (IR 예산집행률 + IR 사업이행률) ÷ 2</span>
      <span>④ 종합등급: 95 이상 A+ · 85 이상 A · 75 이상 B+ · 65 이상 B · 55 이상 C · 55 미만 D</span>
      <span>⑤ 성과관리사업이 없는 경우 사업이행률은 ‘해당없음’, 종합등급은 예산집행률 등급을 적용함.</span>
    </div>
    <table class="summary-table">
      <thead><tr>
        <th>소속</th><th>부서명</th><th>조정예산<br>(천원)</th>
        <th>예산집행률<br>({year - 1}→{year})</th>
        <th>사업이행률<br>({year - 1}→{year})</th>
        <th>종합<br>({year - 1}→{year})</th>
      </tr></thead>
      <tbody>{summary_rows(departments)}</tbody>
    </table>
  </section>

  <section class="feedback-summary-section">
    <h1 class="report-title">부서별 연간 환류 내역</h1>
    <div class="source-note">
      ※ 아래 환류 내역은 각 부서가 직접 작성·제출한 내용을 기반으로 하며,
      원문의 의미와 수치는 변경하지 않고 보고서 형식에 맞추어 문체와 구조만 정리함.
    </div>
    <table class="feedback-summary-table">
      <thead><tr><th>소속</th><th>부서명</th><th>연차평가 결과 요약</th></tr></thead>
      <tbody>{annual_feedback_rows(departments)}</tbody>
    </table>
  </section>

  <section class="department-divider">
    <div class="divider-kicker">{year}학년도 부서연차평가</div>
    <h1>부서별 연차보고서</h1>
    <div class="divider-year">{year}. 03. 01. — {year + 1}. 02. 28.</div>
  </section>

  <section class="department-toc-section">
    <h1 class="report-title">부서별 연차보고서 목차</h1>
    <div class="department-toc">{detail_toc}</div>
  </section>

  {sections}
</body>
</html>
"""


def print_pdf(html_path: Path, pdf_path: Path) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright가 필요합니다: pip install playwright") from exc

    temp_path = pdf_path.with_name(f"{pdf_path.stem}_생성중.pdf")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.emulate_media(media="print")
        page.pdf(
            path=str(temp_path),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            display_header_footer=True,
            header_template="<span></span>",
            footer_template=(
                '<div style="width:100%;font-size:8px;text-align:center;color:#555;">'
                '<span class="pageNumber"></span> / <span class="totalPages"></span>'
                "</div>"
            ),
            margin={"top": "14mm", "right": "11mm", "bottom": "16mm", "left": "11mm"},
        )
        browser.close()
    try:
        temp_path.replace(pdf_path)
        return pdf_path
    except PermissionError:
        revised_path = pdf_path.with_name(f"{pdf_path.stem}_수정본.pdf")
        try:
            temp_path.replace(revised_path)
            return revised_path
        except PermissionError:
            timestamp = datetime.now().strftime("%H%M%S")
            versioned_path = pdf_path.with_name(f"{pdf_path.stem}_수정본_{timestamp}.pdf")
            temp_path.replace(versioned_path)
            return versioned_path


def write_audit_html(audit: dict, path: Path) -> None:
    coverage_rows = "".join(
        f"<tr><th>{esc(key)}</th><td>{value}</td></tr>"
        for key, value in audit["coverage"].items()
    )
    missing_sections = "".join(
        f"<h2>{esc(key)}</h2><pre>{esc(json.dumps(value, ensure_ascii=False, indent=2))}</pre>"
        for key, value in audit["missing"].items()
    )
    path.write_text(
        f"""<!doctype html><html lang="ko"><meta charset="utf-8">
<title>부서연차평가 데이터 검증</title>
<style>
body{{font:14px/1.6 "Malgun Gothic",sans-serif;max-width:1000px;margin:30px auto;padding:0 20px}}
table{{border-collapse:collapse}}th,td{{border:1px solid #aaa;padding:6px 10px;text-align:left}}
pre{{white-space:pre-wrap;background:#f5f5f5;padding:12px}}
</style>
<h1>부서연차평가 데이터 검증</h1>
<p>생성: {esc(audit['generatedAt'])}</p>
<p>부서 {audit['departmentCount']}개 · 사업 {audit['projectCount']}개 · 조직 {audit['groupCount']}개</p>
<table>{coverage_rows}</table>{missing_sections}</html>""",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    report = load_embedded_report(args.index)
    config = load_config()
    org = read_json(ORG_PATH, {"groupOrder": [], "parents": {}})
    report_year = int(report.get("year") or 2025)
    perf_previous = load_perf_snapshot(config, report_year - 1)
    finalized_previous = load_finalized_history(report_year - 1)
    current_overrides = read_json(CURRENT_OVERRIDES_PATH, {})
    current_budget_data = read_json(CURRENT_BUDGET_EXEC_PATH, {})
    current_budget_rows = {
        row["name"]: row
        for row in current_budget_data.get("departments", [])
        if isinstance(row, dict) and row.get("name")
    }
    current_report_path = Path(config.get("paths", {}).get("reportJson") or "")
    current_report_data = (
        read_json(current_report_path, {}) if current_report_path.is_file() else {}
    )
    current_report_rows = {
        row["name"]: row
        for row in current_report_data.get("departments", [])
        if isinstance(row, dict) and row.get("name")
    }
    departments = normalize_departments(
        report,
        org,
        perf_previous,
        finalized_previous,
        current_overrides,
        current_budget_rows,
        current_report_rows,
    )
    audit = make_audit(report, departments)

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{report_year}학년도_부서연차평가_보고서_합본"
    html_path = output_dir / f"{stem}.html"
    pdf_path = output_dir / f"{stem}.pdf"
    audit_json_path = output_dir / f"{stem}_데이터검증.json"
    audit_html_path = output_dir / f"{stem}_데이터검증.html"

    html_path.write_text(build_html(report, departments, audit), encoding="utf-8")
    audit_json_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_audit_html(audit, audit_html_path)

    print(f"HTML: {html_path}")
    print(f"Audit JSON: {audit_json_path}")
    print(f"Audit HTML: {audit_html_path}")
    print(
        f"Coverage: {audit['departmentCount']} departments, "
        f"{audit['projectCount']} projects, "
        f"{audit['coverage']['previousYearPerformance']} previous-year matches"
    )

    if not args.html_only:
        written_pdf = print_pdf(html_path, pdf_path)
        print(f"PDF: {written_pdf}")


if __name__ == "__main__":
    main()
