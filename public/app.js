// List page: ranking, surnames filter, girl/boy switch and name lookup.
import {
  applyStaticStrings,
  bindLanguage,
  el,
  formatSource,
  handleWithWord,
  loadSurnames,
  nameUrl,
  saveSurnames,
  setSex,
  sexParam,
  state,
  t,
} from "./common.js";

const TOP = 20;

const form = document.getElementById("search");
const lookup = document.getElementById("lookup");
const namesList = document.getElementById("names");
const status = document.getElementById("status");
const excludedBox = document.getElementById("excluded");
const songName = document.getElementById("song-name");
const results = document.querySelector(".results");
const submitButton = form.querySelector("button[type=submit]");

let lastBody = null;
let lastFailure = null; // "error" | "invalid" | null
let sungName = null;
let requestId = 0; // ignore responses that arrive after a newer search

function sing(name) {
  if (!name || name === sungName) return;
  sungName = name;
  songName.textContent = name;
  songName.classList.remove("is-new");
  void songName.offsetWidth; // restart the entrance animation
  songName.classList.add("is-new");
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
  const row = el("a", "name-row glass");
  row.href = nameUrl(entry.name);

  const score = Math.round(entry.total * 100);
  const bar = el("span", "bar");
  const fill = el("span");
  fill.style.setProperty("--score", String(entry.total));
  bar.append(fill);
  bar.setAttribute("aria-hidden", "true");

  const scoreText = el("span", "score", String(score));
  scoreText.setAttribute("aria-label", t("scoreLabel", score));

  row.append(el("span", "rank", String(entry.rank)), el("span", "name", entry.name), bar, scoreText);
  li.append(row);
  return li;
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
    const reason = item.reasons[0];
    li.append(`${item.name} `, "→ ", handleWithWord(reason.handle, reason.word));
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
  sing(body.names[0]?.name);
  document.getElementById("source").textContent = formatSource(body.data);
}

function surnamesFromForm() {
  const data = new FormData(form);
  return ["surname1", "surname2"].map((field) => String(data.get(field) || "").trim()).filter(Boolean);
}

async function search() {
  const id = ++requestId;
  const params = new URLSearchParams({ top: String(TOP), sex: state.sex });
  // Captured now: edits made while the request is in flight were not searched.
  const surnames = surnamesFromForm();
  const [surname1, surname2] = surnames;
  if (surname1) params.set("surname1", surname1);
  if (surname2) params.set("surname2", surname2);
  if (new FormData(form).get("ascii")) params.set("ascii_only", "true");

  for (const input of form.querySelectorAll("input[name^=surname]")) input.removeAttribute("aria-invalid");
  submitButton.disabled = true;
  submitButton.textContent = t("searching");
  renderLoading();
  try {
    const response = await fetch(`api/rank?${params}`, { headers: { Accept: "application/json" } });
    if (id !== requestId) return;
    if (response.status === 422) {
      lastFailure = "invalid";
      lastBody = null;
      saveSurnames([]); // the name page must not check emails against rejected surnames
      for (const input of form.querySelectorAll("input[name^=surname]")) {
        if (input.value.trim()) input.setAttribute("aria-invalid", "true");
      }
      renderFailure("invalid");
      return;
    }
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const body = await response.json();
    if (id !== requestId) return;
    lastBody = body;
    lastFailure = null;
    saveSurnames(surnames);
    render(body);
  } catch (error) {
    if (id !== requestId) return;
    console.error("name-selector: loading names failed", error);
    lastFailure = "error";
    lastBody = null;
    renderFailure("error");
  } finally {
    if (id === requestId) {
      submitButton.disabled = false;
      submitButton.textContent = t("search");
    }
  }
}

function syncLookupSex() {
  lookup.elements.sexo.value = sexParam();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  search();
});

for (const button of document.querySelectorAll("[data-sex]")) {
  button.addEventListener("click", () => {
    if (button.dataset.sex === state.sex) return;
    setSex(button.dataset.sex);
    syncLookupSex();
    sungName = null;
    search();
  });
}

bindLanguage(() => {
  if (lastFailure) renderFailure(lastFailure);
  else if (lastBody) render(lastBody);
});

// Coming back from a name page: keep the surnames the family already typed.
loadSurnames().forEach((surname, i) => {
  form.elements[`surname${i + 1}`].value = surname;
});
applyStaticStrings();
syncLookupSex();
search();
