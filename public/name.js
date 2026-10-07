// Name page: the web version of `name-selector explain NAME`.
import {
  applyStaticStrings,
  bindLanguage,
  el,
  formatSource,
  formatYears,
  handleWithWord,
  listUrl,
  loadSurnames,
  state,
  strings,
  t,
} from "./common.js";

const CRITERIA = ["anonymity", "ascii", "song", "spelling", "current", "systems"];

const requested = (new URLSearchParams(location.search).get("nombre") || "").trim();
const surnames = loadSurnames();
const status = document.getElementById("status");
const detail = document.getElementById("detail");

let body = null;
let failure = null; // "invalidName" | "nameError" | null

function criterionItem(key, value) {
  const [label, description] = strings().criteria[key];
  const li = el("li", "criterion glass");
  const head = el("div", "criterion-head");
  const score = Math.round(value * 100);
  const scoreText = el("span", "score", String(score));
  scoreText.setAttribute("aria-label", t("scoreLabel", score));
  const bar = el("span", "bar");
  const fill = el("span");
  fill.style.setProperty("--score", String(value));
  bar.append(fill);
  bar.setAttribute("aria-hidden", "true");
  head.append(el("h3", "", label), bar, scoreText);
  li.append(head, el("p", "hint", description));
  return li;
}

function fact(term, value) {
  const wrap = el("div", "fact");
  wrap.append(el("dt", "", term), el("dd", "", value));
  return wrap;
}

function renderHandles() {
  const box = document.getElementById("handles");
  const title = document.getElementById("handles-title");
  if (!surnames.length) {
    title.textContent = t("handlesTitleNone");
    box.replaceChildren(el("p", "hint", t("handlesHint")));
    return;
  }
  title.textContent = t("handlesTitle", surnames.join(" "));
  const list = el("ul", "handles glass");
  for (const handle of body.handles) {
    const li = el("li", handle.word ? "is-bad" : "");
    const verdict = handle.word ? t("handleBad", handle.word) : t("handleOk");
    li.append(handleWithWord(handle.handle, handle.word), el("span", "verdict", verdict));
    list.append(li);
  }
  const summary = body.excluded ? "handlesVerdictBad" : "handlesVerdictOk";
  box.replaceChildren(list, el("p", body.excluded ? "excluded-note" : "hint", t(summary)));
}

function render() {
  status.replaceChildren();
  document.getElementById("song-name").textContent = body.name;
  document.title = t("pageTitle", body.name);
  document.getElementById("total-number").textContent = String(Math.round(body.total * 100));
  let place = t("outsidePool", state.sex, formatYears(body.data.birth_years));
  if (body.rank) place = t("placeInPool", state.sex, body.rank, body.pool_size);
  else if (body.excluded) place = t("droppedFromList");
  document.getElementById("place").textContent = place;
  const note = document.getElementById("spelling-note");
  note.hidden = body.spelling_checked;
  note.textContent = body.spelling_checked ? "" : t("spellingUnchecked");

  document.getElementById("criteria").replaceChildren(...CRITERIA.map((key) => criterionItem(key, body.criteria[key])));

  const births = Object.entries(body.births);
  document.getElementById("facts").replaceChildren(
    fact(t("people", state.sex), body.in_census ? t("peopleValue", body.census_frequency, body.census_mean_age) : t("notInCensus")),
    fact(t("births"), births.length ? births.map(([year, n]) => `${year}: ${n}`).join(", ") : t("birthsOutside")),
    fact(t("shape"), t("shapeValue", body.syllables, strings().stress[body.stress] ?? body.stress)),
  );
  renderHandles();
  document.getElementById("source").textContent = formatSource(body.data);
  detail.hidden = false;
}

function renderFailure() {
  detail.hidden = true;
  const box = el("div", "notice glass");
  box.append(el("p", "", t(failure)));
  status.replaceChildren(box);
}

async function load() {
  status.replaceChildren(el("p", "hint", t("loadingName")));
  const params = new URLSearchParams({ name: requested, sex: state.sex });
  surnames.forEach((surname, i) => params.set(`surname${i + 1}`, surname));
  try {
    const response = await fetch(`api/explain?${params}`, { headers: { Accept: "application/json" } });
    if (response.status === 422) {
      failure = "invalidName";
      renderFailure();
      return;
    }
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    body = await response.json();
    failure = null;
    render();
  } catch (error) {
    console.error("name-selector: loading the name failed", error);
    failure = "nameError";
    renderFailure();
  }
}

document.getElementById("back").href = listUrl();
document.getElementById("song-name").textContent = requested;
bindLanguage(() => (failure ? renderFailure() : body && render()));
applyStaticStrings();
load();
