# -*- coding: utf-8 -*-
"""Bind mid-term plan + department annual reports into one printable volume."""
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
MIDTERM_HTML = REPORTS / "2025학년도_중장기발전계획_연차평가_보고서.html"
DEPT_HTML = REPORTS / "2025학년도_부서연차평가_보고서_합본.html"
OUT_HTML = REPORTS / "2025학년도_연차평가_보고서.html"
OUT_PDF = REPORTS / "2025학년도_연차평가_보고서.pdf"

ISSUED = "2026. 08. 27."
ISSUED_KO = "2026년 8월 27일"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="2025학년도 연차평가 보고서 합본 생성")
    parser.add_argument("--html-only", action="store_true", help="PDF를 만들지 않고 HTML만 생성")
    return parser.parse_args()


def extract_parts(html: str) -> tuple[str, str]:
    style_m = re.search(r"<style>(.*?)</style>", html, re.S)
    body_m = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
    style = style_m.group(1) if style_m else ""
    body = body_m.group(1).strip() if body_m else ""
    style = re.sub(r"@page\s*\{[^}]*\}", "", style)
    return style, body


COMBINED_CSS = """
    @page {
      size: A4;
      margin: 14mm 11mm 18mm;
    }
    * { box-sizing: border-box; }
    html { font-family: "Malgun Gothic", "Noto Sans KR", sans-serif; color: #111;
      -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    body { margin: 0; font-size: 9.2pt; line-height: 1.48; }
    h1, h2, h3, .index-title, .department-title {
      break-after: avoid;
      page-break-after: avoid;
      break-inside: avoid;
      page-break-inside: avoid;
    }
    h3 + table, h3 + .plan-narrative, h3 + .chart-box,
    h3 + .calculation-note, h3 + .source-note, h3 + .notice,
    .calculation-note + table, .source-note + table,
    .index-title + table, .department-title + h3 {
      break-before: avoid;
      page-break-before: avoid;
    }
    table {
      page-break-inside: auto;
      break-inside: auto;
    }
    thead { display: table-header-group; }
    tfoot { display: table-footer-group; }
    tbody { display: table-row-group; }
    tr { break-inside: avoid; page-break-inside: avoid; }
    caption.continued-cap {
      caption-side: top; text-align: right; font-size: 8pt; color: #666;
      padding: 0 0 1.2mm; font-weight: 400;
    }
    .print-chunk { margin-bottom: 3mm; }
    .print-chunk-cont { break-before: page; page-break-before: always; margin-top: 0; }
    table.keep-table,
    #vol-midterm .summary-section > table,
    .grade-table, .metric-table {
      break-inside: avoid;
      page-break-inside: avoid;
    }
    #vol-midterm .index-section {
      break-after: auto !important;
      page-break-after: auto !important;
    }
    #vol-midterm .area-section {
      break-before: page;
      page-break-before: always;
    }
    #vol-midterm .index-section.index-break-before {
      break-before: page;
      page-break-before: always;
    }
    /* Chromium often ignores break-inside on tables; wrap blocks in divs instead. */
    #vol-midterm .index-block-goals,
    #vol-midterm .index-block-result,
    #vol-midterm .index-keep {
      break-inside: avoid;
      page-break-inside: avoid;
    }
    #vol-midterm .index-section table {
      break-inside: avoid;
      page-break-inside: avoid;
      margin: 0 0 1.5mm;
    }
    #vol-midterm .index-title {
      display: flex; align-items: flex-start; gap: 3.5mm;
      margin-bottom: 2.4mm; padding-bottom: 1.5mm;
    }
    #vol-midterm .index-title > span { min-width: 15mm; font-size: 10.5pt; }
    #vol-midterm .index-title h2 { margin: 0; font-size: 14.5pt; line-height: 1.32; }
    #vol-midterm .index-title .index-indicator {
      margin: 0.8mm 0 0; font-size: 12.5pt; font-weight: 700; line-height: 1.32;
    }
    #vol-midterm .index-section h3 { margin: 2.2mm 0 1.1mm; }
    #vol-midterm .index-section th,
    #vol-midterm .index-section td { padding: 0.95mm 1.05mm; }
    #vol-midterm .index-section .plan-narrative {
      padding: 1.8mm 2.3mm;
      break-inside: avoid;
      page-break-inside: avoid;
    }
    #vol-midterm .index-section h3 {
      break-after: avoid;
      page-break-after: avoid;
    }
    #vol-midterm .index-section h3 + table,
    #vol-midterm .index-section h3 + .plan-narrative {
      break-before: avoid;
      page-break-before: avoid;
    }
    #vol-midterm .index-section .score-head th { padding: 1.5mm 2.2mm; font-size: 10.5pt; }
    #vol-midterm .index-section .formula-vars { margin-top: .25mm; }
    #vol-midterm .index-section.index-fit-page { line-height: 1.38; }
    #vol-midterm .index-section.index-fit-page .sub-table { font-size: 7.7pt; }
    #vol-midterm .index-section.index-fit-page .index-title {
      margin-bottom: 1.6mm; padding-bottom: 1.1mm;
    }
    #vol-midterm .index-section.index-fit-page .index-title h2 { font-size: 13.5pt; }
    #vol-midterm .index-section.index-fit-page .index-indicator { font-size: 11.5pt; }
    #vol-midterm .index-section.index-fit-page h3 { margin: 1.5mm 0 0.7mm; font-size: 11pt; }
    #vol-midterm .index-section.index-fit-page table { margin: 0 0 1mm; }
    #vol-midterm .index-section.index-fit-page th,
    #vol-midterm .index-section.index-fit-page td { padding: 0.72mm 0.95mm; }
    #vol-midterm .index-section.index-fit-page .plan-narrative { padding: 1.3mm 2mm; }
    #vol-midterm .index-section.index-fit-page .score-head th { padding: 1.15mm 2mm; font-size: 10pt; }
    #vol-midterm .index-section.index-fit-page .formula-vars { margin-top: .15mm; line-height: 1.28; }
    #vol-midterm .index-section.index-fit-page .analysis p { margin: 0 0 0.55mm; }
    #vol-midterm .index-fill th,
    #vol-midterm .index-fill td,
    #vol-midterm .index-section.index-fit-page .index-fill th,
    #vol-midterm .index-section.index-fit-page .index-fill td {
      padding-top: calc(1.15mm + var(--fill-pad, 0px));
      padding-bottom: calc(1.15mm + var(--fill-pad, 0px));
      padding-left: 1.2mm;
      padding-right: 1.2mm;
    }
    #vol-midterm .index-fill h3,
    #vol-midterm .index-section.index-fit-page .index-fill h3 {
      margin-top: calc(2.8mm + var(--fill-gap, 0px));
      margin-bottom: calc(1.5mm + var(--fill-gap, 0px));
      font-size: 11.5pt;
    }
    #vol-midterm .index-fill table {
      height: auto;
      margin-bottom: calc(2.2mm + var(--fill-gap, 0px));
    }
    #vol-midterm .index-fill .index-title {
      margin-bottom: calc(3mm + var(--fill-gap, 0px));
      padding-bottom: 2mm;
    }
    #vol-midterm .index-fill .plan-narrative {
      padding: calc(2.6mm + var(--fill-pad, 0px)) 3mm;
      line-height: 1.62;
    }
    #vol-midterm .index-fill .score-head th {
      padding: calc(2.2mm + var(--fill-pad, 0px)) 2.8mm;
      font-size: 11.2pt;
    }
    #vol-midterm .index-fill .sub-table { font-size: 8.4pt; }
    #vol-midterm .index-fill .formula-vars { margin-top: .45mm; line-height: 1.45; }
    #vol-midterm .index-fill .analysis p { margin: 0 0 1.1mm; }
    #vol-dept .plan-narrative {
      min-height: 0;
      padding: 3mm;
      line-height: 1.55;
      break-inside: avoid;
      page-break-inside: avoid;
    }
    #vol-dept .dept-plan-keep,
    #vol-dept .dept-tail-keep {
      break-inside: avoid;
      page-break-inside: avoid;
    }
    #vol-dept .dept-plan-keep.dept-plan-flow,
    #vol-dept .dept-plan-flow .plan-narrative {
      break-inside: auto;
      page-break-inside: auto;
    }
    #vol-dept .grade-table {
      break-after: avoid;
      page-break-after: avoid;
    }
    #vol-dept h3 + .plan-narrative,
    #vol-dept h3 + .dept-plan-keep {
      break-before: avoid;
      page-break-before: avoid;
    }
    #vol-dept .department-section.dept-trim-overflow .plan-narrative { padding: 2.2mm 3mm; }
    #vol-dept .department-section.dept-trim-overflow table { margin-bottom: 2.5mm; }
    #vol-dept .department-section.dept-trim-overflow h3 { margin: 4.5mm 0 2mm; }
    .front-cover {
      height: 255mm; display: flex; flex-direction: column;
      align-items: center; justify-content: center; text-align: center;
      break-after: page; page-break-after: always;
    }
    .front-cover .univ { font-size: 13pt; letter-spacing: .18em; color: #444; margin-bottom: 18mm; }
    .front-cover .year { font-size: 16pt; letter-spacing: .16em; margin-bottom: 10mm; }
    .front-cover h1 { font-size: 30pt; margin: 0; letter-spacing: -.04em; line-height: 1.3; }
    .front-cover .parts { margin-top: 10mm; font-size: 12pt; color: #444; line-height: 1.7; }
    .front-cover .date { margin-top: 52mm; font-size: 13pt; }
    .front-cover .office { margin-top: 7mm; font-size: 16pt; font-weight: 700; }
    .volume-toc { break-after: page; page-break-after: always; }
    .volume-toc ol { margin: 8mm 0 0; padding: 0; list-style: none; }
    .volume-toc li { margin: 0 0 8mm; border-bottom: .3mm solid #aaa; padding-bottom: 4mm; }
    .volume-toc .vol-no { font-size: 10pt; color: #555; letter-spacing: .08em; }
    .volume-toc strong { display: block; margin-top: 1.5mm; font-size: 14pt; }
    .volume-toc span { display: block; margin-top: 1.5mm; color: #444; font-size: 9pt; }
    #vol-dept { break-before: page; page-break-before: always; }
    .colophon {
      break-before: page; page-break-before: always;
      min-height: 255mm; display: flex; flex-direction: column; justify-content: flex-end;
      padding-bottom: 8mm;
    }
    .colophon-rule { border-top: .7mm solid #111; margin-bottom: 7mm; }
    .colophon h2 { font-size: 13pt; margin: 0 0 6mm; }
    .colophon-meta { width: 100%; border-collapse: collapse; table-layout: fixed; margin: 0 0 6mm; }
    .colophon-meta th, .colophon-meta td {
      border: 0; border-bottom: .2mm solid #ccc; padding: 2.4mm 2mm; text-align: left;
      background: none; font-weight: 400; vertical-align: top;
    }
    .colophon-meta th { width: 28mm; font-weight: 700; color: #333; }
    .colophon-note { margin: 0; font-size: 8.5pt; color: #444; line-height: 1.6; }
    .chart-box, .cover, .department-divider, .front-cover { break-inside: avoid; }
    @media screen {
      body { max-width: 210mm; margin: 0 auto; padding: 12mm; background: white; }
      .front-cover, .volume-toc, .volume, .colophon {
        border-bottom: 1px dashed #aaa; padding-bottom: 10mm; margin-bottom: 10mm;
      }
    }
    @media print {
      .front-cover, .volume-toc, .colophon { border: 0; margin: 0; padding: 0; }
    }
"""

PREPARE_PRINT_JS = r"""
<script>
(function () {
  function mm(px) { return px * 25.4 / 96; }
  function rowGroups(rows) {
    var groups = [];
    var i = 0;
    while (i < rows.length) {
      var span = 1;
      var cells = rows[i].cells;
      for (var c = 0; c < cells.length; c++) {
        if ((cells[c].rowSpan || 1) > span) span = cells[c].rowSpan;
      }
      groups.push(Array.prototype.slice.call(rows, i, i + span));
      i += span;
    }
    return groups;
  }
  function groupHeight(rows) {
    var h = 0;
    for (var i = 0; i < rows.length; i++) h += rows[i].getBoundingClientRect().height;
    return mm(h);
  }
  function fillBlock(el, budgetPx) {
    if (!el) return;
    var h0 = el.getBoundingClientRect().height;
    var spare = budgetPx - h0;
    if (spare < 36) return;
    var rows = el.querySelectorAll("tbody tr").length || 6;
    var heads = el.querySelectorAll("h3, .index-title").length || 2;
    var unit = (spare * 0.55) / (2 * rows + 3 * heads + 4);
    var padPx = Math.min(Math.max(unit, 1.5), 22);
    var gapPx = Math.min(Math.max(unit * 1.05, 1.2), 16);
    el.classList.add("index-fill");
    el.style.setProperty("--fill-pad", padPx + "px");
    el.style.setProperty("--fill-gap", gapPx + "px");
    void el.offsetHeight;
    var h = el.getBoundingClientRect().height;
    var n = 0;
    while (h > budgetPx - 10 && n < 7) {
      padPx *= 0.72;
      gapPx *= 0.72;
      el.style.setProperty("--fill-pad", padPx + "px");
      el.style.setProperty("--fill-gap", gapPx + "px");
      void el.offsetHeight;
      h = el.getBoundingClientRect().height;
      n++;
    }
    if (h > budgetPx - 8) {
      el.classList.remove("index-fill");
      el.style.removeProperty("--fill-pad");
      el.style.removeProperty("--fill-gap");
      return;
    }
    var still = budgetPx - 18 - el.getBoundingClientRect().height;
    if (still > 18) {
      var tables = Array.prototype.slice.call(el.querySelectorAll("table"));
      var box = el.querySelector(".plan-narrative");
      if (box) {
        var boxShare = still * 0.22;
        box.style.minHeight = (box.getBoundingClientRect().height + boxShare) + "px";
        still -= boxShare;
      }
      if (tables.length && still > 12) {
        var share = still / tables.length;
        tables.forEach(function (tb) {
          tb.style.height = (tb.getBoundingClientRect().height + share) + "px";
        });
      }
    }
  }
  window.__preparePrint = function () {
    if (document.body.dataset.printSplit === "1") return;
    document.body.dataset.printSplit = "1";
    var pagePx = 267 * 96 / 25.4;
    document.querySelectorAll("#vol-midterm .index-section").forEach(function (sec) {
      var prev = sec.previousElementSibling;
      var followsArea = prev && prev.classList.contains("area-section");
      if (!followsArea) {
        sec.classList.add("index-break-before");
      }
      var areaH = followsArea ? prev.getBoundingClientRect().height : 0;
      var kids = Array.prototype.filter.call(sec.children, function (el) {
        return el.nodeType === 1;
      });
      var resultStart = null;
      kids.forEach(function (el) {
        if (el.tagName === "H3" && /성과지표\s*실적/.test(el.textContent || "")) {
          resultStart = el;
        }
      });
      if (!resultStart) return;
      var goals = document.createElement("div");
      goals.className = "index-block-goals";
      var result = document.createElement("div");
      result.className = "index-block-result";
      var mode = "g";
      kids.forEach(function (el) {
        if (el === resultStart) mode = "r";
        (mode === "g" ? goals : result).appendChild(el);
      });
      sec.appendChild(goals);
      sec.appendChild(result);
      var h = sec.getBoundingClientRect().height;
      var limit = pagePx - (followsArea ? 14 : 8);
      function tryKeep() {
        sec.classList.add("keep-index");
        var pack = document.createElement("div");
        pack.className = "index-keep";
        pack.appendChild(goals);
        pack.appendChild(result);
        sec.appendChild(pack);
        void sec.offsetHeight;
        if (sec.getBoundingClientRect().height + areaH > pagePx - 2) {
          sec.classList.remove("keep-index");
          sec.appendChild(goals);
          sec.appendChild(result);
          pack.remove();
          return false;
        }
        return true;
      }
      var kept = false;
      if (h + areaH <= limit) {
        kept = tryKeep();
      } else {
        sec.classList.add("index-fit-page");
        void sec.offsetHeight;
        h = sec.getBoundingClientRect().height;
        if (h + areaH <= limit) kept = tryKeep();
        if (!kept) sec.classList.remove("index-fit-page");
      }
      if (kept) {
        if (!followsArea) fillBlock(sec.querySelector(".index-keep"), pagePx - 14);
      } else {
        if (followsArea) {
          fillBlock(goals, pagePx - areaH - 48);
          void goals.offsetHeight;
          if (areaH + goals.getBoundingClientRect().height > pagePx - 16) {
            goals.classList.remove("index-fill");
            goals.style.removeProperty("--fill-pad");
            goals.style.removeProperty("--fill-gap");
            Array.prototype.forEach.call(goals.querySelectorAll("table"), function (tb) {
              tb.style.height = "";
            });
            var box = goals.querySelector(".plan-narrative");
            if (box) box.style.minHeight = "";
          }
        } else {
          fillBlock(goals, pagePx - 14);
        }
        fillBlock(result, pagePx - 14);
      }
    });
    var tables = Array.prototype.slice.call(document.querySelectorAll("table"));
    tables.forEach(function (table) {
      if (table.closest(".front-cover, .colophon, .volume-toc, .cover, .department-divider")) return;
      if (table.closest(".keep-index, .index-section")) return;
      if (table.classList.contains("colophon-meta")) return;
      var thead = table.tHead;
      var tbody = table.tBodies && table.tBodies[0];
      if (!thead || !tbody) return;
      var rows = Array.prototype.slice.call(tbody.rows);
      if (rows.length < 4) return;
      var theadH = mm(thead.getBoundingClientRect().height) || 8;
      var groups = rowGroups(rows);
      var gHeights = groups.map(function (g) { return Math.max(groupHeight(g), 6); });
      var tall = gHeights.some(function (gh) { return gh > 85; });
      if (tall) return;
      var totalH = theadH;
      gHeights.forEach(function (gh) { totalH += gh; });
      if (totalH <= 245) {
        table.classList.add("keep-table");
        return;
      }
      var firstMax = 200;
      var restMax = 230;
      var chunks = [];
      var chunkHs = [];
      var cur = [];
      var h = theadH;
      var maxH = firstMax;
      groups.forEach(function (g, gi) {
        var gh = gHeights[gi];
        if (cur.length && h + gh > maxH) {
          chunks.push(cur);
          chunkHs.push(h);
          cur = [];
          h = theadH;
          maxH = restMax;
        }
        cur = cur.concat(g);
        h += gh;
      });
      if (cur.length) {
        chunks.push(cur);
        chunkHs.push(h);
      }
      while (chunks.length >= 2 && chunkHs[chunkHs.length - 1] < theadH + 48) {
        var last = chunks.pop();
        var lastH = chunkHs.pop();
        var merged = chunkHs[chunkHs.length - 1] + (lastH - theadH);
        if (merged > 250) {
          chunks.push(last);
          chunkHs.push(lastH);
          break;
        }
        chunks[chunks.length - 1] = chunks[chunks.length - 1].concat(last);
        chunkHs[chunkHs.length - 1] = merged;
      }
      if (chunks.length < 2) {
        table.classList.add("keep-table");
        return;
      }
      var parent = table.parentNode;
      chunks.forEach(function (chunkRows, idx) {
        var clone = table.cloneNode(false);
        clone.classList.add("print-chunk");
        if (idx > 0) {
          clone.classList.add("print-chunk-cont");
          var cap = document.createElement("caption");
          cap.className = "continued-cap";
          cap.textContent = "〈계속〉";
          clone.appendChild(cap);
        }
        clone.appendChild(thead.cloneNode(true));
        var tb = document.createElement("tbody");
        chunkRows.forEach(function (r) { tb.appendChild(r); });
        clone.appendChild(tb);
        parent.insertBefore(clone, table);
      });
      table.remove();
    });
    document.querySelectorAll("#vol-dept .department-section").forEach(function (sec) {
      var kids = Array.prototype.slice.call(sec.children);
      kids.forEach(function (el) {
        if (el.tagName !== "H3" || !/성과관리계획/.test(el.textContent || "")) return;
        var nxt = el.nextElementSibling;
        var wrap = document.createElement("div");
        wrap.className = "dept-plan-keep";
        el.parentNode.insertBefore(wrap, el);
        wrap.appendChild(el);
        if (nxt && nxt.classList && nxt.classList.contains("plan-narrative")) {
          wrap.appendChild(nxt);
        }
      });
      sec.querySelectorAll(".dept-plan-keep").forEach(function (wrap) {
        var nar = wrap.querySelector(".plan-narrative");
        if (!nar) return;
        var nh = mm(nar.getBoundingClientRect().height);
        if (nh > 70) {
          wrap.classList.add("dept-plan-flow");
          return;
        }
        var table = wrap.previousElementSibling;
        if (!table || table.tagName !== "TABLE") return;
        var gradeH3 = table.previousElementSibling;
        var gtxt = (gradeH3 && gradeH3.textContent) || "";
        if (!gradeH3 || gradeH3.tagName !== "H3" || !/평가결과/.test(gtxt) || /학년도/.test(gtxt)) return;
        var tail = document.createElement("div");
        tail.className = "dept-tail-keep";
        gradeH3.parentNode.insertBefore(tail, gradeH3);
        tail.appendChild(gradeH3);
        tail.appendChild(table);
        tail.appendChild(wrap);
      });
      var h = sec.getBoundingClientRect().height;
      var rem = h % pagePx;
      if (rem > 0 && rem < 18) sec.classList.add("dept-trim-overflow");
    });
  };
  window.addEventListener("beforeprint", function () {
    window.__preparePrint();
  });
})();
</script>
"""


def build_html(mid_style: str, mid_body: str, dept_style: str, dept_body: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>2025학년도 연차평가 보고서</title>
  <style>
{mid_style}
{dept_style}
{COMBINED_CSS}
  </style>
  {PREPARE_PRINT_JS}
</head>
<body>
  <section class="front-cover">
    <div class="univ">삼육대학교</div>
    <div class="year">2025학년도</div>
    <h1>연차평가 보고서</h1>
    <div class="parts">중장기발전계획 연차평가<br>부서별 연차평가</div>
    <div class="date">{ISSUED}</div>
    <div class="office">기획처</div>
  </section>

  <section class="volume-toc">
    <h1 class="report-title">목차</h1>
    <ol>
      <li>
        <div class="vol-no">제1편</div>
        <strong>중장기발전계획 연차평가 보고서</strong>
        <span>『SU-GLORY 플랜 2030』 성과관리종합지수 분석</span>
      </li>
      <li>
        <div class="vol-no">제2편</div>
        <strong>부서별 연차평가 보고서</strong>
        <span>부서별 연차평가 결과, 환류 내역 및 부서 연차보고서</span>
      </li>
    </ol>
  </section>

  <article id="vol-midterm" class="volume">
{mid_body}
  </article>

  <article id="vol-dept" class="volume">
{dept_body}
  </article>

  <section class="colophon">
    <div class="colophon-rule"></div>
    <h2>2025학년도 연차평가 보고서</h2>
    <table class="colophon-meta">
      <tbody>
        <tr><th>발 행 일</th><td>{ISSUED_KO}</td></tr>
        <tr><th>발 행 처</th><td>삼육대학교 기획처</td></tr>
        <tr><th>총 괄</th><td>윤재영 삼육대학교 기획처장</td></tr>
        <tr><th>편 집</th><td>기획처 기획팀</td></tr>
        <tr><th>주 소</th><td>서울특별시 노원구 화랑로 815</td></tr>
        <tr><th>전 화</th><td>02-3399-3395</td></tr>
        <tr><th>구 분</th><td>비매품</td></tr>
      </tbody>
    </table>
    <p class="colophon-note">본 보고서는 삼육대학교 『SU-GLORY 플랜 2030』 중장기발전계획 연차평가와 부서별 연차평가 결과를 수록함.</p>
  </section>
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
        page = browser.new_page(viewport={"width": 710, "height": 1008})
        page.set_default_timeout(300_000)
        page.goto(html_path.resolve().as_uri(), wait_until="load", timeout=120_000)
        page.emulate_media(media="print")
        page.wait_for_timeout(500)
        page.evaluate("() => window.__preparePrint && window.__preparePrint()")
        page.wait_for_timeout(300)
        page.pdf(
            path=str(temp_path),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            display_header_footer=True,
            header_template="<span></span>",
            footer_template=(
                '<div style="width:100%;font-size:8px;font-family:Malgun Gothic,sans-serif;'
                'text-align:center;color:#555;padding-top:4px;">'
                '<span class="pageNumber"></span>'
                "</div>"
            ),
            margin={"top": "14mm", "right": "11mm", "bottom": "16mm", "left": "11mm"},
        )
        browser.close()
    try:
        temp_path.replace(pdf_path)
        return pdf_path
    except PermissionError:
        revised = pdf_path.with_name(f"{pdf_path.stem}_수정본.pdf")
        try:
            temp_path.replace(revised)
            return revised
        except PermissionError:
            stamped = pdf_path.with_name(
                f"{pdf_path.stem}_수정본_{datetime.now().strftime('%H%M%S')}.pdf"
            )
            temp_path.replace(stamped)
            return stamped


def main() -> None:
    args = parse_args()
    if not MIDTERM_HTML.exists():
        raise SystemExit(f"중장기 보고서가 없습니다: {MIDTERM_HTML}")
    if not DEPT_HTML.exists():
        raise SystemExit(f"부서 보고서가 없습니다: {DEPT_HTML}")

    mid_style, mid_body = extract_parts(MIDTERM_HTML.read_text(encoding="utf-8"))
    dept_style, dept_body = extract_parts(DEPT_HTML.read_text(encoding="utf-8"))
    html = build_html(mid_style, mid_body, dept_style, dept_body)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML: {OUT_HTML} ({OUT_HTML.stat().st_size:,} bytes)")

    if args.html_only:
        return
    written = print_pdf(OUT_HTML, OUT_PDF)
    print(f"PDF: {written} ({written.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
