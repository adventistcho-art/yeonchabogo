const SUBMIT_EMAIL = "adventistcho@syu.ac.kr";
const DRAFT_KEY = "yeonchabogo-review-2025";
const SAVED_KEY = "yeonchabogo-review-2025-saved";
const SENT_KEY = "yeonchabogo-review-2025-sent";

const form = document.getElementById("reviewForm");
const statusEl = document.getElementById("formStatus");
const saveBtn = document.getElementById("saveBtn");
const editBtn = document.getElementById("editBtn");
const submitBtn = document.getElementById("submitBtn");
const jumpSelect = document.getElementById("jumpSelect");
const reportFrame = document.getElementById("reportFrame");
const formPane = document.getElementById("formPane");
const formToggle = document.getElementById("formToggle");

const fields = {
  name: document.getElementById("fieldName"),
  good: document.getElementById("fieldGood"),
  weak: document.getElementById("fieldWeak"),
  suggest: document.getElementById("fieldSuggest"),
};

let mode = "edit"; // edit | saved | sent

function nowStamp() {
  const now = new Date();
  const parts = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(now);
  const pick = (type) => parts.find((part) => part.type === type)?.value || "";
  return `${pick("year")}-${pick("month")}-${pick("day")} ${pick("hour")}:${pick("minute")}:${pick("second")}`;
}

function setStatus(message, ok) {
  statusEl.textContent = message || "";
  statusEl.classList.toggle("ok", Boolean(ok));
}

function readValues() {
  return {
    name: fields.name.value.trim(),
    good: fields.good.value.trim(),
    weak: fields.weak.value.trim(),
    suggest: fields.suggest.value.trim(),
  };
}

function fillValues(values) {
  Object.keys(fields).forEach((key) => {
    fields[key].value = values?.[key] || "";
  });
}

function writeJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function readJson(key) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch (_err) {
    return null;
  }
}

function autosave() {
  writeJson(DRAFT_KEY, { ...readValues(), savedAt: nowStamp() });
}

function setMode(next) {
  mode = next;
  const locked = next !== "edit";
  Object.values(fields).forEach((el) => {
    el.readOnly = locked;
  });
  form.classList.toggle("is-locked", locked);
  saveBtn.disabled = locked;
  editBtn.disabled = next === "edit";
  submitBtn.disabled = next === "sent";
}

function formatEmailBody(values) {
  return [
    "2025학년도 연차평가 서면심의",
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

function nextUrl() {
  const url = new URL("review.html", location.href);
  url.searchParams.set("sent", "1");
  return url.toString();
}

async function submitByAjax(values) {
  const body = formatEmailBody(values);
  const response = await fetch("https://formsubmit.co/ajax/" + SUBMIT_EMAIL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      _subject: "[연차평가 서면심의] " + values.name,
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

function submitByPost(values) {
  const body = formatEmailBody(values);
  const postForm = document.createElement("form");
  postForm.method = "POST";
  postForm.action = "https://formsubmit.co/" + SUBMIT_EMAIL;
  postForm.style.display = "none";
  const data = {
    _subject: "[연차평가 서면심의] " + values.name,
    _template: "box",
    _captcha: "false",
    _next: nextUrl(),
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

function markSent(values) {
  writeJson(SENT_KEY, { ...values, sentAt: nowStamp() });
  writeJson(SAVED_KEY, { ...values, savedAt: nowStamp() });
  writeJson(DRAFT_KEY, { ...values, savedAt: nowStamp() });
  setMode("sent");
  setStatus("제출되었습니다. 네 칸이 메일 한 통으로 기획처에 전달됩니다. 고치려면 수정을 누르십시오.", true);
}

saveBtn.addEventListener("click", () => {
  const values = { ...readValues(), savedAt: nowStamp() };
  writeJson(SAVED_KEY, values);
  writeJson(DRAFT_KEY, values);
  setMode("saved");
  setStatus("임시저장했습니다. 고치려면 수정, 보내려면 제출을 누르십시오. (" + values.savedAt + ")", true);
});

editBtn.addEventListener("click", () => {
  const saved = readJson(SAVED_KEY) || readJson(SENT_KEY) || readJson(DRAFT_KEY);
  if (saved) fillValues(saved);
  setMode("edit");
  setStatus("수정할 수 있습니다. 고친 뒤 임시저장 또는 제출하십시오.", true);
  fields.name.focus();
});

form.addEventListener("input", () => {
  if (mode === "edit") autosave();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const honeypot = form.querySelector("[name='_gotcha']");
  if (honeypot && honeypot.value) return;
  const values = readValues();
  if (!values.name || !values.good || !values.weak || !values.suggest) {
    setStatus("제출하려면 네 칸을 모두 작성해 주십시오.");
    setMode("edit");
    return;
  }
  submitBtn.disabled = true;
  setStatus("제출하는 중입니다. 네 칸을 메일 한 통으로 보냅니다…", true);
  try {
    await submitByAjax(values);
    markSent(values);
  } catch (_err) {
    writeJson(SENT_KEY, { ...values, sentAt: nowStamp() });
    writeJson(SAVED_KEY, { ...values, savedAt: nowStamp() });
    setStatus("메일 전송 화면으로 연결합니다. 네 칸 전체가 한 통에 들어갑니다.");
    submitByPost(values);
  } finally {
    submitBtn.disabled = mode === "sent";
  }
});

formToggle.addEventListener("click", () => {
  formPane.classList.toggle("open");
});

jumpSelect.addEventListener("change", () => {
  jumpTo(jumpSelect.value);
});

reportFrame.addEventListener("load", fillJumpOptions);

(function init() {
  const sentFlag = new URLSearchParams(location.search).get("sent") === "1";
  const sent = readJson(SENT_KEY);
  const saved = readJson(SAVED_KEY);
  const draft = readJson(DRAFT_KEY);
  if (sentFlag && sent) {
    fillValues(sent);
    markSent(sent);
    return;
  }
  if (saved) {
    fillValues(saved);
    setMode("saved");
    setStatus("임시저장본이 있습니다. 수정 또는 제출하십시오. (" + (saved.savedAt || "") + ")", true);
    return;
  }
  if (draft) {
    fillValues(draft);
    setMode("edit");
  } else {
    setMode("edit");
    editBtn.disabled = true;
  }
})();
