# 2025 연차보고 통합 대시보드 (yeonchabogo)

IR 성과 대시보드 + 그룹웨어 공문 제출 현황을 **하나의 `index.html`** 에서 봅니다.

## 폴더

```
yeonchabogo/
├── index.html          ← 통합 대시보드 (관리용, 빌드 후 데이터 embed)
├── briefing.html       ← 부서별 브리핑 (총장·팀장 미팅용)
├── assets/
│   ├── dashboard.css
│   ├── dashboard.js
│   ├── briefing.css
│   └── briefing.js
└── scripts/
    ├── config.json     ← F: 드라이브 데이터 경로
    ├── build_dashboard.py
    ├── submission_data.py
    ├── submission_utils.py
    └── sync-approved-from-gw.py
```

데이터·PDF는 F: 드라이브에 그대로 둡니다 (`scripts/config.json` 참고).

## 준비

```powershell
cd "C:\Users\SYU\Documents\커서도전\yeonchabogo\scripts"
pip install -r requirements.txt
```

## 1. 그룹웨어 공문 동기화 (선택)

브라우저에서 gw.syu.ac.kr 로그인 후 개발자도구 → Application → Cookies → `PHPSESSID` 복사.

```powershell
python sync-approved-from-gw.py --auto-login
# 또는
python sync-approved-from-gw.py <PHPSESSID> [sekey]
```

다음 위치에서 연차보고서 공문을 수집합니다.

- **결재할문서함** (내부수신)
- **결재한문서함** (내부수신, 검색어 병합)
- **통합문서함** (boxid 3399, `config.json` → `gw.integratedDocboxId`)

→ `F:\...\부서공문제출\approved_submissions.json` 갱신 및 PDF 다운로드  
→ GW에 확인된 부서는 **로컬 PDF 없어도 제출**로 표시 (PDF는 이후 sync 시 받음)

## 2. 대시보드 빌드

```powershell
cd "C:\Users\SYU\Documents\커서도전\yeonchabogo\scripts"
python build_dashboard.py
```

→ `index.html`, `briefing.html`에 IR + 제출 데이터 embed

## 3. 확인

- **관리용**: `index.html` — 공문 제출·비고·전체 표
- **브리핑용**: `briefing.html` — 부서 선택 → KPI·그래프·문서

## 4. (관리용) 사업 HTML·PDF

- IR: 조정예산, 종합점수, 세부사업, **사업계획 및 결과**(결과 HTML 모달)
- 공문: 제출/미제출, 제출 PDF, 결재완료 공문 목록, 미제출 담당자·이메일, 비고(이상) 자동 분석
- 필터: 전체 / 제출 / 미제출 / 비고(이상) + 부서명 검색

## IR 데이터 갱신 (하루 1회 권장)

IR JSON + 사업결과 HTML은 F: 본체에서 수집합니다:

```powershell
cd "F:\기획평가\2026\2025연차보고서\연차보고 시스템으로 정리\scripts"
python scrape_ir.py
```

- 기본: IR API JSON + **사업결과 HTML** (`html/{부서}/{사업명}_result.html`)
- PDF가 필요할 때만: `python scrape_ir.py --pdf`
- HTML만 다시: `python scrape_ir.py --html-only`
- **2026 사업계획 HTML만** (기존 plan/result 유지): `python scrape_ir.py --plan2026-only`
- **2024 연차보고 PDF만**: `python scrape_ir.py --annual-report-2024-only`
- 테스트: `python scrape_ir.py --plan2026-only --limit-plan2026 5`

이후 yeonchabogo에서 `python build_dashboard.py` 를 다시 실행하세요.

## 부서별 연차평가 합본 보고서

`index.html`에 embed된 데이터를 기준으로 참고 양식과 유사한 A4 합본 PDF를 생성합니다.

```powershell
cd "C:\Users\SYU\Documents\커서도전\yeonchabogo"
python scripts\build_annual_evaluation_report.py
python scripts\validate_annual_evaluation_report.py
```

결과물은 `reports/`에 생성됩니다. GitHub Pages 합본:

- https://adventistcho-art.github.io/yeonchabogo/reports/
- https://adventistcho-art.github.io/yeonchabogo/reports/2025학년도_연차평가_보고서.pdf

`master`에 푸시하면 Pages가 갱신됩니다.

- `2025학년도_부서연차평가_보고서_합본.html`
- `2025학년도_부서연차평가_보고서_합본.pdf`
- `2025학년도_부서연차평가_보고서_합본_데이터검증.html/json`
- `2025학년도_부서연차평가_보고서_합본_출력검증.json`

전년도 실적·종합등급은 `2024부서별데이터.xlsx`를 불러온 뒤 최종 발간 합본 PDF와
대조한 확정값을 우선 사용합니다. 두 자료가 다르면 최종 PDF의 `해당없음`과 종합등급을
적용하며, 전년도 명단에 없는 신규·변경 부서만 `자료없음`으로 표시합니다.
