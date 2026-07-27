# -*- coding: utf-8 -*-
"""Create IR busiTreeMgr entries from SU-WINGs business metadata."""
from __future__ import annotations

import re
from dataclasses import dataclass

import requests
from playwright.sync_api import sync_playwright

from suwings_client import SuwingsBusiness


@dataclass
class IrCreateResult:
    ir_name: str
    lvl_cd: str
    prog_cd: str
    dept_cd: str
    dept_name: str
    parent_lvl_cd: str
    year: str


def login_ir(session: requests.Session, base_url: str, username: str, password: str) -> None:
    base_url = base_url.rstrip("/") + "/"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto(base_url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(1500)
        if page.locator('input[name="id"]').count():
            page.fill('input[name="id"]', username)
            page.fill('input[name="pw"]', password)
            page.click("input.signin")
            for _ in range(30):
                page.wait_for_timeout(1500)
                if "중장기발전계획" in page.inner_text("body"):
                    break
                if page.locator('input[name="id"]').count() == 0:
                    break
        for cookie in context.cookies():
            session.cookies.set(cookie["name"], cookie["value"], domain=cookie.get("domain"))
        browser.close()


def _list_tree(
    session: requests.Session,
    base_url: str,
    year: str,
    busi_gbn: str = "113",
    keyword: str = "",
) -> list[dict]:
    r = session.get(
        base_url.rstrip("/") + "/kuts/busiTreeMgr/list",
        params={"sYear": year, "sBusiGbn": busi_gbn, "sText": keyword},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def find_parent_lvl_cd(tree: list[dict], class_prefix: str) -> dict:
    prefix = class_prefix.strip()
    if not prefix[0].isdigit() and prefix[:1].isdigit() is False:
        m = re.search(r"(\d-\d-\d)", prefix)
        if m:
            prefix = m.group(1)
    for item in tree:
        name = item.get("LVL_NM") or ""
        if name.startswith(prefix + ".") or name.startswith(prefix + " "):
            return item
    raise RuntimeError(f"IR 분류 노드를 찾지 못했습니다: {class_prefix}")


def resolve_dept_cd(
    session: requests.Session,
    base_url: str,
    year: str,
    dept_name: str,
) -> tuple[str, str]:
    tree = _list_tree(session, base_url, year, keyword=dept_name)
    for item in tree:
        name = item.get("LVL_NM") or ""
        if dept_name in name and item.get("LVL") == "4":
            r = session.get(
                base_url.rstrip("/") + "/kuts/busiTreeMgr/modal2",
                params={
                    "yyyy": year,
                    "busiGbn": "113",
                    "lvl": "4",
                    "lvlCd": item["LVL_CD"],
                },
                timeout=60,
            )
            r.raise_for_status()
            data = r.json().get("list") or {}
            if data.get("deptCd"):
                return data["deptCd"], data.get("deptNm") or dept_name
    raise RuntimeError(f"IR 주관부서 코드를 찾지 못했습니다: {dept_name}")


def create_business(
    session: requests.Session,
    base_url: str,
    sw: SuwingsBusiness,
    dept_name: str,
    *,
    year: str | None = None,
    busi_gbn: str = "113",
    dry_run: bool = False,
) -> IrCreateResult:
    year = year or sw.acnt_yy or "2026"
    ir_name = f"{sw.busi_name}({dept_name})"
    class_prefix = sw.busi_class.split(".")[0].strip()
    m = re.search(r"(\d-\d-\d)", sw.busi_class)
    if m:
        class_prefix = m.group(1)

    tree = _list_tree(session, base_url, year, busi_gbn, keyword=class_prefix)
    parent = find_parent_lvl_cd(tree, class_prefix)
    parent_lvl_cd = parent["LVL_CD"]

    existing = _list_tree(session, base_url, year, busi_gbn, keyword=ir_name)
    for item in existing:
        if item.get("LVL_NM") == ir_name and item.get("LVL") == "4":
            raise RuntimeError(f"IR에 이미 존재하는 사업입니다: {ir_name} (LVL_CD={item['LVL_CD']})")

    dept_cd, dept_nm = resolve_dept_cd(session, base_url, year, dept_name)

    if dry_run:
        return IrCreateResult(
            ir_name=ir_name,
            lvl_cd="(dry-run)",
            prog_cd=sw.busi_code,
            dept_cd=dept_cd,
            dept_name=dept_nm,
            parent_lvl_cd=parent_lvl_cd,
            year=year,
        )

    save = session.post(
        base_url.rstrip("/") + "/kuts/busiTreeMgr/save",
        data={
            "requestType": "save",
            "yyyy": year,
            "busiGbn": busi_gbn,
            "lvl": "4",
            "upLvlCd": parent_lvl_cd,
            "lvlNm": ir_name,
            "sortOrder": "999",
        },
        timeout=60,
    )
    save.raise_for_status()
    if save.json().get("result") != "ok":
        raise RuntimeError(f"busiTreeMgr/save 실패: {save.text[:300]}")

    created = find_created_node(session, base_url, year, busi_gbn, ir_name)
    modal = session.get(
        base_url.rstrip("/") + "/kuts/busiTreeMgr/modal2",
        params={
            "yyyy": year,
            "busiGbn": busi_gbn,
            "lvl": "4",
            "lvlCd": created["LVL_CD"],
        },
        timeout=60,
    )
    modal.raise_for_status()
    info = modal.json().get("list") or {}

    payload = {
        "requestType": "update",
        "yyyy": year,
        "busiGbn": busi_gbn,
        "lvl": "4",
        "progCd": sw.busi_code,
        "lvlCd": created["LVL_CD"],
        "lvlNm": ir_name,
        "lvlCd1": info.get("lvlCd1", ""),
        "lvlNm1": info.get("lvlNm1", ""),
        "lvlCd2": info.get("lvlCd2", ""),
        "lvlNm2": info.get("lvlNm2", ""),
        "lvlCd3": info.get("lvlCd3", ""),
        "lvlNm3": info.get("lvlNm3", ""),
        "deptCd": dept_cd,
        "deptNm": dept_nm,
        "jaewon": "100",
        "busiSect": "101",
        "busiMgmt": "101",
        "sortOrder4": "999",
    }
    save2 = session.post(base_url.rstrip("/") + "/kuts/busiTreeMgr/save2", data=payload, timeout=60)
    save2.raise_for_status()
    if save2.json().get("result") != "ok":
        raise RuntimeError(f"busiTreeMgr/save2 실패: {save2.text[:300]}")

    return IrCreateResult(
        ir_name=ir_name,
        lvl_cd=created["LVL_CD"],
        prog_cd=sw.busi_code,
        dept_cd=dept_cd,
        dept_name=dept_nm,
        parent_lvl_cd=parent_lvl_cd,
        year=year,
    )


def find_created_node(
    session: requests.Session,
    base_url: str,
    year: str,
    busi_gbn: str,
    ir_name: str,
) -> dict:
    tree = _list_tree(session, base_url, year, busi_gbn, keyword=ir_name)
    for item in tree:
        if item.get("LVL_NM") == ir_name and str(item.get("LVL")) == "4":
            return item
    raise RuntimeError(f"생성된 IR 사업 노드를 찾지 못했습니다: {ir_name}")
