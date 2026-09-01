const SUBMIT_EMAIL = "adventistcho@syu.ac.kr";
const DRAFT_KEY = "yeonchabogo-review-2025";

const form = document.getElementById("reviewForm");
const doneBox = document.getElementById("doneBox");
const statusEl = document.getElementById("formStatus");
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

function saveDraft() {
  localStorage.setItem(DRAFT_KEY, JSON.stringify(readValues()));
}

function restoreDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (!raw) return;
    const draft = JSON.parse(raw);
    Object.keys(fields).forEach((key) => {
      if (typeof draft[key] === "string") fields[key].value = draft[key];
    });
  } catch (_err) {
    /* ignore broken drafts */
  }
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
  const extras = [];
  doc.querySelectorAll(".department-section").forEach((section) => {
    const key = section.getAttribute("data-dept") || "";
    const title = (section.querySelector(".department-title h2")?.textContent || "")
      .replace(/\s*연차보고서\s*$/, "")
      .trim();
    if (!key) return;
    extras.push({
      value: `[data-dept="${key}"]`,
      label: title || key,
    });
  });
  extras.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = item.label;
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

function mailtoFallback(values) {
  const body = [
    `위원 성명: ${values.name}`,
    "",
    "[잘된 점]",
    values.good,
    "",
    "[미흡하거나 보완할 점]",
    values.weak,
    "",
    "[제도·산식·환류에 대한 제안]",
    values.suggest,
  ].join("\n");
  const href =
    "mailto:" +
    encodeURIComponent(SUBMIT_EMAIL) +
    "?subject=" +
    encodeURIComponent("[연차평가 서면심의] " + values.name) +
    "&body=" +
    encodeURIComponent(body);
  window.location.href = href;
}

async function submitReview(values) {
  const response = await fetch("https://formsubmit.co/ajax/" + SUBMIT_EMAIL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      name: values.name,
      "잘된 점": values.good,
      "미흡하거나 보완할 점": values.weak,
      "제도·산식·환류에 대한 제안": values.suggest,
      _subject: "[연차평가 서면심의] " + values.name,
      _template: "table",
      _captcha: "false",
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.message || "제출에 실패했습니다.");
  }
  return payload;
}

function showDone() {
  form.classList.add("hidden");
  doneBox.classList.remove("hidden");
  formPane.classList.add("open");
}

function showForm() {
  doneBox.classList.add("hidden");
  form.classList.remove("hidden");
}

form.addEventListener("input", saveDraft);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const honeypot = form.querySelector("[name='_gotcha']");
  if (honeypot && honeypot.value) {
    showDone();
    return;
  }
  const values = readValues();
  if (!values.name || !values.good || !values.weak || !values.suggest) {
    setStatus("네 칸을 모두 작성해 주십시오.");
    return;
  }
  submitBtn.disabled = true;
  setStatus("제출하는 중입니다…", true);
  try {
    await submitReview(values);
    localStorage.removeItem(DRAFT_KEY);
    form.reset();
    setStatus("");
    showDone();
  } catch (err) {
    setStatus("바로 접수가 되지 않아 메일 작성창을 엽니다. 보내기만 눌러 주시면 됩니다.");
    mailtoFallback(values);
  } finally {
    submitBtn.disabled = false;
  }
});

document.getElementById("writeAgain").addEventListener("click", () => {
  showForm();
  fields.name.focus();
});

formToggle.addEventListener("click", () => {
  formPane.classList.toggle("open");
});

jumpSelect.addEventListener("change", () => {
  jumpTo(jumpSelect.value);
});

reportFrame.addEventListener("load", fillJumpOptions);
restoreDraft();
