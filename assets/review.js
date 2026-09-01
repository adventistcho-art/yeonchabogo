const SUBMIT_EMAIL = "adventistcho@syu.ac.kr";
const STORE_KEY = "yeonchabogo-review-2025-members";
const WHO_KEY = "yeonchabogo-review-2025-who";
const PENDING_KEY = "yeonchabogo-review-2025-pending";
const OLD_KEYS = [
  "yeonchabogo-review-2025",
  "yeonchabogo-review-2025-saved",
  "yeonchabogo-review-2025-sent",
];

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
  const locked = next !== "edit";
  Object.values(fields).forEach((el) => {
    el.readOnly = locked;
  });
  form.classList.toggle("is-locked", locked);
  saveBtn.disabled = locked;
  editBtn.disabled = next === "edit";
  submitBtn.disabled = false;
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

function saveDraft(locked) {
  if (!currentName) return;
  const store = readStore();
  store.drafts[currentName] = {
    ...readValues(),
    savedAt: nowStamp(),
    mode: locked ? "saved" : "edit",
  };
  writeStore(store);
}

function deleteDraft(name) {
  const store = readStore();
  delete store.drafts[name];
  writeStore(store);
}

function markSubmitted(name) {
  const store = readStore();
  delete store.drafts[name];
  store.submitted[name] = { submittedAt: nowStamp() };
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

function showBye(name, already) {
  currentName = "";
  sessionStorage.removeItem(WHO_KEY);
  clearForm();
  byeText.textContent = already
    ? (name || "해당 위원") + " 님은 이미 제출하셨습니다. 이 화면에서는 내용을 다시 볼 수 없습니다."
    : (name || "위원") + " 님의 제출이 완료되었습니다. 이 내용은 더 이상 이 화면에서 볼 수 없습니다.";
  showOnly("bye");
}

function openMember(name) {
  const store = readStore();
  if (store.submitted[name]) {
    showBye(name, true);
    return;
  }
  currentName = name;
  sessionStorage.setItem(WHO_KEY, name);
  whoName.textContent = name;
  const draft = store.drafts[name];
  showOnly("form");
  if (draft) {
    fillValues(draft);
    if (draft.mode === "saved") {
      setMode("saved");
      setFormStatus("임시저장본을 불러왔습니다. 수정 또는 제출하십시오. (" + (draft.savedAt || "") + ")", true);
    } else {
      setMode("edit");
      setFormStatus("이어서 작성할 수 있습니다.", true);
    }
    return;
  }
  fillValues({});
  setMode("edit");
  setFormStatus("새 서면의견입니다. 작성 후 임시저장 또는 제출하십시오.", true);
  fields.good.focus();
}

function nextUrl(name) {
  const url = new URL("review.html", location.href);
  url.searchParams.set("sent", "1");
  url.searchParams.set("who", name);
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
  sessionStorage.setItem(PENDING_KEY, values.name);
  const body = formatEmailBody(values);
  const postForm = document.createElement("form");
  postForm.method = "POST";
  postForm.action = "https://formsubmit.co/" + SUBMIT_EMAIL;
  postForm.style.display = "none";
  const data = {
    _subject: "[연차평가 서면심의] " + values.name,
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
  saveDraft(true);
  setMode("saved");
  setFormStatus("임시저장했습니다. 다음에 " + currentName + "으로 들어가면 이 내용이 열립니다.", true);
});

editBtn.addEventListener("click", () => {
  const draft = readStore().drafts[currentName];
  if (draft) fillValues(draft);
  setMode("edit");
  setFormStatus("수정할 수 있습니다.", true);
  fields.good.focus();
});

form.addEventListener("input", () => {
  if (mode === "edit" && currentName) saveDraft(false);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const honeypot = form.querySelector("[name='_gotcha']");
  if (honeypot && honeypot.value) return;
  const values = readValues();
  if (!values.name || !values.good || !values.weak || !values.suggest) {
    setFormStatus("제출하려면 세 칸을 모두 작성해 주십시오.");
    setMode("edit");
    return;
  }
  submitBtn.disabled = true;
  setFormStatus("제출하는 중입니다. 세 칸을 메일 한 통으로 보냅니다…", true);
  try {
    await submitByAjax(values);
    markSubmitted(values.name);
    showBye(values.name, false);
  } catch (_err) {
    sessionStorage.setItem(PENDING_KEY, values.name);
    setFormStatus("메일 전송 화면으로 연결합니다.");
    submitByPost(values);
  } finally {
    submitBtn.disabled = false;
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
  const params = new URLSearchParams(location.search);
  const sentWho = normalizeName(params.get("who") || sessionStorage.getItem(PENDING_KEY) || "");
  if (params.get("sent") === "1" && sentWho) {
    markSubmitted(sentWho);
    sessionStorage.removeItem(PENDING_KEY);
    showBye(sentWho, false);
    return;
  }
  const sessionWho = normalizeName(sessionStorage.getItem(WHO_KEY) || "");
  if (sessionWho) {
    openMember(sessionWho);
    return;
  }
  showOnly("gate");
})();
