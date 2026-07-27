# -*- coding: utf-8 -*-
import json
import shutil
import sys
from pathlib import Path

TARGET_DEPTS = {
    "건축・안전관리팀", "교육미디어지원팀", "조경미화팀", "전기통신팀", "관재팀",
    "총무과", "기획처", "IR센터", "학생복지팀", "장애학생지원센터",
    "학생상담센터", "교목처", "인성교육원", "콘서바토리",
}


def copy_target_plan2026(
    *,
    root: Path | None = None,
    config_path: Path | None = None,
) -> tuple[int, int]:
    root = root or Path(__file__).resolve().parent.parent
    config_path = config_path or Path(__file__).resolve().parent / "config.json"
    html_out = root / "html"

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    ir_root = Path(cfg["paths"]["irPdfRoot"])
    report = json.loads(Path(cfg["paths"]["reportJson"]).read_text(encoding="utf-8"))

    count = 0
    size = 0
    for dept in report.get("departments", []):
        if dept["name"] not in TARGET_DEPTS:
            continue
        for proj in dept.get("projects", []):
            rel = proj.get("plan2026HtmlPath")
            if not rel or rel.startswith("file:"):
                continue
            src = ir_root / rel.replace("/", "\\")
            if not src.is_file():
                continue
            rel_under_html = rel.removeprefix("html/").replace("/", "\\")
            dest = html_out / rel_under_html
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists() or dest.stat().st_size != src.stat().st_size:
                shutil.copy2(src, dest)
            count += 1
            size += dest.stat().st_size
    return count, size


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    count, size = copy_target_plan2026()
    html_out = Path(__file__).resolve().parent.parent / "html"
    print(f"Copied {count} plan2026 files, {size/1024/1024:.1f} MB -> {html_out}")


if __name__ == "__main__":
    main()
