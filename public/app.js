import { STRINGS } from "/i18n.js";

const LANG_KEY = "name-selector-lang";
const TOP = 20;

const form = document.getElementById("search");
const namesList = document.getElementById("names");
const status = document.getElementById("status");
const excludedBox = document.getElementById("excluded");
const songName = document.getElementById("song-name");
const results = document.querySelector(".results");
const submitButton = form.querySelector("button[type=submit]");

let lang = initialLanguage();
let lastBody = null;
let lastFailure = null; // "error" | "invalid" | null
let sungName = null;

function initialLanguage() {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    if (saved in STRINGS) return saved;
  } catch {
    // Storage blocked (private mode): fall back to the browser language.
  }
  return navigator.language?.toLowerCase().startsWith("en") ? "en" : "es";
}

const t = (key, ...args) => {
  const value = STRINGS[lang][key];
  return typeof value === "function" ? value(...args) : value;
};

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function applyStaticStrings() {
  document.documentElement.lang = lang;
  document.title = t("htmlTitle");
  for (const node of document.querySelectorAll("[data-i18n]")) {
    node.textContent = t(node.dataset.i18n);
  }
  for (const button of document.querySelectorAll("[data-lang]")) {
    button.setAttribute("aria-pressed", String(button.dataset.lang === lang));
  }
}

function setLanguage(next) {
  lang = next;
  try {
    localStorage.setItem(LANG_KEY, next);
  } catch {
    // Not persisted; the choice still applies to this visit.
  }
  applyStaticStrings();
  if (lastFailure) renderFailure(lastFailure);
  else if (lastBody) render(lastBody);
}

function sing(name) {
  if (!name || name === sungName) return;
  sungName = name;
  songName.textContent = name;
  songName.classList.remove("is-new");
  void songName.offsetWidth; // restart the entrance animation
  songName.classList.add("is-new");
  for (const row of namesList.querySelectorAll(".name-row")) {
    row.setAttribute("aria-current", String(row.dataset.name === name));
  }
}

function renderLoading() {
  results.setAttribute("aria-busy", "true");
  status.replaceChildren();
  excludedBox.hidden = true;
  namesList.replaceChildren(
    ...Array.from({ length: 6 }, () => {
      const li = el("li", "skeleton");
      li.setAttribute("aria-hidden", "true");
      return li;
    }),
  );
}

function renderFailure(kind) {
  results.setAttribute("aria-busy", "false");
  namesList.replaceChildren();
  excludedBox.hidden = true;
  const box = el("div", "notice glass");
  box.append(el("p", "", t(kind)));
  if (kind === "error") {
    const retry = el("button", "primary", t("retry"));
    retry.type = "button";
    retry.addEventListener("click", search);
    box.append(retry);
  }
  status.replaceChildren(box);
}

function nameRow(entry) {
  const li = el("li");
  const row = el("button", "name-row glass");
  row.type = "button";
  row.dataset.name = entry.name;
  row.setAttribute("aria-current", String(entry.name === sungName));

  const score = Math.round(entry.total * 100);
  const bar = el("span", "bar");
  const fill = el("span");
  fill.style.setProperty("--score", String(entry.total));
  bar.append(fill);
  bar.setAttribute("aria-hidden", "true");

  const scoreText = el("span", "score", String(score));
  scoreText.setAttribute("aria-label", t("scoreLabel", score));

  row.append(el("span", "rank", String(entry.rank)), el("span", "name", entry.name), bar, scoreText);
  row.addEventListener("click", () => sing(entry.name));
  li.append(row);
  return li;
}

// Bold the offending word inside the handle: "analopez" + "anal" → <b>anal</b>opez@
function handleWithWord(reason) {
  const span = el("span");
  const start = reason.handle.indexOf(reason.word);
  if (start < 0) {
    span.textContent = `${reason.handle}@`;
    return span;
  }
  span.append(
    reason.handle.slice(0, start),
    el("b", "", reason.word),
    `${reason.handle.slice(start + reason.word.length)}@`,
  );
  return span;
}

function renderExcluded(excluded) {
  if (!excluded.length) {
    excludedBox.hidden = true;
    excludedBox.replaceChildren();
    return;
  }
  const list = el("ul");
  for (const item of excluded) {
    const li = el("li");
    li.append(`${item.name} `, "→ ", handleWithWord(item.reasons[0]));
    list.append(li);
  }
  excludedBox.replaceChildren(el("h3", "", t("excludedTitle", excluded.length)), list);
  excludedBox.hidden = false;
}

function render(body) {
  results.setAttribute("aria-busy", "false");
  if (body.names.length) {
    // #status is a live region: screen readers hear the outcome of every search.
    status.replaceChildren(el("p", "summary hint", t("summary", body.names.length, body.excluded.length)));
  } else {
    const box = el("div", "notice glass");
    box.append(el("p", "", t("empty")));
    status.replaceChildren(box);
  }
  namesList.replaceChildren(...body.names.map(nameRow));
  renderExcluded(body.excluded);
  if (!body.names.some((n) => n.name === sungName)) sing(body.names[0]?.name);

  const [day, month, year] = body.data.census_date.split("-").reverse();
  const years = body.data.birth_years.join(lang === "es" ? " y " : " and ");
  document.getElementById("source").textContent = t("source", `${day}/${month}/${year}`, years);
}

async function search() {
  const data = new FormData(form);
  const params = new URLSearchParams({ top: String(TOP) });
  for (const field of ["surname1", "surname2"]) {
    const value = String(data.get(field) || "").trim();
    if (value) params.set(field, value);
  }
  if (data.get("ascii")) params.set("ascii_only", "true");

  for (const input of form.querySelectorAll("input[name^=surname]")) input.removeAttribute("aria-invalid");
  submitButton.disabled = true;
  submitButton.textContent = t("searching");
  renderLoading();
  try {
    const response = await fetch(`/api/rank?${params}`, { headers: { Accept: "application/json" } });
    if (response.status === 422) {
      lastFailure = "invalid";
      lastBody = null;
      for (const input of form.querySelectorAll("input[name^=surname]")) {
        if (input.value.trim()) input.setAttribute("aria-invalid", "true");
      }
      renderFailure("invalid");
      return;
    }
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    lastBody = await response.json();
    lastFailure = null;
    render(lastBody);
  } catch (error) {
    console.error("name-selector: loading names failed", error);
    lastFailure = "error";
    lastBody = null;
    renderFailure("error");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = t("search");
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  search();
});

for (const button of document.querySelectorAll("[data-lang]")) {
  button.addEventListener("click", () => setLanguage(button.dataset.lang));
}

applyStaticStrings();
search();
