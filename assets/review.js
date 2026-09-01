const SUBMIT_EMAIL = "adventistcho@syu.ac.kr";
const STORE_KEY = "yeonchabogo-review-2025-members";
const WHO_KEY = "yeonchabogo-review-2025-who";
const PENDING_KEY = "yeonchabogo-review-2025-pending";
const OLD_KEYS = [
  "yeonchabogo-review-2025",
  "yeonchabogo-review-2025-saved",
  "yeonchabogo-review-2025-sent",
];
const EDIT_UNTIL = new Date("2026-09-18T23:59:59+09:00");
const DEADLINE_LABEL = "2026. 9. 18.(금) 23:59";

const gateBox = document.getElementById("gateBox");
const byeBox = document.getElementById("byeBox");
const byeText = document.getElementById("byeText");
const form = document.getElementById("reviewForm");
const gateName = document.getElementById("gateName");
const gateStatus = document.getElementById("gateStatus");
const whoName = document.getElementById("whoName");
const formStatus = document.getElementById("formStatus");
const saveBtn = document.getElementById("saveBtn");
const editBtn = document.getElementById("editBtn");
const submitBtn = document.getElementById("submitBtn");
const jumpSelect = document.getElementById("jumpSelect");
const reportFrame = document.getElementById("reportFrame");
const formPane = document.getElementById("formPane");

const fields = {
  good: document.getElementById("fieldGood"),
  weak: document.getElementById("fieldWeak"),
  suggest: document.getElementById("fieldSuggest"),
};

let currentName = "";
let mode = "edit";

function nowStamp() {
  const parts = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(new Date());
  const pick = (type) => parts.find((part) => part.type === type)?.value || "";
  return `${pick("year")}-${pick("month")}-${pick("day")} ${pick("hour")}:${pick("minute")}:${pick("second")}`;
}

function normalizeName(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function isPeriodOpen() {
  return Date.now() <= EDIT_UNTIL.getTime();
}

function periodHint() {
  return "평가기간: " + DEADLINE_LABEL + "까지. 제출 후에도 이 시간까지는 수정할 수 있습니다.";
}

function isSubmitted(name) {
  const store = readStore();
  return Boolean(store.submitted[name] || store.drafts[name]?.submitted);
}

function emptyStore() {
  return { drafts: {}, submitted: {} };
}

function readStore() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    const parsed = raw ? JSON.parse(raw) : emptyStore();
    parsed.drafts = parsed.drafts || {};
    parsed.submitted = parsed.submitted || {};
    return parsed;
  } catch (_err) {
    return emptyStore();
  }
}

function writeStore(store) {
  localStorage.setItem(STORE_KEY, JSON.stringify(store));
}

function setFormStatus(message, ok) {
  formStatus.textContent = message || "";
  formStatus.classList.toggle("ok", Boolean(ok));
}

function setGateStatus(message) {
  gateStatus.textContent = message || "";
}

function readValues() {
  return {
    name: currentName,
    good: fields.good.value.trim(),
    weak: fields.weak.value.trim(),
    suggest: fields.suggest.value.trim(),
  };
}

function fillValues(values) {
  fields.good.value = values?.good || "";
  fields.weak.value = values?.weak || "";
  fields.suggest.value = values?.suggest || "";
}

function clearForm() {
  fillValues({});
  setFormStatus("");
}

function showOnly(which) {
  gateBox.classList.toggle("hidden", which !== "gate");
  form.classList.toggle("hidden", which !== "form");
  byeBox.classList.toggle("hidden", which !== "bye");
  formPane.classList.add("open");
}

function setMode(next) {
  mode = next;
  const closed = next === "closed" || !isPeriodOpen();
  const locked = next !== "edit" || closed;
  Object.values(fields).forEach((el) => {
    el.readOnly = locked;
  });
  form.classList.toggle("is-locked", locked);
  saveBtn.disabled = locked || closed;
  editBtn.disabled = next === "edit" || closed;
  submitBtn.disabled = closed;
  submitBtn.textContent = isSubmitted(currentName) ? "다시 제출" : "제출";
}

function formatEmailBody(values, revision) {
  return [
    "2025학년도 연차평가 서면심의",
    revision ? "구분: 수정 제출" : "구분: 최초 제출",
    "제출시각: " + nowStamp(),
    "",
    "■ 위원 성명",
    values.name,
    "",
    "■ 잘된 점",
    values.good,
    "",
    "■ 미흡하거나 보완할 점",
    values.weak,
    "",
    "■ 제도·산식·환류에 대한 제안",
    values.suggest,
  ].join("\n");
}

function saveDraft(locked) {
  if (!currentName) return;
  const store = readStore();
  const prev = store.drafts[currentName] || {};
  store.drafts[currentName] = {
    ...prev,
    ...readValues(),
    savedAt: nowStamp(),
    mode: locked ? "saved" : "edit",
  };
  writeStore(store);
}

function markSubmitted(name) {
  const store = readStore();
  const prev = store.drafts[name] || {};
  const values = currentName === name ? readValues() : prev;
  const count = (prev.submitCount || 0) + 1;
  const stamp = nowStamp();
  store.drafts[name] = {
    ...prev,
    ...values,
    name,
    savedAt: stamp,
    mode: "saved",
    submitted: true,
    submittedAt: stamp,
    submitCount: count,
  };
  store.submitted[name] = { submittedAt: stamp, submitCount: count };
  writeStore(store);
}

function openGate() {
  currentName = "";
  sessionStorage.removeItem(WHO_KEY);
  clearForm();
  gateName.value = "";
  setGateStatus("");
  showOnly("gate");
  gateName.focus();
}

function showBye(message) {
  currentName = "";
  sessionStorage.removeItem(WHO_KEY);
  clearForm();
  byeText.textContent = message;
  showOnly("bye");
}

function openMember(name) {
  const store = readStore();
  const draft = store.drafts[name];
  const submitted = Boolean(store.submitted[name] || draft?.submitted);

  if (!isPeriodOpen()) {
    if (draft && (draft.good || draft.weak || draft.suggest)) {
      currentName = name;
      sessionStorage.setItem(WHO_KEY, name);
      whoName.textContent = name;
      fillValues(draft);
      showOnly("form");
      setMode("closed");
      setFormStatus("평가기간이 종료되어 더 이상 수정할 수 없습니다. (" + DEADLINE_LABEL + ")", false);
      return;
    }
    showBye("평가기간이 " + DEADLINE_LABEL + "에 종료되어 작성·수정할 수 없습니다.");
    return;
  }

  currentName = name;
  sessionStorage.setItem(WHO_KEY, name);
  whoName.textContent = name;
  showOnly("form");
  if (draft) {
    fillValues(draft);
    setMode("saved");
    if (submitted) {
      setFormStatus(
        "제출한 내용입니다. " + DEADLINE_LABEL + "까지 수정한 뒤 다시 제출할 수 있습니다.",
        true
      );
    } else if (draft.mode === "saved") {
      setFormStatus("임시저장본을 불러왔습니다. 수정 또는 제출하십시오. (" + (draft.savedAt || "") + ")", true);
    } else {
      setMode("edit");
      setFormStatus("이어서 작성할 수 있습니다.", true);
    }
    return;
  }
  fillValues({});
  setMode("edit");
  setFormStatus("새 서면의견입니다. " + DEADLINE_LABEL + "까지 작성·수정할 수 있습니다.", true);
  fields.good.focus();
}

function nextUrl(name) {
  const url = new URL("review.html", location.href);
  url.searchParams.set("sent", "1");
  url.searchParams.set("who", name);
  return url.toString();
}

async function submitByAjax(values, revision) {
  const body = formatEmailBody(values, revision);
  const subject =
    "[연차평가 서면심의] " + values.name + (revision ? " (수정 제출)" : "");
  const response = await fetch("https://formsubmit.co/ajax/" + SUBMIT_EMAIL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      _subject: subject,
      _template: "box",
      _captcha: "false",
      name: values.name,
      message: body,
      "위원 성명": values.name,
      "잘된 점": values.good,
      "미흡하거나 보완할 점": values.weak,
      "제도·산식·환류에 대한 제안": values.suggest,
      "서면의견 전체": body,
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.message || "제출에 실패했습니다.");
  }
  return payload;
}

function submitByPost(values, revision) {
  sessionStorage.setItem(PENDING_KEY, values.name);
  const body = formatEmailBody(values, revision);
  const subject =
    "[연차평가 서면심의] " + values.name + (revision ? " (수정 제출)" : "");
  const postForm = document.createElement("form");
  postForm.method = "POST";
  postForm.action = "https://formsubmit.co/" + SUBMIT_EMAIL;
  postForm.style.display = "none";
  const data = {
    _subject: subject,
    _template: "box",
    _captcha: "false",
    _next: nextUrl(values.name),
    name: values.name,
    message: body,
    "위원 성명": values.name,
    "잘된 점": values.good,
    "미흡하거나 보완할 점": values.weak,
    "제도·산식·환류에 대한 제안": values.suggest,
    "서면의견 전체": body,
  };
  Object.entries(data).forEach(([key, value]) => {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = key;
    input.value = value;
    postForm.appendChild(input);
  });
  document.body.appendChild(postForm);
  postForm.submit();
}

function reportDoc() {
  try {
    return reportFrame.contentDocument;
  } catch (_err) {
    return null;
  }
}

function fillJumpOptions() {
  const doc = reportDoc();
  if (!doc) return;
  doc.querySelectorAll(".department-section").forEach((section) => {
    const key = section.getAttribute("data-dept") || "";
    const title = (section.querySelector(".department-title h2")?.textContent || "")
      .replace(/\s*연차보고서\s*$/, "")
      .trim();
    if (!key) return;
    const option = document.createElement("option");
    option.value = `[data-dept="${key}"]`;
    option.textContent = title || key;
    jumpSelect.appendChild(option);
  });
}

function jumpTo(selector) {
  const doc = reportDoc();
  const win = reportFrame.contentWindow;
  if (!doc || !win) return;
  const target = selector.startsWith("#")
    ? doc.getElementById(selector.slice(1))
    : doc.querySelector(selector);
  if (!target) return;
  const top = target.getBoundingClientRect().top + win.scrollY - 12;
  win.scrollTo(0, Math.max(0, top));
}

document.getElementById("enterBtn").addEventListener("click", () => {
  const name = normalizeName(gateName.value);
  if (!name) {
    setGateStatus("위원 성명을 입력해 주십시오.");
    return;
  }
  openMember(name);
});

gateName.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    document.getElementById("enterBtn").click();
  }
});

document.getElementById("switchBtn").addEventListener("click", openGate);
document.getElementById("byeSwitch").addEventListener("click", openGate);

saveBtn.addEventListener("click", () => {
  if (!isPeriodOpen()) return;
  saveDraft(true);
  setMode("saved");
  setFormStatus("임시저장했습니다. 다음에 " + currentName + "으로 들어가면 이 내용이 열립니다.", true);
});

editBtn.addEventListener("click", () => {
  if (!isPeriodOpen()) return;
  const draft = readStore().drafts[currentName];
  if (draft) fillValues(draft);
  setMode("edit");
  setFormStatus("수정할 수 있습니다. 고친 뒤 임시저장하거나 다시 제출하십시오.", true);
  fields.good.focus();
});

form.addEventListener("input", () => {
  if (mode === "edit" && currentName) saveDraft(false);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!isPeriodOpen()) {
    setFormStatus("평가기간이 종료되어 제출할 수 없습니다.");
    return;
  }
  const honeypot = form.querySelector("[name='_gotcha']");
  if (honeypot && honeypot.value) return;
  const values = readValues();
  if (!values.name || !values.good || !values.weak || !values.suggest) {
    setFormStatus("제출하려면 세 칸을 모두 작성해 주십시오.");
    setMode("edit");
    return;
  }
  const revision = isSubmitted(values.name);
  submitBtn.disabled = true;
  setFormStatus("제출하는 중입니다. 세 칸을 메일 한 통으로 보냅니다…", true);
  try {
    await submitByAjax(values, revision);
    markSubmitted(values.name);
    setMode("saved");
    setFormStatus(
      "제출했습니다. " + DEADLINE_LABEL + "까지 같은 이름으로 들어와 수정한 뒤 다시 제출할 수 있습니다.",
      true
    );
  } catch (_err) {
    saveDraft(true);
    sessionStorage.setItem(PENDING_KEY, values.name);
    setFormStatus("메일 전송 화면으로 연결합니다.");
    submitByPost(values, revision);
  } finally {
    submitBtn.disabled = !isPeriodOpen();
  }
});

document.getElementById("formToggle").addEventListener("click", () => {
  formPane.classList.toggle("open");
});

jumpSelect.addEventListener("change", () => {
  jumpTo(jumpSelect.value);
});

reportFrame.addEventListener("load", fillJumpOptions);

(function init() {
  OLD_KEYS.forEach((key) => localStorage.removeItem(key));
  const gateNote = document.getElementById("gateNote");
  const formNote = document.getElementById("formNote");
  if (gateNote) gateNote.textContent = periodHint() + " 다른 위원 내용은 보이지 않습니다.";
  if (formNote) {
    formNote.textContent =
      "제출하면 기획처 메일로 전달됩니다. " + DEADLINE_LABEL + "까지 다시 들어와 수정한 뒤 다시 제출할 수 있습니다.";
  }
  const params = new URLSearchParams(location.search);
  const sentWho = normalizeName(params.get("who") || sessionStorage.getItem(PENDING_KEY) || "");
  if (params.get("sent") === "1" && sentWho) {
    if (sessionStorage.getItem(PENDING_KEY)) {
      markSubmitted(sentWho);
      sessionStorage.removeItem(PENDING_KEY);
    }
    openMember(sentWho);
    return;
  }
  const sessionWho = normalizeName(sessionStorage.getItem(WHO_KEY) || "");
  if (sessionWho) {
    openMember(sessionWho);
    return;
  }
  showOnly("gate");
})();
