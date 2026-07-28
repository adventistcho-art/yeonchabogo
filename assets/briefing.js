(function () {

  const DATA = JSON.parse(document.getElementById('report-data').textContent || '{}');

  const departments = DATA.departments || [];
  const deptByName = Object.fromEntries(departments.map((d) => [d.name, d]));

  const PLAN2026_GROUPS = [
    {
      title: '1. 사무처',
      units: [
        { label: '건축안전관리팀', dept: '건축・안전관리팀' },
        { label: '교육미디어지원팀', dept: '교육미디어지원팀' },
        { label: '조경미화팀', dept: '조경미화팀' },
        { label: '전기통신팀', dept: '전기통신팀' },
        { label: '관재팀', dept: '관재팀' },
      ],
    },
    {
      title: '2. 총무인사팀',
      units: [{ label: '총무인사팀', dept: '총무인사팀' }],
    },
    {
      title: '3. 기획처',
      units: [{ label: '기획처', dept: '기획처' }],
    },
    {
      title: '4. IR센터',
      units: [{ label: 'IR센터', dept: 'IR센터' }],
    },
    {
      title: '5. 학생처',
      units: [
        { label: '학생복지팀', dept: '학생복지팀' },
        { label: '장애학생지원센터', dept: '장애학생지원센터' },
        { label: '학생상담센터', dept: '학생상담센터' },
      ],
    },
    {
      title: '6. 교목처',
      units: [
        { label: '교목처', dept: '교목처' },
        { label: '리더십센터', dept: '인성교육원', budgetDept: '리더십센터', projectMatch: '리더십|MVP' },
        { label: '콘서바토리', dept: '콘서바토리' },
      ],
    },
    {
      title: '7. 교무처',
      units: [
        { label: '교수지원', dept: '교수지원' },
        { label: '교원인사', dept: '교원인사' },
        { label: '학사지원팀', dept: '학사지원팀' },
      ],
    },
    {
      title: '8. 브랜드전략본부',
      units: [
        { label: '부속실', dept: '부속실', budgetDept: '부속팀' },
        { label: '커뮤니케이션팀', dept: '커뮤니케이션팀' },
        { label: '대외협력팀', dept: '대외국제처', budgetDept: '대외협력팀' },
      ],
    },
    {
      title: '9. 연구처',
      units: [{ label: '연구산학팀', dept: '연구산학팀' }],
    },
    {
      title: '10. AI융합교육원',
      units: [{ label: '소프트웨어중심대학사업단', dept: '소프트웨어중심대학사업단' }],
    },
    {
      title: '11. 학술정보원',
      units: [
        { label: '학술정보팀', dept: '학술정보팀' },
        { label: '정보전산팀', dept: '정보전산팀' },
      ],
    },
    {
      title: '12. 대학일자리본부',
      units: [
        { label: '취업진로지원센터', dept: '취업진로지원센터' },
        { label: '스타트업지원센터', dept: '창업교육센터' },
      ],
    },
    {
      title: '13. 국제처',
      units: [{ label: '국제교육원', dept: '국제교육원' }],
    },
    {
      title: '14. 대학원',
      units: [
        { label: '일반대학원(교학)', dept: '일반대학원(교학)' },
        { label: '신학대학원(교학)', dept: '신학대학원(교학)' },
        { label: '경영대학원(교학)', dept: '경영대학원(교학)' },
      ],
    },
    {
      title: '15. 재무처',
      units: [
        { label: '예산팀', dept: '예산팀' },
        { label: '재무팀', dept: '재무팀' },
        { label: '구매팀', dept: '구매팀' },
      ],
    },
  ];

  let selectedDept = null;
  let trendChart = null;
  let activeView = 'briefing2025';

  const fmtCompact = (v) => {
    if (v == null || v === '') return '-';
    const n = Number(v);
    if (Number.isNaN(n)) return '-';
    if (Math.abs(n) >= 100000000) return (n / 100000000).toFixed(1).replace(/\.0$/, '') + '억';
    if (Math.abs(n) >= 10000) return Math.round(n / 10000).toLocaleString('ko-KR') + '만';
    return n.toLocaleString('ko-KR');
  };

  const fmtMoney = (v) => {
    if (v == null || v === '') return '-';
    const n = Number(v);
    if (Number.isNaN(n)) return '-';
    return n.toLocaleString('ko-KR') + '원';
  };

  const fmtPct = (v) => {
    if (v == null || v === '') return '-';
    if (typeof v === 'number') return v.toFixed(1) + '%';
    return String(v);
  };

  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function escAttr(s) {
    return esc(s).replace(/'/g, '&#39;');
  }

  function projectMatchesUnit(project, unit) {
    if (!unit.projectMatch) return true;
    return new RegExp(unit.projectMatch).test(project.name || '');
  }

  const DEPT_ALIASES = {
    '총무인사팀': '총무과',
  };

  const PERF_BUDGET_ALIASES = {
    '부속실': '부속팀',
    '대외국제처': '대외협력팀',
    '총무인사팀': '총무과',
  };

  function resolveDeptName(name) {
    return DEPT_ALIASES[name] || name;
  }

  function budgetDeptForUnit(unit) {
    return resolveDeptName(unit.budgetDept || unit.dept);
  }

  function deptPerfBudget2026(deptName) {
    const dept = deptByName[resolveDeptName(deptName)];
    if (dept?.performance2026?.adjustedBudget != null) {
      return dept.performance2026.adjustedBudget;
    }
    const map = DATA.perfBudget2026 || {};
    if (map[deptName] != null) return map[deptName];
    const alias = PERF_BUDGET_ALIASES[deptName];
    if (alias != null && map[alias] != null) return map[alias];
    return null;
  }

  function plan2026ProjectsForUnit(unit) {
    const dept = deptByName[resolveDeptName(unit.dept)];
    if (!dept) return [];
    return (dept.projects || []).filter(
      (p) => p.plan2026HtmlPath && projectMatchesUnit(p, unit)
    );
  }

  function totalBudgetForUnit(unit) {
    const fromPerf = deptPerfBudget2026(budgetDeptForUnit(unit));
    if (fromPerf != null && fromPerf > 0) return fromPerf;
    return plan2026ProjectsForUnit(unit).reduce((sum, p) => sum + (p.budget2026 || 0), 0);
  }

  function fundedCountForUnit(unit) {
    return plan2026ProjectsForUnit(unit).filter((p) => (p.budget2026 || 0) > 0).length;
  }

  function fmtBudget2026(v) {
    if (v == null || v === 0) return '—';
    return fmtCompact(v);
  }

  function renderDeptList(query) {
    const q = query.trim().toLowerCase();
    const list = document.getElementById('deptList');
    const filtered = departments.filter((d) => !q || d.name.toLowerCase().includes(q));
    list.innerHTML = filtered.map((d) =>
      '<li><button type="button" data-dept="' + escAttr(d.name) + '"' +
      (selectedDept && selectedDept.name === d.name ? ' class="active"' : '') + '>' +
      esc(d.name) + '</button></li>'
    ).join('') || '<li>검색 결과 없음</li>';

    list.querySelectorAll('button[data-dept]').forEach((btn) => {
      btn.addEventListener('click', () => selectDept(btn.dataset.dept));
    });
  }

  function selectDept(name) {
    const dept = departments.find((d) => d.name === name);
    if (!dept) return;
    selectedDept = dept;
    location.hash = 'dept=' + encodeURIComponent(name);
    try { localStorage.setItem('briefingDept', name); } catch (_) {}

    document.getElementById('emptyState').classList.add('hidden');
    document.getElementById('deptPanel').classList.remove('hidden');
    renderDeptList(document.getElementById('deptSearch').value);
    renderDeptPanel(dept);
  }

  function changeClass(rate) {
    if (rate == null) return 'flat';
    if (rate > 0) return 'up';
    if (rate < 0) return 'down';
    return 'flat';
  }

  function formatChange(rate) {
    if (rate == null) return '—';
    const sign = rate > 0 ? '+' : '';
    return sign + rate.toFixed(1) + '%';
  }

  function typePill(type) {
    const perf = type === '성과관리사업';
    return '<span class="type-pill' + (perf ? ' perf' : '') + '">' + esc(type || '-') + '</span>';
  }

  function renderHero(dept) {
    const perf = dept.performance || {};
    const sm = dept.summary || {};
    const budget = perf.adjustedBudget;
    const change = dept.budgetChangeRate;
    const changeCls = changeClass(change);

    document.getElementById('heroMetrics').innerHTML =
      '<div class="metric metric-change">' +
        '<div class="metric-label">전년 대비 예산</div>' +
        '<div class="metric-value ' + changeCls + '">' + formatChange(change) + '</div>' +
      '</div>' +
      '<div class="metric metric-count">' +
        '<div class="metric-label">2025 사업</div>' +
        '<div class="metric-value sm">' + (sm.projectCount || 0) + '<span class="metric-unit">건</span></div>' +
      '</div>' +
      '<div class="metric metric-budget">' +
        '<div class="metric-label">2025 조정예산</div>' +
        '<div class="metric-value">' + fmtCompact(budget) + '</div>' +
      '</div>';
  }

  function destroyChart() {
    if (trendChart) {
      trendChart.destroy();
      trendChart = null;
    }
  }

  function renderTrendChart(dept) {
    destroyChart();
    const hist = dept.budgetHistory || {};
    const years = Object.keys(hist).sort();
    const note = document.getElementById('trendNote');
    if (!years.length) {
      years.push(String(DATA.year || 2025));
      hist[years[0]] = dept.performance?.adjustedBudget;
    }
    note.textContent = years.length >= 2 ? '조정예산 · 억 원' : '';

    const values = years.map((y) => hist[y] || 0);
    const currentYear = String(DATA.year || 2025);
    trendChart = new Chart(document.getElementById('trendChart'), {
      type: 'bar',
      data: {
        labels: years.map((y) => y),
        datasets: [{
          data: values,
          backgroundColor: years.map((y) => (y === currentYear ? '#2563eb' : '#cbd5e1')),
          borderRadius: 8,
          barThickness: 56,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => fmtCompact(ctx.raw),
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 15, weight: '700' }, color: '#334155' },
          },
          y: {
            grid: { color: '#f1f5f9' },
            ticks: {
              callback: (v) => fmtCompact(v),
              font: { size: 12 },
              color: '#94a3b8',
            },
          },
        },
      },
    });
  }

  function bindDocButtons(container, dept) {
    container.querySelectorAll('.btn-open-doc').forEach((btn) => {
      btn.addEventListener('click', () => openDocModal(dept.name + ' · ' + btn.dataset.title, btn.dataset.href));
    });
  }

  function annualReport2025Href(dept) {
    return dept.annualReport2025PdfHref
      || dept.submission?.annualReport2025PdfHref
      || dept.annualReport2025IrPdfHref
      || '';
  }

  function renderDocs(dept) {
    const href24 = dept.annualReport2024PdfHref || '';
    const href25 = annualReport2025Href(dept);
    const row = document.getElementById('docBar');
    row.innerHTML = docChip('24 연차', href24) + docChip('25 연차', href25);
    bindDocButtons(row, dept);
  }

  function docChip(label, href) {
    if (!href) {
      return '<button type="button" class="doc-chip" disabled>' + esc(label) + '</button>';
    }
    return '<button type="button" class="doc-chip btn-open-doc" data-href="' + escAttr(href) + '" data-title="' + escAttr(label) + '">' + esc(label) + '</button>';
  }

  function miniDoc(label, href) {
    if (!href) {
      return '<button type="button" class="mini-btn" disabled title="' + escAttr(label) + '">' + esc(label) + '</button>';
    }
    return '<button type="button" class="mini-btn btn-open-doc" data-href="' + escAttr(href) + '" data-title="' + escAttr(label) + '" title="' + escAttr(label) + '">' + esc(label) + '</button>';
  }

  function renderProjects(dept) {
    const projects = (dept.projects || []).slice().sort((a, b) => (b.budget || 0) - (a.budget || 0));
    document.getElementById('projectCount').textContent = projects.length + '건';

    document.getElementById('projectTableBody').innerHTML = projects.map((p) =>
      '<tr>' +
        '<td class="col-name">' +
          '<div class="project-name">' + esc(p.name) + '</div>' +
          (p.mgmtType ? '<div class="project-type">' + typePill(p.mgmtType) + '</div>' : '') +
        '</td>' +
        '<td class="col-money">' + fmtCompact(p.budget) + '</td>' +
        '<td class="col-pct">' + fmtPct(p.budgetExecRate) + '</td>' +
        '<td class="col-docs">' +
          miniDoc('계획', p.planHtmlPath) +
          miniDoc('결과', p.resultHtmlPath) +
          miniDoc('26', p.plan2026HtmlPath) +
        '</td>' +
      '</tr>'
    ).join('') || '<tr><td colspan="4" class="empty-row">등록된 사업 없음</td></tr>';

    bindDocButtons(document.getElementById('projectTableBody'), dept);
  }

  function renderDeptPanel(dept) {
    document.getElementById('deptTitle').textContent = dept.name;
    renderDocs(dept);
    renderHero(dept);
    renderTrendChart(dept);
    renderProjects(dept);
  }

  function renderPlan2026Groups() {
    const root = document.getElementById('plan2026Groups');
    root.innerHTML = PLAN2026_GROUPS.map((group) => {
      const cards = group.units.map((unit) => {
        const projects = plan2026ProjectsForUnit(unit);
        const total = totalBudgetForUnit(unit);
        const funded = fundedCountForUnit(unit);
        const missing = !deptByName[resolveDeptName(unit.dept)];
        const hasBudget = total > 0;
        const disabled = missing || (!projects.length && !hasBudget);
        const budgetLabel = total > 0 ? fmtCompact(total) : '—';
        let meta = '';
        if (missing) {
          meta = '연동된 부서 데이터가 없습니다.';
        } else if (!projects.length) {
          meta = '2026 사업계획서 없음';
        } else {
          meta = projects.length + '개 사업계획서';
          if (funded) meta += ' · 예산 ' + funded + '건';
        }
        return (
          '<article class="plan2026-card' + (disabled ? ' is-empty' : '') + '">' +
            '<div class="plan2026-card-head">' +
              '<h4>' + esc(unit.label) + '</h4>' +
              (missing ? '<span class="plan2026-badge warn">데이터 없음</span>' : '') +
            '</div>' +
            '<div class="plan2026-card-budget-label">2026 조정예산</div>' +
            '<div class="plan2026-card-budget' + (total > 0 ? '' : ' is-muted') + '">' + budgetLabel + '</div>' +
            '<div class="plan2026-card-meta">' + meta + '</div>' +
            '<button type="button" class="plan2026-open-btn"' +
              ' data-unit-label="' + escAttr(unit.label) + '"' +
              ' data-unit-dept="' + escAttr(unit.dept) + '"' +
              (unit.budgetDept ? ' data-unit-budget-dept="' + escAttr(unit.budgetDept) + '"' : '') +
              (unit.projectMatch ? ' data-unit-match="' + escAttr(unit.projectMatch) + '"' : '') +
              (disabled ? ' disabled' : '') +
            '>사업계획서 보기</button>' +
          '</article>'
        );
      }).join('');

      return (
        '<section class="plan2026-group">' +
          '<h3 class="plan2026-group-title">' + esc(group.title) + '</h3>' +
          '<div class="plan2026-card-grid">' + cards + '</div>' +
        '</section>'
      );
    }).join('');

    root.querySelectorAll('.plan2026-open-btn:not([disabled])').forEach((btn) => {
      btn.addEventListener('click', () => {
        openPlan2026ListModal({
          label: btn.dataset.unitLabel,
          dept: btn.dataset.unitDept,
          budgetDept: btn.dataset.unitBudgetDept || '',
          projectMatch: btn.dataset.unitMatch || '',
        });
      });
    });
  }

  function openPlan2026ListModal(unit) {
    const projects = plan2026ProjectsForUnit(unit).sort((a, b) => (b.budget2026 || 0) - (a.budget2026 || 0));
    const total = totalBudgetForUnit(unit);
    const funded = fundedCountForUnit(unit);

    document.getElementById('plan2026ListTitle').textContent = unit.label + ' · 2026년 사업계획서';
    document.getElementById('plan2026ListSummary').textContent =
      projects.length + '건' +
      (total > 0 ? ' · 조정예산 ' + fmtMoney(total) : '') +
      (funded ? ' · 입력 ' + funded + '건' : '');

    document.getElementById('plan2026ListBody').innerHTML = projects.map((p) =>
      '<tr>' +
        '<td class="col-name"><div class="project-name">' + esc(p.name) + '</div></td>' +
        '<td class="col-money">' + fmtBudget2026(p.budget2026) + '</td>' +
        '<td class="col-docs">' +
          '<button type="button" class="mini-btn btn-open-plan2026" data-href="' + escAttr(p.plan2026HtmlPath) + '" data-title="' + escAttr(p.name) + '">보기</button>' +
        '</td>' +
      '</tr>'
    ).join('');

    document.getElementById('plan2026ListBody').querySelectorAll('.btn-open-plan2026').forEach((btn) => {
      btn.addEventListener('click', () => {
        openDocModal(unit.label + ' · ' + btn.dataset.title, btn.dataset.href);
      });
    });

    document.getElementById('plan2026ListBackdrop').classList.add('open');
  }

  function closePlan2026ListModal() {
    document.getElementById('plan2026ListBackdrop').classList.remove('open');
  }

  function openDocModal(title, href) {
    document.getElementById('docModalTitle').textContent = title;
    document.getElementById('docModalFrame').src = href || 'about:blank';
    document.getElementById('docModalBackdrop').classList.add('open');
  }

  function closeDocModal() {
    document.getElementById('docModalBackdrop').classList.remove('open');
    document.getElementById('docModalFrame').src = 'about:blank';
  }

  function closeModals() {
    closeDocModal();
    closePlan2026ListModal();
  }

  function setView(view) {
    activeView = view;
    const is2025 = view === 'briefing2025';
    document.getElementById('briefing2025View').classList.toggle('hidden', !is2025);
    document.getElementById('plan2026View').classList.toggle('hidden', is2025);
    document.getElementById('sidebarBriefing').classList.toggle('hidden', !is2025);
    document.querySelectorAll('.view-tab').forEach((tab) => {
      tab.classList.toggle('active', tab.dataset.view === view);
    });

    if (view === 'plan2026') {
      location.hash = 'view=plan2026';
      renderPlan2026Groups();
    } else if (selectedDept) {
      location.hash = 'dept=' + encodeURIComponent(selectedDept.name);
    } else {
      location.hash = '';
    }
  }

  function initFromHash() {
    const hash = location.hash.replace(/^#/, '');
    const params = new URLSearchParams(hash);

    if (params.get('view') === 'plan2026') {
      setView('plan2026');
      return;
    }

    const fromHash = params.get('dept');
    if (fromHash && departments.some((d) => d.name === fromHash)) {
      setView('briefing2025');
      selectDept(fromHash);
      return;
    }

    try {
      const saved = localStorage.getItem('briefingDept');
      if (saved && departments.some((d) => d.name === saved)) {
        setView('briefing2025');
        selectDept(saved);
        return;
      }
    } catch (_) {}

    setView('briefing2025');
    if (departments.length) selectDept(departments[0].name);
  }

  document.getElementById('deptSearch').addEventListener('input', (e) => {
    renderDeptList(e.target.value);
  });

  document.querySelectorAll('.view-tab').forEach((tab) => {
    tab.addEventListener('click', () => setView(tab.dataset.view));
  });

  document.getElementById('docModalClose').addEventListener('click', closeDocModal);
  document.getElementById('docModalBackdrop').addEventListener('click', (e) => {
    if (e.target.id === 'docModalBackdrop') closeDocModal();
  });

  document.getElementById('plan2026ListClose').addEventListener('click', closePlan2026ListModal);
  document.getElementById('plan2026ListBackdrop').addEventListener('click', (e) => {
    if (e.target.id === 'plan2026ListBackdrop') closePlan2026ListModal();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (document.getElementById('docModalBackdrop').classList.contains('open')) {
        closeDocModal();
      } else if (document.getElementById('plan2026ListBackdrop').classList.contains('open')) {
        closePlan2026ListModal();
      }
    }
  });

  document.getElementById('sidebarMeta').textContent =
    (DATA.builtAt || '-') + ' · ' + departments.length + '개 부서';

  renderDeptList('');
  renderPlan2026Groups();
  initFromHash();
})();
