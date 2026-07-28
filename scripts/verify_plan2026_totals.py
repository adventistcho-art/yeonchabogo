# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from plan2026_budget import enrich_plan2026_budgets

cfg = json.loads((ROOT / "scripts" / "config.json").read_text(encoding="utf-8"))
report = json.loads(Path(cfg["paths"]["reportJson"]).read_text(encoding="utf-8"))
ir_pdf_root = Path(cfg["paths"]["irPdfRoot"])
report = enrich_plan2026_budgets(report, ir_pdf_root, ROOT)

TARGETS = [
    "건축・안전관리팀",
    "교육미디어지원팀",
    "조경미화팀",
    "전기통신팀",
    "관재팀",
    "총무과",
    "기획처",
    "IR센터",
    "학생복지팀",
    "장애학생지원센터",
    "학생상담센터",
    "교목처",
    "인성교육원",
    "콘서바토리",
]


def fmt(n: int) -> str:
    if n >= 100_000_000:
        return f"{n / 100_000_000:.2f}억"
    if n >= 10_000:
        return f"{n / 10_000:.0f}만"
    return str(n)


print("부서 | 사업수 | 예산입력 | HTML합계")
for name in TARGETS:
    dept = next((d for d in report["departments"] if d["name"] == name), None)
    if not dept:
        print(f"{name} | NOT FOUND")
        continue
    projs = dept.get("projects", [])
    funded = sum(1 for p in projs if (p.get("budget2026") or 0) > 0)
    html_sum = sum(p.get("budget2026") or 0 for p in projs)
    print(f"{name} | {len(projs)} | {funded} | {fmt(html_sum)} ({html_sum:,})")
