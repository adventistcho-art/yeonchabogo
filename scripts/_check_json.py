# -*- coding: utf-8 -*-
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

html = Path(__file__).resolve().parent.parent / "briefing.html"
text = html.read_text(encoding="utf-8")
marker = '<script id="report-data" type="application/json">'
start = text.index(marker) + len(marker)
end = text.index("</script>", start)
raw = text[start:end]

print("JSON length:", len(raw))
print("Contains </script>:", "</script>" in raw.lower() or "</script>" in raw)
print("Contains <:", "<" in raw)

try:
    data = json.loads(raw)
    print("Parse OK, departments:", len(data.get("departments", [])))
    d = next((x for x in data["departments"] if x["name"] == "교육미디어지원팀"), None)
    if d:
        plans = [p for p in d["projects"] if p.get("plan2026HtmlPath")]
        print("교육미디어 plan2026:", len(plans))
except json.JSONDecodeError as e:
    print("Parse FAIL:", e)

# check if HTML breaks due to </script> in JSON
if re.search(r"</script", raw, re.I):
    for m in re.finditer(r"</script", raw, re.I):
        pos = m.start()
        print("Found </script at", pos, "context:", repr(raw[max(0,pos-30):pos+20]))
