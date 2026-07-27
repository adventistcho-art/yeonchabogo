# -*- coding: utf-8 -*-
"""Fetch 신규 사업 metadata from SU-WINGs (사업계획서 등록)."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

from playwright.sync_api import Page, sync_playwright


@dataclass
class SuwingsBusiness:
    busi_name: str
    busi_code: str
    busi_class: str
    busi_class_code: str
    dept_name: str
    acnt_yy: str


def _get_form_window(page: Page):
    outer = page.frame_locator('iframe[src*="work_form"]')
    inner = outer.frame_locator("#ifrForm")
    handle = inner.element_handle(timeout=30000)
    if not handle:
        raise RuntimeError("SU-WINGs 사업계획서 등록 iframe을 찾지 못했습니다.")
    return handle.content_frame()


def login(page: Page, username: str, password: str) -> None:
    page.goto("https://suwings.syu.ac.kr/", wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(2000)
    if "login" not in page.url and "006197" in page.title():
        return

    for sel in ('input[name="id"]', "#userId"):
        if page.locator(sel).count():
            page.fill(sel, username)
            break
    for sel in ('input[name="pw"]', 'input[type="password"]'):
        if page.locator(sel).count():
            page.fill(sel, password)
            break
    for sel in ('input.signin', 'button:has-text("로그인")', 'input[type="submit"]'):
        if page.locator(sel).count():
            page.locator(sel).first.click()
            break

    for _ in range(30):
        page.wait_for_timeout(2000)
        if "main.xml" in page.url:
            return
    raise RuntimeError(f"SU-WINGs 로그인 실패: {page.url}")


def open_business_plan_register(page: Page) -> None:
    page.evaluate(
        """() => {
            document.getElementById('reMenuL1_4_opImgL1')?.click();
            fnSelectL2Menu('40000000');
        }"""
    )
    page.wait_for_timeout(2500)
    page.evaluate(
        """() => {
            document.getElementById('reMenuL2_2_opImgL2')?.click();
            const code = document.getElementById('reMenuL2_2_opCodeL2')?.textContent?.trim();
            if (code) fnFindLeftMenu(code);
        }"""
    )
    page.wait_for_timeout(2500)
    page.evaluate("""() => { document.getElementById('treeview1_label_3')?.click(); }""")
    page.wait_for_timeout(5000)


def fetch_business(page: Page, busi_name: str, dept_name: str) -> SuwingsBusiness:
    frame = _get_form_window(page)
    frame.evaluate(
        """(name) => {
            ipF_BIZ_NO.setValue(name);
            fn_preM0_F0();
        }""",
        busi_name,
    )
    page.wait_for_timeout(4000)

    rows = frame.evaluate(
        """(name) => {
            const list = gdM0_F0.getAllDataList ? gdM0_F0.getAllDataList() : [];
            return list.filter(r => (r.BIZ_NM || r.bizNm || '').includes(name));
        }""",
        busi_name,
    )
    if not rows:
        raise RuntimeError(f"SU-WINGs에서 사업을 찾지 못했습니다: {busi_name}")

    row_index = frame.evaluate(
        """(name) => {
            const list = gdM0_F0.getAllDataList();
            for (let i = 0; i < list.length; i++) {
                if ((list[i].BIZ_NM || '').includes(name)) {
                    gdM0_F0.setFocusedCell(i, 1);
                    if (typeof gdM0_F0_oncellclick === 'function') gdM0_F0_oncellclick(i, 1);
                    return i;
                }
            }
            return -1;
        }""",
        busi_name,
    )
    page.wait_for_timeout(3000)

    detail = frame.evaluate(
        """() => ({
            busi_code: document.getElementById('ipI_BIZ_NO')?.value || '',
            busi_name: document.getElementById('ipI_BIZ_NM')?.value || '',
            busi_class: document.getElementById('ipI_STAS_CTNT')?.value || '',
            busi_class_code: document.getElementById('ipI_STAS_NO')?.value || '',
        })"""
    )

    dept_rows = frame.evaluate(
        """() => {
            const list = gdM1_F0.getAllDataList ? gdM1_F0.getAllDataList() : [];
            return list.map(r => ({
                dept: r.ORGN_NM || r.orgnNm || r.DEPT_NM || '',
                role: r.ORGN_ROLE_NM || r.orgnRoleNm || '',
            }));
        }"""
    )
    matched_dept = dept_name
    for row in dept_rows:
        if dept_name in (row.get("dept") or ""):
            matched_dept = row["dept"]
            break

    cls = detail["busi_class"] or ""
    m = re.search(r"(\d-\d-\d)", cls)
    busi_class_short = m.group(1) if m else cls

    return SuwingsBusiness(
        busi_name=detail["busi_name"] or busi_name,
        busi_code=detail["busi_code"],
        busi_class=cls,
        busi_class_code=detail["busi_class_code"],
        dept_name=matched_dept or dept_name,
        acnt_yy=frame.evaluate("() => sbF_ACNT_YY.getValue ? sbF_ACNT_YY.getValue() : '2026'") or "2026",
    )


def fetch_business_with_login(
    username: str,
    password: str,
    busi_name: str,
    dept_name: str,
    *,
    headless: bool = True,
) -> SuwingsBusiness:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1600, "height": 1200})
        login(page, username, password)
        open_business_plan_register(page)
        result = fetch_business(page, busi_name, dept_name)
        browser.close()
        return result
