import json
from pathlib import Path

p = Path(r"F:\기획평가\2026\2025연차보고서\연차보고 시스템으로 정리\data\report2025.json")
data = json.loads(p.read_text(encoding="utf-8"))
d = data["departments"][5]
print("dept:", d["name"])
print("performance:", json.dumps(d.get("performance"), ensure_ascii=False, indent=2))
print("summary:", json.dumps(d.get("summary"), ensure_ascii=False, indent=2))
if d.get("projects"):
    print("project keys:", list(d["projects"][0].keys()))
