# -*- coding: utf-8 -*-
"""Obtain GW PHPSESSID/sekey via Playwright SSO login (IR config credentials)."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

IR_CONFIG = Path(r"F:\기획평가\2026\2025연차보고서\연차보고 시스템으로 정리\scripts\config.json")


def login_gw_credentials() -> tuple[str, str]:
    cfg = json.loads(IR_CONFIG.read_text(encoding="utf-8"))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto("https://gw.syu.ac.kr/login.html", wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(1500)

        if page.locator('input[name="id"]').count():
            page.fill('input[name="id"]', cfg["username"])
            page.fill('input[name="pw"]', cfg["password"])
            if page.locator("button.loginBtnM").count():
                page.click("button.loginBtnM")
            else:
                page.keyboard.press("Enter")

        logged_in = False
        for _ in range(20):
            page.wait_for_timeout(1500)
            if "index.html" in page.url or (
                "gw.syu.ac.kr" in page.url and "login" not in page.url
            ):
                logged_in = True
                break

        cookies = {c["name"]: c["value"] for c in ctx.cookies()}
        browser.close()

    phpsessid = cookies.get("PHPSESSID", "")
    sekey = cookies.get("sekey", "")
    if not phpsessid or not logged_in:
        raise RuntimeError("GW login failed")
    return phpsessid, sekey
