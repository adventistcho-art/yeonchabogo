(function () {
  const DATA = JSON.parse(document.getElementById('report-data').textContent || '{}');
  const departments = DATA.departments || [];
  const submissionMeta = DATA.submissionMeta || {};
  const approvedDocuments = DATA.approvedDocuments || [];
  let submissionFilter = 'all';

  const fmtPct = (v) => (v == null || v === '' ? '-' : (typeof v === 'number' ? v.toFixed(2) + '%' : String(v)));
  const fmtMoney = (v) => (v == null ? '-' : Number(v).toLocaleString('ko-KR'));
  const fmtRate = (v) => (v == null ? '-' : v.toFixed(2) + '%');

  function gradeSortKey(score) {
    const order = ['A+', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'F'];
    const idx = order.indexOf(String(score).trim());
    return idx === -1 ? 999 : idx;
  }

  function filteredDepts(query) {
    const q = query.trim().toLowerCase();
    return departments.filter((d) => {
      if (submissionFilter === 'submitted' && d.submission?.status !== 'submitted') return false;
      if (submissionFilter === 'not_submitted' && d.submission?.status !== 'not_submitted') return false;
      if (submissionFilter === 'anomaly' && !d.submission?.hasAnomaly) return false;
      if (!q) return true;
      return d.name.toLowerCase().includes(q);
    });
  }

  function feedbackMap(dept) {
    const map = {};
    (dept.feedback || []).forEach((f) => {
      map[f.projectName] = f;
    });
    return map;
  }

  function renderSummary(depts) {
    const submitted = submissionMeta.submittedCount ?? departments.filter((d) => d.submission?.status === 'submitted').length;
    const pending = submissionMeta.notSubmittedCount ?? (departments.length - submitted);
    const anomaly = submissionMeta.anomalyCount ?? departments.filter((d) => d.submission?.hasAnomaly).length;
    document.getElementById('summary').innerHTML =
      '<div class="card"><div class="num">' + departments.length + '</div><div class="label">대상 부서</div></div>' +
      '<div class="card done"><div class="num">' + submitted + '</div><div class="label">공문 제출</div></div>' +
      '<div class="card pending"><div class="num">' + pending + '</div><div class="label">미제출</div></div>' +
      '<div class="card approved"><div class="num">' + (submissionMeta.approvedCount || approvedDocuments.length) + '</div><div class="label">결재완료</div></div>' +
      '<div class="card anomaly"><div class="num">' + anomaly + '</div><div class="label">비고(이상)</div></div>';

    document.getElementById('meta').innerHTML =
      'IR: 중장기발전계획 &gt; 계획관리 &gt; 부서별 연차보고서 &gt; 연도 2025<br>' +
      'IR 생성: ' + (DATA.generatedAt || '-') + '<br>' +
      '사업 HTML 동기화: ' + (DATA.htmlSyncedAt || '-') + '<br>' +
      '2026 계획 HTML: ' + (DATA.plan2026SyncedAt || '-') + '<br>' +
      '2024 연차보고 PDF: ' + (DATA.annualReport2024SyncedAt || '-') + '<br>' +
      '공문 동기화: ' + (submissionMeta.updated || '-') +
      (submissionMeta.source ? ' (' + esc(submissionMeta.source) + ')' : '') + '<br>' +
      '빌드: ' + (DATA.builtAt || '-');
  }

  function submissionCell(dept) {
    const sub = dept.submission || {};
    const status = sub.status === 'submitted' ? 'submitted' : 'not_submitted';
    const label = status === 'submitted' ? '제출' : '미제출';
    const cls = status === 'submitted' ? 'status-submitted' : 'status-not-submitted';
    let filesHtml = '';
    if (sub.files && sub.files.length) {
      filesHtml = '<div class="submission-files">' +
        sub.files.map((f) => f.href
          ? '<a href="' + escAttr(f.href) + '" target="_blank" rel="noopener">' + esc(f.name) + '</a>'
          : esc(f.name)).join('<br>') +
        '</div>';
    }
    return '<td class="center-cell"><span class="status ' + cls + '">' + label + '</span>' + filesHtml + '</td>';
  }

  function remarksCell(dept) {
    const remarks = dept.submission?.remarks || [];
    if (!remarks.length) {
      return '<td class="remarks-empty">-</td>';
    }
    return '<td><ul class="remarks">' +
      remarks.map((r) => '<li>' + esc(r) + '</li>').join('') +
      '</ul></td>';
  }

  function contactCell(dept) {
    const c = dept.submission?.contact || {};
    const name = (c.name || '').trim();
    const email = (c.email || '').trim();
    if (!name && !email) {
      return '<td class="contact-cell">-</td>';
    }
    if (!email) {
      return '<td class="contact-cell"><span class="contact-name">' + esc(name || '-') + '</span></td>';
    }
    return '<td class="contact-cell">' +
      '<div class="contact-row">' +
      '<span class="contact-name">' + esc(name || '-') + '</span>' +
      '<button type="button" class="btn-email-mini" data-email="' + escAttr(email) + '" title="이메일 보기">✉</button>' +
      '</div>' +
      '<div class="contact-email hidden"></div>' +
      '</td>';
  }

  function annualReportCell(dept) {
    const href24 = dept.annualReport2024PdfHref || '';
    const href25 = dept.submission?.annualReport2025PdfHref || '';
    const btn24 = href24
      ? '<button type="button" class="btn btn-sm btn-annual-doc" data-dept="' + escAttr(dept.name) + '" data-href="' + escAttr(href24) + '" data-year="24">연차보고서24</button>'
      : '<button type="button" class="btn btn-sm" disabled title="2024 연차보고 PDF 없음">연차보고서24</button>';
    const btn25 = href25
      ? '<button type="button" class="btn btn-sm btn-annual-doc" data-dept="' + escAttr(dept.name) + '" data-href="' + escAttr(href25) + '" data-year="25">연차보고서25</button>'
      : '<button type="button" class="btn btn-sm" disabled title="2025 공문 PDF 없음">연차보고서25</button>';
    return '<td class="center-cell plan-result-cell"><div class="btn-row">' + btn24 + btn25 + '</div></td>';
  }

  function renderMain(depts) {
    const sorted = depts.slice().sort((a, b) => gradeSortKey(a.evaluation.totalScore) - gradeSortKey(b.evaluation.totalScore));
    const tbody = document.getElementById('mainBody');

    tbody.innerHTML = sorted.map((d) => {
      const bt = d.summary.byType || {};
      const plan = d.evaluation.performancePlan2026 || '-';
      const planMeta = d.evaluation.performancePlan2026Meta || {};
      const planDisabled = planMeta.isSubstantive ? '' : 'disabled';
      const typeStr = (bt['성과관리사업'] || 0) + ' / ' + (bt['항례적사업'] || 0) + ' / ' + (bt['지정안됨'] || 0);

      return '<tr>' +
        '<td class="dept-name">' + esc(d.name) + '</td>' +
        submissionCell(d) +
        '<td class="num-cell">' + fmtMoney(d.performance.adjustedBudget) + '</td>' +
        '<td class="num-cell"><span class="badge">' + esc(d.evaluation.totalScore) + '</span></td>' +
        '<td class="num-cell">' + esc(String(d.evaluation.budgetExecRate)) + '</td>' +
        '<td class="num-cell">' + esc(String(d.evaluation.projectExecRate)) + '</td>' +
        annualReportCell(d) +
        '<td class="center-cell"><button class="btn btn-plan" data-dept="' + escAttr(d.name) + '" ' + planDisabled + '>보기</button></td>' +
        '<td class="center-cell type-counts">' + typeStr + '</td>' +
        '<td class="center-cell"><button class="btn btn-detail" data-dept="' + escAttr(d.name) + '">보기 (' + d.summary.projectCount + ')</button></td>' +
        remarksCell(d) +
        contactCell(d) +
      '</tr>';
    }).join('') || '<tr><td colspan="12" class="empty">데이터 없음</td></tr>';

    tbody.querySelectorAll('.btn-annual-doc').forEach((btn) => {
      btn.addEventListener('click', () => {
        const yearLabel = btn.dataset.year === '24' ? '2024' : '2025';
        openHtmlModal((btn.dataset.dept || '') + ' - ' + yearLabel + ' 연차보고서', btn.dataset.href);
      });
    });

    tbody.querySelectorAll('.btn-plan').forEach((btn) => {
      btn.addEventListener('click', () => {
        const dept = sorted.find((d) => d.name === btn.dataset.dept);
        if (!dept) return;
        openTextModal(dept.name + ' - 성과관리계획(2026년 반영)', dept.evaluation.performancePlan2026);
      });
    });

    tbody.querySelectorAll('.btn-detail').forEach((btn) => {
      btn.addEventListener('click', () => {
        const dept = sorted.find((d) => d.name === btn.dataset.dept);
        if (!dept) return;
        openDetailModal(dept);
      });
    });

    tbody.querySelectorAll('.btn-email-mini').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const email = btn.dataset.email || '';
        const box = btn.closest('.contact-cell')?.querySelector('.contact-email');
        if (!box || !email) return;
        const isHidden = box.classList.contains('hidden');
        tbody.querySelectorAll('.contact-email').forEach((el) => {
          el.classList.add('hidden');
          el.innerHTML = '';
        });
        if (isHidden) {
          box.classList.remove('hidden');
          box.innerHTML = '<a class="email" href="mailto:' + escAttr(email) + '">' + esc(email) + '</a>';
        }
      });
    });
  }

  function renderApproved() {
    document.getElementById('approvedBadge').textContent = (approvedDocuments.length || 0) + '건';
    const tbody = document.getElementById('approvedBody');
    if (!approvedDocuments.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty">결재완료 공문 없음</td></tr>';
      return;
    }
    tbody.innerHTML = approvedDocuments.map((doc, i) => {
      const dept = doc.dept || '-';
      let tag = '';
      if (doc.sender && doc.sender.indexOf('리더십센터') >= 0) tag = ' <span class="tag">(리더십→교목처)</span>';
      else if (doc.sender && doc.sender.indexOf('교목팀') >= 0) tag = ' <span class="tag">(교목팀→교목처)</span>';
      const pdfCell = doc.hasPdf && doc.pdfHref
        ? '<a class="btn" href="' + escAttr(doc.pdfHref) + '" target="_blank" rel="noopener">열기</a>'
        : '<span class="badge badge-muted">없음</span>';
      return '<tr>' +
        '<td class="center-cell">' + (i + 1) + '</td>' +
        '<td>' + esc(doc.sender || '-') + '</td>' +
        '<td>' + esc(doc.title || '-') + '</td>' +
        '<td>' + esc(dept) + tag + '</td>' +
        '<td class="center-cell">' + pdfCell + '</td>' +
      '</tr>';
    }).join('');
  }

  function detailTableHtml(dept) {
    const fb = feedbackMap(dept);
    const projects = dept.projects || [];
    if (!projects.length) return '<div class="empty">사업 없음</div>';

    return '<table class="detail-table"><thead><tr>' +
      '<th>사업명</th>' +
      '<th>사업관리구분</th>' +
      '<th>예산</th>' +
      '<th>예산집행률</th>' +
      '<th>예산집행률<br>적용</th>' +
      '<th>사업이행률</th>' +
      '<th>사업환류<br><span class="th-sub">(취약요소 / 개선계획)</span></th>' +
      '<th>사업계획 및 결과</th>' +
      '</tr></thead><tbody>' +
      projects.map((p) => {
        const f = fb[p.name] || {};
        const weakness = f.weakness || '-';
        const improvement = f.improvement || '-';
        const reflux = (weakness === '-' && improvement === '-') ? '-' :
          '<div class="reflux-block"><strong>취약요소</strong><p>' + esc(weakness) + '</p>' +
          '<strong>개선계획</strong><p>' + esc(improvement) + '</p></div>';

        return '<tr>' +
          '<td class="col-name">' + esc(p.name) + '</td>' +
          '<td class="center-cell">' + esc(p.mgmtType) + '</td>' +
          '<td class="num-cell">' + fmtMoney(p.budget) + '</td>' +
          '<td class="num-cell">' + fmtPct(p.budgetExecRate) + '</td>' +
          '<td class="center-cell">' + (p.budgetExecApplied ? 'Y' : 'N') + '</td>' +
          '<td class="num-cell">' + (p.projectExecRate != null ? fmtRate(p.projectExecRate) : '-') + '</td>' +
          '<td class="col-reflux">' + reflux + '</td>' +
          '<td class="center-cell plan-result-cell">' + planResultButtons(p) + '</td>' +
        '</tr>';
      }).join('') +
      '</tbody></table>';
  }

  function planResultButtons(project) {
    const planBtn = project.planHtmlPath
      ? htmlDocButton('25사업게획', project.planHtmlPath, 'plan')
      : '<a class="btn btn-sm btn-muted-link" href="https://ir.syu.ac.kr/kuts/busiMgr3?sBusiGbn=' +
        escAttr(project.busiGbn || '113') + '" target="_blank" rel="noopener" title="IR 사업관리에서 사업계획 확인">IR계획</a>';
    const resultBtn = htmlDocButton('25사업결과', project.resultHtmlPath, 'result');
    const plan2026Btn = project.plan2026HtmlPath
      ? htmlDocButton('26사업게획', project.plan2026HtmlPath, 'plan2026')
      : '<button type="button" class="btn btn-sm" disabled title="2026 사업계획 HTML 미수집">26사업게획</button>';
    return '<div class="btn-row">' + planBtn + resultBtn + plan2026Btn + '</div>';
  }

  function htmlDocButton(label, href, kind) {
    if (!href) {
      return '<button type="button" class="btn btn-sm" disabled>' + label + '</button>';
    }
    return '<button type="button" class="btn btn-sm btn-html-doc" data-href="' +
      escAttr(href) + '" data-kind="' + escAttr(kind) + '">' + label + '</button>';
  }

  function openHtmlModal(title, href) {
    document.getElementById('htmlModalTitle').textContent = title;
    const frame = document.getElementById('htmlModalFrame');
    frame.src = href || 'about:blank';
    document.getElementById('htmlModalBackdrop').classList.add('open');
  }

  function openTextModal(title, body) {
    document.getElementById('textModalTitle').textContent = title;
    document.getElementById('textModalBody').textContent = body || '-';
    document.getElementById('textModalBackdrop').classList.add('open');
  }

  function openDetailModal(dept) {
    document.getElementById('detailModalTitle').textContent = dept.name + ' - 세부사업';
    document.getElementById('detailModalBody').innerHTML = detailTableHtml(dept);
    document.getElementById('detailModalBackdrop').classList.add('open');

    document.getElementById('detailModalBody').querySelectorAll('.btn-html-doc').forEach((btn) => {
      btn.addEventListener('click', () => {
        const kind = btn.dataset.kind === 'plan'
          ? '25사업게획'
          : btn.dataset.kind === 'plan2026'
            ? '26사업게획'
            : '25사업결과';
        const row = btn.closest('tr');
        const nameCell = row ? row.querySelector('.col-name') : null;
        const projectName = nameCell ? nameCell.textContent : '';
        openHtmlModal(dept.name + ' - ' + projectName + ' (' + kind + ')', btn.dataset.href);
      });
    });
  }

  function closeModals() {
    document.getElementById('textModalBackdrop').classList.remove('open');
    document.getElementById('detailModalBackdrop').classList.remove('open');
    document.getElementById('htmlModalBackdrop').classList.remove('open');
    document.getElementById('htmlModalFrame').src = 'about:blank';
  }

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

  function renderAll() {
    const depts = filteredDepts(document.getElementById('searchInput').value);
    renderSummary(depts);
    renderMain(depts);
    renderApproved();
  }

  document.getElementById('searchInput').addEventListener('input', renderAll);
  document.querySelectorAll('#submissionFilter .filter-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#submissionFilter .filter-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      submissionFilter = btn.dataset.filter;
      renderAll();
    });
  });
  document.getElementById('textModalClose').addEventListener('click', closeModals);
  document.getElementById('detailModalClose').addEventListener('click', closeModals);
  document.getElementById('htmlModalClose').addEventListener('click', closeModals);
  document.getElementById('textModalBackdrop').addEventListener('click', (e) => {
    if (e.target.id === 'textModalBackdrop') closeModals();
  });
  document.getElementById('detailModalBackdrop').addEventListener('click', (e) => {
    if (e.target.id === 'detailModalBackdrop') closeModals();
  });
  document.getElementById('htmlModalBackdrop').addEventListener('click', (e) => {
    if (e.target.id === 'htmlModalBackdrop') closeModals();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModals();
  });

  renderAll();
})();
