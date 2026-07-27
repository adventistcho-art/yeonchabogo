# -*- coding: utf-8 -*-
import json
import sys
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding="utf-8")

import urllib.request

html = urllib.request.urlopen(
    "https://adventistcho-art.github.io/yeonchabogo/briefing.html", timeout=30
).read().decode("utf-8")


class ScriptExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_report = False
        self.chunks = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            d = dict(attrs)
            if d.get("id") == "report-data":
                self.in_report = True

    def handle_endtag(self, tag):
        if tag == "script" and self.in_report:
            self.in_report = False

    def handle_data(self, data):
        if self.in_report:
            self.chunks.append(data)


p = ScriptExtractor()
p.feed(html)
dom_json = "".join(p.chunks)
print("DOM script text length:", len(dom_json))
print("String slice length:", len(html.split('type="application/json">', 1)[1].split("</script>", 1)[0]))

try:
    data = json.loads(dom_json)
    print("DOM JSON parse OK, depts:", len(data.get("departments", [])))
except json.JSONDecodeError as e:
    print("DOM JSON parse FAIL:", e)
    print("around error:", dom_json[max(0, e.pos - 50) : e.pos + 50])
