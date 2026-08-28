# -*- coding: utf-8 -*-
"""Build 2025 mid-term plan annual evaluation report from cho.syu.my admin dump."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "midterm_plan_admin_raw.json"
OUT_HTML = ROOT / "reports" / "2025학년도_중장기발전계획_연차평가_보고서.html"
OUT_JSON = ROOT / "data" / "midterm_plan_scores.json"

SCORE_2024 = {
    "10000": 85.3,
    "20000": 75.5,
    "30000": 61.7,
    "40000": 100.0,
    "50000": 94.6,
    "60000": 88.8,
    "70000": 93.1,
    "90000": 91.1,
    "80000": 64.2,
    "91000": 71.2,
    "100000": 96.6,
    "110000": 89.6,
}

INDEX_ORDER = [
    "10000",
    "20000",
    "30000",
    "40000",
    "50000",
    "60000",
    "70000",
    "90000",
    "80000",
    "91000",
    "100000",
    "110000",
]

META = {
    "10000": {
        "no": "1-1",
        "area": "Ⅰ. 고등교육 선도",
        "strategy": "융합·유연화 기반 미래형 교육 운영 체계 혁신",
        "cat": "Ⅰ. 미래교육을 선도하는 MVP 교육혁신",
        "tasks": [
            ("01 미래교육 대비 학사제도 개선", "미래형 학사제도 참여학생 비율"),
            ("02 미래교육환경 대비 학사구조 개선", "융합형 교과목 개발 건수"),
            ("03 우수교원 확보", "적정 전임교원확보율"),
            ("04 교원 역량 강화", "교원 교수법 역량강화 참여인원"),
            ("05 교원 역량강화 프로그램", "교원 역량강화 프로그램 참여시간"),
        ],
    },
    "20000": {
        "no": "1-2",
        "area": "Ⅰ. 고등교육 선도",
        "strategy": "미래사회 역량 함양을 위한 교과교육 혁신",
        "cat": "Ⅰ. 미래교육을 선도하는 MVP 교육혁신",
        "tasks": [
            ("01 변혁적 역량 기반 핵심역량 체계 구축", "SU 핵심역량 지표"),
            ("02 교양교육 혁신", "디지털·융합 교양 교과목 개설 비율"),
            ("03 전공능력 관리체계", "SU 전공능력 지표"),
            ("04 전공교육 혁신", "혁신형 전공 교과목 개발·개편 비율"),
        ],
    },
    "30000": {
        "no": "1-3",
        "area": "Ⅰ. 고등교육 선도",
        "strategy": "교육관리체계 혁신",
        "cat": "Ⅰ. 미래교육을 선도하는 MVP 교육혁신",
        "tasks": [
            ("01 SU-MVP교수법의 대학 대표브랜드화", "SU-MVP교수법 적용 교과 비율 (30%)"),
            ("02 에듀테크 첨단교육 인프라 확충", "에듀테크 기반 강의실 개선 건수 (30%)"),
            ("03 교육 콘텐츠 개발 및 지식정보자원화", "교육콘텐츠 신규 개발 건수 (40%)"),
        ],
    },
    "40000": {
        "no": "2-1",
        "area": "Ⅱ. 학생 미래비전",
        "strategy": "역량기반 교육 통합관리 체계 구축",
        "cat": "Ⅱ. 학생주도 미래 설계 및 MVP인재 구현을 위한 종합지원 체계",
        "tasks": [
            ("01 인재육성 거버넌스", "인재육성체계 통합관리 거버넌스 이행률"),
            ("02 교육과정 질 관리", "교육과정 질 관리 인증 교과목 누적 비율"),
            ("03 비교과 참여", "비교과 프로그램 참여율"),
            ("04 인성교육", "대학 교육이념 연계 인성교육 프로그램 참여 비율"),
        ],
    },
    "50000": {
        "no": "2-2",
        "area": "Ⅱ. 학생 미래비전",
        "strategy": "학생의 성장과 성공을 위한 학업생활 종합지원",
        "cat": "Ⅱ. 학생주도 미래 설계 및 MVP인재 구현을 위한 종합지원 체계",
        "tasks": [
            ("01 역량증진", "학생역량증진 활동지수"),
            ("02 개별화 교육", "학생 1인당 개별화 교육 지원 건수"),
            ("03 학습역량", "학습역량강화 성장지수"),
            ("04 혁신 프로그램", "혁신형 학습역량·정서심리 프로그램 신규개발 수"),
            ("05 학업생활 만족", "학생 학업생활 만족도"),
        ],
    },
    "60000": {
        "no": "2-3",
        "area": "Ⅱ. 학생 미래비전",
        "strategy": "사회 기여 MVP 인재를 완성하는 진로·취창업 지원",
        "cat": "Ⅱ. 학생주도 미래 설계 및 MVP인재 구현을 위한 종합지원 체계",
        "tasks": [
            ("01 진로탄력성 기반 진로개발 지원", "진로·취창업 프로그램 개발·개편 비율"),
            ("02 졸업생 맞춤형 취업 지원", "혁신형 진로·취창업 프로그램 신규개발 수"),
            ("03 지역사회 맞춤형 창업 지원", "진로개발 및 창업 지원 교과목 운영 건수"),
            ("04 삼육 MVP 인증의 공신력 강화", "삼육 MVP 인증획득 학생 비율"),
        ],
    },
    "70000": {
        "no": "3-1",
        "area": "Ⅲ. 사회 가치창출",
        "strategy": "사회문제해결과 미래혁신을 위한 실용연구 역량 강화",
        "cat": "Ⅲ. 공유·협력 사회기여, 융합·초연결 산학협력, 현장기반 실용연구 혁신",
        "tasks": [
            ("01 국제논문", "전임교원 1인당 국제논문 수"),
            ("02 연구역량 계획", "연구역량 강화 개선계획 이행률"),
            ("03 융합연구", "학제간 및 국제 융합연구 수행 건수"),
            ("04 대학원 혁신", "대학원 교육 혁신 건수"),
        ],
    },
    "90000": {
        "no": "3-2",
        "area": "Ⅲ. 사회 가치창출",
        "strategy": "소통형 산학협력 네트워크 추진 강화",
        "cat": "Ⅲ. 공유·협력 사회기여, 융합·초연결 산학협력, 현장기반 실용연구 혁신",
        "tasks": [
            ("01 산학연계교육", "산학연계교육 참여자 비율"),
            ("02 가족회사", "산학협력 가족회사 확보 건수"),
            ("03 산업체 만족도", "산업체 만족도"),
            ("04 산학 역량강화", "산학협력 역량강화 개선과제 이행률"),
        ],
    },
    "80000": {
        "no": "3-3",
        "area": "Ⅲ. 사회 가치창출",
        "strategy": "사회적 가치 구현을 위한 공유·협력",
        "cat": "Ⅲ. 공유·협력 사회기여, 융합·초연결 산학협력, 현장기반 실용연구 혁신",
        "tasks": [
            ("01 서비스러닝", "서비스러닝 교육 만족도"),
            ("02 대외협력", "대외협력 협약 체결 건수"),
            ("03 평생교육", "평생교육 프로그램 참여자 수"),
            ("04 교육국제화", "SU-edx 교육국제화 프로그램 참여 학생 비율"),
        ],
    },
    "91000": {
        "no": "4-1",
        "area": "Ⅳ. 지속가능 경영",
        "strategy": "국내외 입학자원 확보 및 학생 유지 관리",
        "cat": "Ⅳ. 구성원의 참여·소통으로 함께 성장하는 혁신 거버넌스 구현",
        "tasks": [
            ("01 입학 마스터플랜 및 신입생 FYE", "신입생 교육 만족도 (50%)"),
            ("02 외국인 유학생 유치 및 정착 지원", "외국인 유학생 수 (50%)"),
        ],
    },
    "100000": {
        "no": "4-2",
        "area": "Ⅳ. 지속가능 경영",
        "strategy": "재정 건전성 확보",
        "cat": "Ⅳ. 구성원의 참여·소통으로 함께 성장하는 혁신 거버넌스 구현",
        "tasks": [
            ("01 재정수입 확충", "재정수입 확충 계획 이행률 (25%)"),
            ("02 등록금 외 수입 확대", "등록금 외 수입(중장기) 목표 달성률 (25%)"),
            ("03 기부금 수입 확대", "기부금 수입(중장기) 목표 달성률 (25%)"),
            ("04 예산 집행 효율화", "예산 집행률 (25%)"),
        ],
    },
    "110000": {
        "no": "4-3",
        "area": "Ⅳ. 지속가능 경영",
        "strategy": "행정관리 역량 강화",
        "cat": "Ⅳ. 구성원의 참여·소통으로 함께 성장하는 혁신 거버넌스 구현",
        "tasks": [
            ("01 의사결정 참여", "교원·직원 1인당 대학 내 의사결정 활동 참여 건수 (20%)"),
            ("02 캠퍼스 여건", "캠퍼스 시설 종합 만족도 (20%)"),
            ("03 교직원 역량", "교직원 1인당 교육훈련 참여 건수 (20%)"),
            ("04 정보화", "정보화 인프라 고도화 계획 이행률 (20%)"),
            ("05 외부 수요자", "외부 수요자 만족도(산업체·학부모·지역사회) (20%)"),
        ],
    },
}

AREAS = [
    {
        "id": "I",
        "title": "1. 「Ⅰ. 고등교육 선도」 영역",
        "ids": ["10000", "20000", "30000"],
    },
    {
        "id": "II",
        "title": "2. 「Ⅱ. 학생 미래비전」 영역",
        "ids": ["40000", "50000", "60000"],
    },
    {
        "id": "III",
        "title": "3. 「Ⅲ. 사회 가치창출」 영역",
        "ids": ["70000", "90000", "80000"],
    },
    {
        "id": "IV",
        "title": "4. 「Ⅳ. 지속가능 경영」 영역",
        "ids": ["91000", "100000", "110000"],
    },
]


def cap(actual, target):
    if not isinstance(actual, (int, float)) or not isinstance(target, (int, float)) or not target:
        return None
    return min(100.0, actual / float(target) * 100)


def eval_formula(formula, vals):
    if not formula:
        return None
    if any(v is None for v in vals.values()):
        return None
    expr = formula.replace("×", "*").replace("÷", "/")
    expr = expr.replace("A / B+C", "A / (B + C)")
    for k in sorted(vals, key=len, reverse=True):
        expr = re.sub(r"\b" + k + r"\b", str(vals[k]), expr)
    try:
        return float(eval(expr, {"__builtins__": {}}, {}))
    except Exception:
        return None


def sub_map(comp, key_a, key_t):
    vals = {}
    for s in comp.get("subs") or []:
        vk = s.get("var")
        if vk:
            vals[vk] = s.get(key_a if False else None)
    return vals


def vars_of(comp, actual=True, year="25"):
    vals = {}
    k = f"a{year}" if actual else f"t{year}"
    for s in comp.get("subs") or []:
        vk = s.get("var")
        if vk:
            vals[vk] = s.get(k)
    return vals


def formula_display(formula):
    if not formula:
        return ""
    if formula == "A / B+C":
        return "A / (B + C)"
    return formula.replace("*", "×")


def fmt(v, unit=""):
    if v is None:
        return "—"
    if isinstance(v, str):
        return v
    if unit == "원":
        return f"{v:,.0f}"
    if unit in ("명", "건", "차시") and abs(v) >= 1:
        if abs(v - round(v)) < 1e-6:
            return f"{int(round(v)):,}"
    if unit == "%":
        if abs(v - round(v)) < 1e-6:
            return str(int(round(v)))
        if abs(v) >= 100:
            return f"{v:.1f}"
        return f"{v:.2f}"
    if abs(v) >= 1000:
        return f"{v:,.0f}" if abs(v - round(v)) < 1e-6 else f"{v:,.2f}"
    if abs(v - round(v)) < 1e-6 and abs(v) >= 10:
        return str(int(round(v)))
    return f"{v:.2f}".rstrip("0").rstrip(".")


def fmt_u(v, unit=""):
    n = fmt(v, unit)
    if n == "—" or not unit:
        return n
    if unit == "%":
        return f"{n}%"
    if unit == "배":
        return n
    if unit in ("지수", "점", "건/인", "시간/인"):
        return f"{n} {unit}"
    return f"{n}{unit}"


def formula_cell(comp):
    formula = formula_display(comp.get("formula") or "")
    lines = []
    for s in comp.get("subs") or []:
        vk = s.get("var")
        name = (s.get("name") or "").strip()
        if vk:
            lines.append(f"{vk}: {name}")
    vars_html = "<br>".join(lines)
    extra = f'<div class="formula-vars">{vars_html}</div>' if vars_html else ""
    return f'<div class="formula-sys">{formula}</div>{extra}'


def rate_class(r):
    if r is None:
        return "flat"
    if r >= 100:
        return "up"
    if r < 70:
        return "down"
    return "flat"


def delta_html(a, b):
    d = round(b - a, 1)
    if abs(d) < 0.05:
        return f'<td class="num flat">{b:.1f} (0.0)</td>'
    if d > 0:
        return f'<td class="num up">{b:.1f} (+{d})</td>'
    return f'<td class="num down">{b:.1f} (−{abs(d)})</td>'


def delta_grade(a, b):
    d = round(b - a, 1)
    if abs(d) < 0.05:
        return '<td class="grade flat">0.0</td>'
    if d > 0:
        return f'<td class="grade up">+{d}</td>'
    return f'<td class="grade down">−{abs(d)}</td>'


def area_summary_table(area, by_id):
    rows = []
    s24s, s25s = [], []
    for iid in area["ids"]:
        s24 = SCORE_2024[iid]
        s25 = float(by_id[iid]["score"])
        s24s.append(s24)
        s25s.append(s25)
        name = by_id[iid]["name"].replace(" 지수", "")
        rows.append(
            f"<tr><td>{name}</td>"
            f'<td class="num">{s24:.1f}</td>'
            f'<td class="num">{s25:.1f}</td>'
            f"{delta_grade(s24, s25)}</tr>"
        )
    avg24 = round(sum(s24s) / len(s24s), 1)
    avg25 = round(sum(s25s) / len(s25s), 1)
    rows.append(
        f'<tr><td class="group-cell">영역 평균</td>'
        f'<td class="num">{avg24:.1f}</td>'
        f'<td class="num">{avg25:.1f}</td>'
        f"{delta_grade(avg24, avg25)}</tr>"
    )
    return f"""
    <h3>■ 영역 요약</h3>
    <table>
      <thead>
        <tr>
          <th style="width:46%">성과관리종합지수</th>
          <th style="width:18%">2024</th>
          <th style="width:18%">2025</th>
          <th style="width:18%">증감</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
    """


CHART_LABELS = {
    "10000": "Edu-Framework",
    "20000": "교과교육",
    "30000": "스마트 교육방법",
    "40000": "성과관리",
    "50000": "인재 성장",
    "60000": "사회기여",
    "70000": "연구역량",
    "90000": "산학협력",
    "80000": "공유·협력",
    "91000": "규모화",
    "100000": "재정 건전성",
    "110000": "경영체계",
}


def bar_fill(a, b):
    d = b - a
    if d >= 0.2:
        return "#3d6b4f"
    if d <= -0.2:
        return "#8b4540"
    return "#5b6e7d"


def svg_area_bars(by_id):
    groups = []
    for area in AREAS:
        s24 = [SCORE_2024[i] for i in area["ids"]]
        s25 = [float(by_id[i]["score"]) for i in area["ids"]]
        label = area["title"].split("「")[1].split("」")[0]
        groups.append((label, round(sum(s24) / 3, 1), round(sum(s25) / 3, 1)))
    w, h = 700, 230
    left, bottom, top = 48, 36, 36
    plot_w, plot_h = w - left - 16, h - top - bottom
    gap, n = 18, len(groups)
    gw = (plot_w - gap * (n - 1)) / n
    bw = gw * 0.38
    out = [
        f'<svg viewBox="0 0 {w} {h}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        'font-family="Malgun Gothic, sans-serif">',
        f'<rect x="{left}" y="10" width="11" height="11" fill="#9a9a9a"/>',
        f'<text x="{left + 16}" y="20" font-size="11" fill="#333">2024</text>',
        f'<rect x="{left + 72}" y="10" width="11" height="11" fill="#3d6b4f"/>',
        f'<text x="{left + 88}" y="20" font-size="11" fill="#333">2025 상승</text>',
        f'<rect x="{left + 158}" y="10" width="11" height="11" fill="#8b4540"/>',
        f'<text x="{left + 174}" y="20" font-size="11" fill="#333">하락</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" '
        'stroke="#555" stroke-width="1"/>',
    ]
    for t in (0, 50, 100):
        y = top + plot_h - plot_h * t / 100
        out.append(
            f'<line x1="{left}" y1="{y}" x2="{left + plot_w}" y2="{y}" stroke="#eee" stroke-width="1"/>'
        )
        out.append(
            f'<text x="{left - 6}" y="{y + 4}" font-size="10" text-anchor="end" fill="#666">{t}</text>'
        )
    for i, (lab, a, b) in enumerate(groups):
        x0 = left + i * (gw + gap)
        h24 = plot_h * a / 100
        h25 = plot_h * b / 100
        fill25 = bar_fill(a, b)
        out.append(
            f'<rect x="{x0 + 4:.1f}" y="{top + plot_h - h24:.1f}" width="{bw:.1f}" '
            f'height="{h24:.1f}" fill="#9a9a9a"/>'
        )
        out.append(
            f'<rect x="{x0 + 4 + bw + 6:.1f}" y="{top + plot_h - h25:.1f}" width="{bw:.1f}" '
            f'height="{h25:.1f}" fill="{fill25}"/>'
        )
        out.append(
            f'<text x="{x0 + 4 + bw / 2:.1f}" y="{top + plot_h - h24 - 4:.1f}" '
            f'font-size="10" text-anchor="middle" fill="#555">{a:.1f}</text>'
        )
        out.append(
            f'<text x="{x0 + 10 + bw * 1.5:.1f}" y="{top + plot_h - h25 - 4:.1f}" '
            f'font-size="10" text-anchor="middle" fill="#222">{b:.1f}</text>'
        )
        out.append(
            f'<text x="{x0 + gw / 2:.1f}" y="{h - 10}" font-size="11" text-anchor="middle">{lab}</text>'
        )
    out.append("</svg>")
    return "".join(out)


def render_overall(by_id):
    s24s = [SCORE_2024[i] for i in INDEX_ORDER]
    s25s = [float(by_id[i]["score"]) for i in INDEX_ORDER]
    avg24 = round(sum(s24s) / 12, 1)
    avg25 = round(sum(s25s) / 12, 1)
    dlt = round(avg25 - avg24, 1)
    deltas = sorted(
        (
            CHART_LABELS[iid],
            round(float(by_id[iid]["score"]) - SCORE_2024[iid], 1),
        )
        for iid in INDEX_ORDER
    )
    n_up = sum(1 for _, d in deltas if d >= 0.2)
    n_dn = sum(1 for _, d in deltas if d <= -0.2)
    n_fl = 12 - n_up - n_dn
    top_up = [x for x in reversed(deltas) if x[1] >= 0.2][:3]
    top_dn = [x for x in deltas if x[1] <= -0.2]
    dlt_txt = f"+{dlt:.1f}점" if dlt >= 0 else f"−{abs(dlt):.1f}점"
    up_txt = ", ".join(f"{n} +{d:.1f}점" for n, d in top_up)
    dn_txt = ", ".join(f"{n} −{abs(d):.1f}점" for n, d in top_dn)
    return f"""
  <section class="overall-section">
    <h1 class="report-title">종합 분석</h1>

    <h3>■ 영역별 추이</h3>
    <div class="chart-box">
      {svg_area_bars(by_id)}
      <div class="chart-cap">[그림] 4대 전략방향 영역 평균</div>
    </div>
    <div class="plan-narrative analysis">
      <p>○ 전체 평균 {avg24:.1f}점 → {avg25:.1f}점({dlt_txt}). 12개 중 {n_up}개 상승, {n_fl}개 보합, {n_dn}개 하락</p>
      <p class="sub">- 상승 폭 상위: {up_txt}</p>
      <p class="sub">- 하락: {dn_txt}</p>
      <p>○ Ⅰ. 고등교육 선도 74.2점 → 95.2점(+21.0점), 최대 상승. 전년 취약 구간을 회복함</p>
      <p class="sub">- 스마트 교육방법 만점: 콘텐츠 90차시 → 874차시</p>
      <p class="sub">- 교과혁신: 혁신형 전공 교과 4.0% → 27.7%, 학사제도 참여율 27.38% → 44.82%</p>
      <p class="sub">- 융합형 교과(0.13%)는 중장기 ’25 목표(0.3%) 대비 취약</p>
      <p>○ Ⅱ. 학생 미래비전 94.5점 → 90.0점(−4.5점), 유일한 영역 하락</p>
      <p class="sub">- 성과관리 100점, 인재 성장 98.1점은 유지</p>
      <p class="sub">- 사회기여 88.8 → 71.9점. MVP 인증 6명/1,249명(0.48%), 목표 1.89% 대비 25.4%</p>
      <p class="sub">- 진로 프로그램 개편 22.3%는 2025 목표(17.3%) 달성, 구성지표 목표(36%) 대비 62.1%</p>
      <p>○ Ⅲ. 사회 가치창출 82.8점 → 91.1점(+8.3점). 연구 만점과 공유·협력이 영역 상승을 견인함</p>
      <p class="sub">- 연구 93.1점 → 100점. 국제논문 0.29편, 연구역량 이행 6/6, 융합연구 13건 목표 달성. 대학원 혁신 20건(목표 22건 대비 90.9%)</p>
      <p class="sub">- 산학협력 91.1점 → 91.0점 보합. 산학연계 13.46%·산업체 만족도 76점 목표 상회, 가족회사 465/516건(90.1%)</p>
      <p class="sub">- 공유·협력 64.2점 → 82.4점(+18.2점). 서비스러닝 93점·협약 24건 달성, 평생교육 7,049/11,084명(63.6%), SU-edx 0.52%/0.78%(66.4%) 미달</p>
      <p>○ Ⅳ. 지속가능 경영 85.8점 → 89.2점(+3.4점)</p>
      <p class="sub">- 재정 100점, 경영체계 98.0점. 규모화 71.2 → 69.6점(유학생 550/1,400명)이 하방 요인</p>
    </div>

    <h3>■ 향후 환류사항</h3>
    <table class="reflux-table">
      <thead>
        <tr>
          <th style="width:6%">연번</th>
          <th style="width:18%">과제</th>
          <th style="width:32%">현황</th>
          <th style="width:28%">환류 방향</th>
          <th style="width:16%">담당</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="num">1</td>
          <td>삼육 MVP 인증 확대</td>
          <td>0.48%(6/1,249명), 목표 1.89% 대비 25.4%. 사회기여 지수 하락의 핵심 요인</td>
          <td>인증 요건·이수 경로 정비, 비교과·전공 연계 강화</td>
          <td>비교과통합센터</td>
        </tr>
        <tr>
          <td class="num">2</td>
          <td>외국인 유학생 유치</td>
          <td>550명(학부 187, 연수 174, 대학원 189), 목표 1,400명 대비 39.3%. 규모화 지수 최저</td>
          <td>학부·대학원·연수 유치 목표 재설정 및 실행계획 수립</td>
          <td>국제처, 대학원</td>
        </tr>
        <tr>
          <td class="num">3</td>
          <td>평생교육 참여자 확대</td>
          <td>7,049명(평생교육원 1,220 + 체육문화센터 5,829), 목표 11,084명 대비 63.6%</td>
          <td>A+B 집계 범위 고정, 과정 모집·홍보 강화</td>
          <td>평생교육원, 체육문화센터</td>
        </tr>
        <tr>
          <td class="num">4</td>
          <td>SU-edx 참여 제고</td>
          <td>0.52%(53/10,265명), 목표 0.78% 대비 66.4%</td>
          <td>단기 국제교류 프로그램 참여 확대</td>
          <td>국제처</td>
        </tr>
        <tr>
          <td class="num">5</td>
          <td>진로·취창업 목표 정합</td>
          <td>프로그램 개편 22.3%. 2025 목표 17.3%는 달성, 구성지표 목표 36% 대비 62.1%</td>
          <td>지수 산정 목표와 연도 목표 일치, 사회기여 지수 회복 점검</td>
          <td>취업진로지원센터, 스타트업지원센터, 기획처</td>
        </tr>
        <tr>
          <td class="num">6</td>
          <td>구성지표 목표 정합</td>
          <td>전임교원 152.5 vs 80.5, 대학원 혁신 18 vs 22, 학업생활 만족도 76 vs 71.5</td>
          <td>지수 산정용 목표와 부서 2025 목표를 동일 기준으로 정리</td>
          <td>기획처, 해당 부서</td>
        </tr>
        <tr>
          <td class="num">7</td>
          <td>융합형 교과 개발</td>
          <td>0.13%, 중장기 ’25 목표 0.3% 대비 취약</td>
          <td>전공·교양 융합교과 개발 확대</td>
          <td>학사지원팀, 교양교육원</td>
        </tr>
      </tbody>
    </table>
    <div class="plan-narrative analysis">
      <p>○ 상기 환류사항은 2026학년도 실행계획·성과지표 목표 조정에 반영한다.</p>
      <p class="sub">- 달성률 70% 미만 지표(MVP 인증, 유학생, 평생교육, SU-edx)는 담당 부서 실행계획과 연계하여 분기 점검한다.</p>
      <p class="sub">- 구성지표 목표와 연도 목표 불일치는 지수 산정 기준을 단일화한 뒤 차기 연차평가에 적용한다.</p>
      <p class="sub">- 교육혁신 상승분(콘텐츠·혁신형 전공·학사제도)은 유지 관리하고, 융합형 교과는 중장기 ’25 목표(0.3%) 달성을 재추진한다.</p>
    </div>
  </section>
    """


def depts_of(comp):
    names = []
    for s in comp.get("subs") or []:
        d = s.get("dept")
        if d and d not in names:
            names.append(d)
    return "<br>".join(names) if names else "—"


def normalize(indices):
    by_id = {str(x["id"]): x for x in indices}
    for idx in by_id.values():
        for c in idx["components"]:
            formula = c["formula"]
            if c["id"] == "100300":
                formula = "A / B × 100"
                c["formula"] = formula
                c["unit"] = "%"
            if formula == "A / B+C":
                formula = "A / (B + C)"
                c["formula"] = formula
            a24 = eval_formula(formula, vars_of(c, True, "24"))
            t24 = c.get("t24")
            a25 = eval_formula(formula, vars_of(c, True, "25"))
            t25 = eval_formula(formula, vars_of(c, False, "25"))
            if c["id"] == "100300":
                a_row = next((s for s in c["subs"] if s.get("var") == "A"), None)
                b_row = next((s for s in c["subs"] if s.get("var") == "B"), None)
                if a_row and b_row:
                    if a_row.get("a24") and b_row.get("t24"):
                        a24 = a_row["a24"] / b_row["t24"] * 100
                    if a_row.get("a25") and b_row.get("t25"):
                        a25 = a_row["a25"] / b_row["t25"] * 100
                    t25 = 100.0
                    t24 = 100.0
                    c["t24"] = 100.0
            if a24 is not None:
                c["a24_calc"] = a24
            else:
                c["a24_calc"] = c.get("a24")
            c["a25_calc"] = a25 if a25 is not None else c.get("a25")
            c["t25_calc"] = t25 if t25 is not None else c.get("t25_admin")
            c["rate25_admin"] = cap(c["a25_calc"], c["t25_calc"])
            c["rate25_index"] = cap(c["a25_calc"], t24)
            c["rate24"] = cap(c["a24_calc"], t24)
    return by_id


def _an(*rows):
    parts = []
    for mark, text in rows:
        cls = ' class="sub"' if mark == "-" else ""
        parts.append(f"<p{cls}>{mark} {text}</p>")
    return "\n        ".join(parts)


def analysis_for(iid, idx):
    texts = {
        "10000": _an(
            ("○", "지수 85.3점 → 89.1점(+3.8점)"),
            ("-", "학사제도 참여율 27.38% → 44.82%(4,601/10,265명), 목표 상회"),
            ("-", "융합형 교과 0.10% → 0.13%, 중장기 ’25 목표(0.3%) 대비 취약"),
            ("-", "교수법 참여인원 64명 → 43명(목표 달성), 1인당 참여시간 2.32시간 → 4.13시간"),
            ("-", "전임교원 복합지수 76.21, 2025 목표(80.50) 대비 94.7%, 구성지표 목표(152.5) 대비 50.0%"),
        ),
        "20000": _an(
            ("○", "지수 75.5점 → 96.6점(+21.1점)"),
            ("-", "혁신형 전공 교과 4.0% → 27.68%(328/1,185과목), 목표(21.25%) 상회"),
            ("-", "SU 핵심역량 58.5점, SU 전공능력 3.43점 — 목표 달성"),
            ("-", "디지털·융합 교양 5.64%(11/195), 목표(6.52%) 대비 86.5%"),
        ),
        "30000": _an(
            ("○", "지수 61.7점 → 100.0점(+38.3점)"),
            ("-", "교육콘텐츠 90차시 → 874차시, 목표(550차시) 상회"),
            ("-", "SU-MVP교수법 적용 교과 5% → 12.91%(153/1,185), 목표(6.11%) 상회"),
            ("-", "에듀테크 강의실 개선 5건 → 8건"),
        ),
        "40000": _an(
            ("○", "지수 100.0점 유지"),
            ("-", "거버넌스 이행 21/21, 비교과 참여율 852.7%, 인성교육 37.33% — 목표 상회"),
            ("-", "질 관리 인증 63.46(인증 교과 165과목 / 전임교원 평균 교과 2.6과목)"),
        ),
        "50000": _an(
            ("○", "지수 94.6점 → 98.1점(+3.5점)"),
            ("-", "역량증진 8.05 → 13.62, 개별화 교육 211.5 → 228.8건/인 — 목표 상회"),
            ("-", "학습역량강화 성장지수 38.55점, 목표(38.68) 대비 99.7%"),
            ("-", "학업생활 만족도 75점 → 69점, 목표(71.5) 대비 96.5%"),
        ),
        "60000": _an(
            ("○", "지수 88.8점 → 71.9점(−16.9점)"),
            ("-", "삼육 MVP 인증 1.12% → 0.48%(6/1,249명), 목표(1.89%) 대비 25.4%"),
            ("-", "진로·취창업 프로그램 개편 34% → 22.3%, 2025 목표(17.3%)는 달성, 구성지표 목표(36%) 대비 62.1%"),
            ("-", "혁신형 신규개발 2건, 취창업 교과 39건 — 목표 달성"),
        ),
        "70000": _an(
            ("○", "지수 93.1점 → 100.0점(+6.9점)"),
            ("-", "국제논문 0.29편, 연구역량 이행 6/6, 융합연구 13건 — 목표 달성"),
            ("-", "대학원 교육 혁신 13건 → 20건, 2025 목표(22건) 대비 90.9%"),
        ),
        "90000": _an(
            ("○", "지수 91.1점 → 91.0점(보합)"),
            ("-", "산학연계교육 18.19% → 13.46%, 목표(11.05%) 상회"),
            ("-", "산업체 만족도 69.61점 → 76점, 목표(74점) 상회"),
            ("-", "가족회사 432건 → 465건, 목표(516건) 대비 90.1%"),
            ("-", "산학협력 역량강화 이행률 87% → 73.75%(59/80)"),
        ),
        "80000": _an(
            ("○", "지수 64.2점 → 82.4점(+18.2점)"),
            ("-", "서비스러닝 만족도 93점, 대외협력 협약 24건 — 목표 달성"),
            ("-", "평생교육 참여자 6,892명 → 7,049명(평생교육원 1,220 + 체육문화센터 5,829), 목표(11,084명) 대비 63.6%"),
            ("-", "SU-edx 참여 0.38% → 0.52%(53/10,265명), 목표(0.78%) 대비 66.4%"),
        ),
        "91000": _an(
            ("○", "지수 71.2점 → 69.6점(−1.6점)"),
            ("-", "신입생 교육만족도 66.89점 → 69.31점, 목표(67.6점) 달성"),
            ("-", "외국인 유학생 608명 → 550명, 목표(1,400명) 대비 39.3%(학부 187, 연수 174, 대학원 189)"),
        ),
        "100000": _an(
            ("○", "지수 96.6점 → 100.0점(+3.4점)"),
            ("-", "재정수입 확충 68%, 등록금 외 수입 85%, 예산 집행률 103.8% — 목표 달성"),
            ("-", "기부금 결산 29.09억 / 목표 22.42억(129.8%)"),
        ),
        "110000": _an(
            ("○", "지수 89.6점 → 98.0점(+8.4점)"),
            ("-", "캠퍼스 시설 만족도 65.72점 → 75점, 정보화 이행 95.7%, 외부 수요자 만족도 74점 — 목표 달성"),
            ("-", "의사결정 참여 1.57건/인(694명 / 교원 190+직원 252)"),
            ("-", "교직원 1인당 교육훈련 5.94건(1,502/253), 목표(6.59건) 대비 90.1%"),
        ),
    }
    return texts.get(iid, "<p>○ 하위 지표 실적을 표와 함께 확인함.</p>")


CSS = """
    @page { size: A4; margin: 14mm 11mm 16mm; }
    * { box-sizing: border-box; }
    html { font-family: "Malgun Gothic", "Noto Sans KR", sans-serif; color: #111; }
    body { margin: 0; font-size: 9.2pt; line-height: 1.48; }
    .cover {
      height: 255mm; display: flex; flex-direction: column;
      align-items: center; justify-content: center; text-align: center;
      break-after: page;
    }
    .cover .year { font-size: 15pt; letter-spacing: .12em; margin-bottom: 12mm; }
    .cover h1 { font-size: 24pt; margin: 0; letter-spacing: -.04em; line-height: 1.35; }
    .cover .subtitle { margin-top: 8mm; font-size: 13pt; color: #444; }
    .cover .date { margin-top: 56mm; font-size: 13pt; }
    .cover .office { margin-top: 7mm; font-size: 16pt; font-weight: 700; }
    .intro-page, .summary-section, .index-section { break-after: page; }
    .overall-section { break-before: page; }
    .area-section { break-inside: avoid; margin-bottom: 5mm; }
    h1.report-title { text-align: center; font-size: 19pt; margin: 0 0 8mm; }
    h2 { margin: 0 0 3mm; font-size: 15pt; }
    h3 { margin: 6mm 0 2.5mm; font-size: 11.5pt; }
    .area-kicker { font-size: 9pt; color: #555; letter-spacing: .08em; margin-bottom: 2mm; }
    .notice {
      margin: 0 0 3.5mm; padding: 2.5mm 3mm; border-left: 3px solid #777;
      background: #f4f4f4; color: #444; font-size: 8pt; line-height: 1.5;
    }
    .toc { margin: 0; padding: 0; list-style: none; }
    .toc li { margin: 0 0 4mm; border-bottom: .3mm solid #aaa; padding-bottom: 2mm; }
    .toc strong { display: block; font-size: 10.5pt; }
    .toc span { display: block; margin-top: 1mm; color: #444; font-size: 8.5pt; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin: 0 0 4mm; }
    thead { display: table-header-group; }
    th, td { border: .25mm solid #555; padding: 1.7mm 1.5mm; vertical-align: middle; word-break: keep-all; overflow-wrap: anywhere; }
    th { background: #ececec; text-align: center; font-weight: 700; }
    tbody tr { break-inside: avoid-page; }
    .group-cell { text-align: center; font-weight: 700; background: #f7f7f7; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .grade { text-align: center; font-weight: 700; }
    .up { color: #1d4d2c; }
    .down { color: #7a2e24; }
    .flat { color: #444; }
    .index-title {
      display: flex; align-items: baseline; gap: 4mm;
      border-bottom: .7mm solid #111; padding-bottom: 2.5mm; margin-bottom: 5mm;
    }
    .index-title span { font-size: 9pt; color: #555; min-width: 18mm; }
    .plan-narrative {
      border: .25mm solid #555; padding: 4mm;
      white-space: normal; font-size: 9pt; line-height: 1.55;
    }
    .analysis p { margin: 0 0 1.2mm; }
    .analysis p:last-child { margin-bottom: 0; }
    .analysis p.sub { padding-left: 4.5mm; }
    .analysis-cell { text-align: left; font-size: 8.2pt; line-height: 1.45; }
    .chart-box { margin: 1mm 0 4mm; padding: 2.5mm 2mm 2mm; border: .25mm solid #bbb; background: #fafafa; break-inside: avoid; }
    .chart-cap { text-align: center; font-size: 8pt; color: #555; margin: 1.5mm 0 0; }
    .reflux-table { font-size: 8.1pt; }
    .reflux-table td:nth-child(1) { text-align: center; }
    .reflux-table td:nth-child(2) { font-weight: 700; }
    .sub-table { font-size: 8pt; }
    .link-table .link-label { text-align: center; font-weight: 700; background: #f3f3f3; }
    .link-table .link-plan { text-align: left; }
    .score-head th {
      background: #d8d8d8; font-size: 11pt; text-align: left;
      padding: 2.4mm 3mm;
    }
    .score-head .pts { float: right; font-size: 12.5pt; font-weight: 700; }
    .score-head .pts .delta { font-size: 12.5pt; margin-left: 0; }
    .score-head .prev { font-size: 8pt; font-weight: 400; margin-left: 3.5mm; color: #444; }
    .col-y24 { background: #f7f7f7; }
    .col-y25a { background: #eef6ef; }
    .formula-sys { font-weight: 700; font-variant-numeric: tabular-nums; }
    .formula-vars { margin-top: .7mm; font-size: 7.2pt; color: #333; line-height: 1.4; }
    .indicator-name { font-weight: 700; }
    @media screen {
      body { max-width: 210mm; margin: 0 auto; padding: 12mm; background: white; }
      .intro-page, .summary-section, .area-section, .index-section, .cover, .overall-section {
        border-bottom: 1px dashed #aaa; padding-bottom: 10mm; margin-bottom: 10mm;
      }
    }
"""


def trend_get(comp, year, field):
    for t in comp.get("trend") or []:
        if t.get("year") == year:
            return t.get(field)
    return None


def period_target(comp, years):
    vals = [trend_get(comp, y, "target") for y in years]
    vals = [v for v in vals if isinstance(v, (int, float))]
    return vals[-1] if vals else None


def render_index(iid, idx):
    meta = META[iid]
    s24 = SCORE_2024[iid]
    s25 = float(idx["score"])
    strat_no = meta["no"].split("-")[1]
    tasks = meta["tasks"]
    n_task = len(tasks)

    task_html = []
    for i, (task, indicator) in enumerate(tasks):
        if i == 0:
            task_html.append(
                f'<tr><td rowspan="{n_task}" class="link-label">실행과제</td>'
                f'<td class="link-plan">{task}</td>'
                f'<td class="indicator-name">{indicator}</td></tr>'
            )
        else:
            task_html.append(
                f'<tr><td class="link-plan">{task}</td>'
                f'<td class="indicator-name">{indicator}</td></tr>'
            )

    goal_rows = []
    actual_rows = []
    for i, c in enumerate(idx["components"], 1):
        unit = c.get("unit") or ""
        a22 = trend_get(c, 2022, "actual")
        a23 = trend_get(c, 2023, "actual")
        a24_hist = c.get("a24_calc")
        if a24_hist is None:
            a24_hist = trend_get(c, 2024, "actual")
        t25 = trend_get(c, 2025, "target")
        if t25 is None:
            t25 = c.get("t25_calc")
        t2627 = period_target(c, [2026, 2027])
        t2830 = period_target(c, [2028, 2029, 2030])
        goal_rows.append(
            f"""<tr>
            <td>{c['name']}</td>
            <td class="num">{c['weight']}%</td>
            <td class="num">{fmt_u(a22, unit)}</td>
            <td class="num">{fmt_u(a23, unit)}</td>
            <td class="num col-y24">{fmt_u(a24_hist, unit)}</td>
            <td class="num">{fmt_u(t25, unit)}</td>
            <td class="num">{fmt_u(t2627, unit)}</td>
            <td class="num">{fmt_u(t2830, unit)}</td>
            </tr>"""
        )
        actual_rows.append(
            f"""<tr>
            <td>{c['name']}</td>
            <td class="num">{c['weight']}%</td>
            <td class="num col-y24">{fmt_u(c.get('a24_calc'), unit)}</td>
            <td class="num col-y25a">{fmt_u(c.get('a25_calc'), unit)}</td>
            <td>{formula_cell(c)}</td>
            <td>{depts_of(c)}</td>
            </tr>"""
        )

    d = round(s25 - s24, 1)
    if abs(d) < 0.05:
        dhtml = ""
    elif d > 0:
        dhtml = f'<span class="delta up">(+{d}점)</span>'
    else:
        dhtml = f'<span class="delta down">(−{abs(d)}점)</span>'

    return f"""
  <section class="index-section">
    <header class="index-title"><span>{meta['no']}</span><h2>{meta['strategy']}</h2></header>

    <h3>■ 중장기발전계획-성과지표 연계</h3>
    <table class="link-table">
      <thead>
        <tr>
          <th style="width:16%"></th>
          <th style="width:46%">중장기발전계획</th>
          <th style="width:38%">성과지표</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="link-label">4대 전략방향</td>
          <td colspan="2">{meta['cat']}</td>
        </tr>
        <tr>
          <td class="link-label">12대 중점전략</td>
          <td class="link-plan">{strat_no}. {meta['strategy']}</td>
          <td class="indicator-name">{idx['name']}</td>
        </tr>
        {''.join(task_html)}
      </tbody>
    </table>

    <h3>■ 성과지표 목표</h3>
    <table class="sub-table">
      <thead>
        <tr>
          <th rowspan="2" style="width:28%">하위 지표</th>
          <th rowspan="2" style="width:8%">구성 비율</th>
          <th colspan="3">과거 실적</th>
          <th colspan="3">연차별 달성목표</th>
        </tr>
        <tr>
          <th>2022</th><th>2023</th><th>2024</th>
          <th>2025</th><th>’26~’27</th><th>’28~’30</th>
        </tr>
      </thead>
      <tbody>
        {''.join(goal_rows)}
      </tbody>
    </table>

    <h3>■ 성과지표 실적</h3>
    <table class="sub-table">
      <thead>
        <tr class="score-head">
          <th colspan="6">
            {idx['name']} 실적(2025)
            <span class="pts">
              {s25:.1f}점{dhtml}
              <span class="prev">2024년 {s24:.1f}점</span>
            </span>
          </th>
        </tr>
        <tr>
          <th style="width:22%">하위 지표</th>
          <th style="width:8%">구성 비율</th>
          <th style="width:11%" class="col-y24">실적(2024)</th>
          <th style="width:11%" class="col-y25a">실적(2025)</th>
          <th style="width:32%">산출식</th>
          <th style="width:16%">담당부서</th>
        </tr>
      </thead>
      <tbody>
        {''.join(actual_rows)}
      </tbody>
    </table>

    <h3>■ 성과지표 분석</h3>
    <div class="plan-narrative analysis">
        {analysis_for(iid, idx)}
    </div>
  </section>
    """


def main():
    raw = json.loads(SRC.read_text(encoding="utf-8"))
    by_id = normalize(raw)

    summary_rows = []
    area_spans = [("고등교육<br>선도", 3), ("학생<br>미래비전", 3), ("사회<br>가치창출", 3), ("지속가능<br>경영", 3)]
    first_of_area = {0, 3, 6, 9}
    area_idx = 0
    for n, iid in enumerate(INDEX_ORDER):
        idx = by_id[iid]
        meta = META[iid]
        s24 = SCORE_2024[iid]
        s25 = float(idx["score"])
        if n in first_of_area:
            name, span = area_spans[area_idx]
            area_cell = f'<td rowspan="{span}" class="group-cell">{name}</td>'
            area_idx += 1
        else:
            area_cell = ""
        summary_rows.append(
            f"<tr>{area_cell}<td>{meta['strategy']}</td><td>{idx['name']}</td>"
            f'<td class="num">{s24:.1f}</td>{delta_html(s24, s25)}</tr>'
        )

    index_html = []
    for area in AREAS:
        index_html.append(
            f"""
  <section class="area-section">
    <div class="area-kicker">『SU-GLORY 플랜 2030』 종합성과관리지수 분석</div>
    <h2>{area['title']}</h2>
    {area_summary_table(area, by_id)}
  </section>
            """
        )
        for iid in area["ids"]:
            index_html.append(render_index(iid, by_id[iid]))

    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>2025학년도 중장기발전계획 연차평가 보고서</title>
  <style>{CSS}</style>
</head>
<body>
  <section class="cover">
    <div class="year">2025학년도</div>
    <h1>중장기발전계획<br>연차평가 보고서</h1>
    <div class="subtitle">『SU-GLORY 플랜 2030』 성과관리종합지수 분석</div>
    <div class="date">2026. 08. 27.</div>
    <div class="office">기획처</div>
  </section>

  <section class="intro-page">
    <h1 class="report-title">목차</h1>
    <ul class="toc">
      <li><strong>성과관리종합지수 총괄</strong><span>12개 지수 점수 및 영역별 평균 (2024→2025)</span></li>
      <li><strong>Ⅰ. 고등교육 선도</strong><span>MVP Edu-Framework 혁신, MVP 교과교육 혁신, 스마트 융합형 교육방법 혁신</span></li>
      <li><strong>Ⅱ. 학생 미래비전</strong><span>MVP 교육 성과관리 강화, MVP 인재 성장, MVP 인재 사회기여 역량</span></li>
      <li><strong>Ⅲ. 사회 가치창출</strong><span>연구역량 강화, 산학협력 혁신, 공유·협력 혁신</span></li>
      <li><strong>Ⅳ. 지속가능 경영</strong><span>적정 규모화 관리, 재정 건전성 확보, 데이터 기반 대학 경영체계 구축</span></li>
      <li><strong>종합 분석</strong><span>영역별 추이, 향후 환류사항</span></li>
    </ul>
  </section>

  <section class="summary-section">
    <h1 class="report-title">2025학년도 중장기발전계획 성과관리종합지수 결과</h1>
    <table>
      <thead>
        <tr>
          <th style="width:14%">발전방향</th>
          <th style="width:28%">발전전략</th>
          <th style="width:30%">성과관리종합지수</th>
          <th style="width:14%">2024</th>
          <th style="width:14%">2025</th>
        </tr>
      </thead>
      <tbody>
        {''.join(summary_rows)}
      </tbody>
    </table>

    <h3>■ 영역별 평균</h3>
    <table>
      <thead>
        <tr><th>영역</th><th>2024</th><th>2025</th><th>증감</th><th>분석</th></tr>
      </thead>
      <tbody>
        <tr><td>Ⅰ. 고등교육 선도</td><td class="num">74.2</td><td class="num">95.2</td><td class="grade up">+21.0</td><td class="analysis-cell">○ 최대 상승<br>- 스마트 교육방법·교과혁신 견인</td></tr>
        <tr><td>Ⅱ. 학생 미래비전</td><td class="num">94.5</td><td class="num">90.0</td><td class="grade down">−4.5</td><td class="analysis-cell">○ 성과관리·성장 유지<br>- 사회기여 하락이 영역 평균 압박</td></tr>
        <tr><td>Ⅲ. 사회 가치창출</td><td class="num">82.8</td><td class="num">91.1</td><td class="grade up">+8.3</td><td class="analysis-cell">○ 연구 만점, 공유·협력 견인<br>- 산학협력 보합, 평생교육·SU-edx 목표 미달</td></tr>
        <tr><td>Ⅳ. 지속가능 경영</td><td class="num">85.8</td><td class="num">89.2</td><td class="grade up">+3.4</td><td class="analysis-cell">○ 재정·경영체계 우수<br>- 유학생 규모화 미달</td></tr>
        <tr><td class="group-cell">전체 평균</td><td class="num">84.3</td><td class="num">91.4</td><td class="grade up">+7.1</td><td class="analysis-cell">○ 12개 중 8개 상승<br>- 2개 보합, 2개 하락</td></tr>
      </tbody>
    </table>

    <h3>■ 취약 하위 지표 (2025 목표 대비 달성률 70% 미만)</h3>
    <table class="sub-table">
      <thead><tr><th>지수</th><th>하위 지표</th><th>2025 실적</th><th>2025 목표</th><th>달성률</th><th>담당</th></tr></thead>
      <tbody>
        <tr><td>사회기여</td><td>삼육 MVP 인증획득 학생 비율</td><td class="num">0.48%</td><td class="num">1.89%</td><td class="num down">25.4%</td><td>비교과통합센터</td></tr>
        <tr><td>규모화</td><td>외국인 유학생 수</td><td class="num">550명</td><td class="num">1,400명</td><td class="num down">39.3%</td><td>국제처·대학원</td></tr>
        <tr><td>공유·협력</td><td>평생교육 프로그램 참여자 수</td><td class="num">7,049명</td><td class="num">11,084명</td><td class="num down">63.6%</td><td>평생교육원·체육문화센터</td></tr>
        <tr><td>공유·협력</td><td>SU-edx 참여 학생 비율</td><td class="num">0.52%</td><td class="num">0.78%</td><td class="num down">66.4%</td><td>국제처</td></tr>
      </tbody>
    </table>
  </section>

  {''.join(index_html)}

  {render_overall(by_id)}
</body>
</html>
"""
    OUT_HTML.write_text(html, encoding="utf-8")

    export = {
        "title": "SU-GLORY 플랜 2030 성과관리종합지수",
        "source": "https://cho.syu.my/performance/admin",
        "note": "2024·2025 성과관리종합지수 실적. 하위 실적·목표는 부서 제출값.",
        "generatedAt": "2026-08-27",
        "years": {
            "2024": {"scoreType": "실적"},
            "2025": {"scoreType": "실적"},
        },
        "indices": [],
    }
    for iid in INDEX_ORDER:
        idx = by_id[iid]
        meta = META[iid]
        rec = {
            "id": int(iid),
            "name": idx["name"],
            "no": meta["no"],
            "strategyName": meta["strategy"],
            "score2024": SCORE_2024[iid],
            "score2025": float(idx["score"]),
            "formula": idx.get("formula"),
            "indicators": [],
        }
        for c in idx["components"]:
            rec["indicators"].append(
                {
                    "id": c["id"],
                    "name": c["name"],
                    "weight": c["weight"],
                    "formula": c["formula"],
                    "unit": c.get("unit"),
                    "actual2024": c.get("a24_calc"),
                    "target2024": c.get("t24"),
                    "rate2024": c.get("rate24"),
                    "actual2025": c.get("a25_calc"),
                    "target2025": c.get("t25_calc"),
                    "rate2025": c.get("rate25_admin"),
                    "rate2025_indexScore": c.get("rate25_index"),
                    "trendTarget2025": c.get("t25_trend"),
                    "subs": c.get("subs"),
                }
            )
        export["indices"].append(rec)
    OUT_JSON.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", OUT_HTML, "bytes", OUT_HTML.stat().st_size)
    print("Wrote", OUT_JSON, "bytes", OUT_JSON.stat().st_size)


if __name__ == "__main__":
    main()
