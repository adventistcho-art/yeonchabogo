# -*- coding: utf-8 -*-
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

t = urllib.request.urlopen(
    "https://adventistcho-art.github.io/yeonchabogo/briefing.html", timeout=30
).read().decode("utf-8")
marker = '<script id="report-data" type="application/json">'
start = t.index(marker) + len(marker)
end = t.index("</script>", start)
raw = t[start:end]
dom_raw = ""  # simulate browser: get text from script element - same as raw for json script

print("raw len:", len(raw))
print("<!-- in json:", "<!--" in raw)

# Compare DOM parsing simulation - find if browser might truncate
# HTML5: in script, <!-- ... --> comments out until -->
if "<!--" in raw:
    idx = raw.index("<!--")
    print("first <!-- at", idx, raw[idx:idx+80])

try:
    data = json.loads(raw)
    print("JSON parse OK, depts:", len(data["departments"]))
except json.JSONDecodeError as e:
    print("JSON parse FAIL:", e)

# Check if script tag might be closed early by </script in content (case insensitive)
import re
for m in re.finditer(r"</script", raw, re.I):
    print("BAD </script at", m.start())
