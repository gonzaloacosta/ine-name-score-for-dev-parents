// Shared by the list page (app.js) and the name page (name.js).
import { STRINGS } from "/i18n.js";

const LANG_KEY = "name-selector-lang";
const SEX_KEY = "name-selector-sex";
const SURNAMES_KEY = "name-selector-surnames";
// Spanish words in the URL, API values in code.
const SEX_PARAM = { female: "nina", male: "nino" };

// Storage is looked up inside try: with site data blocked, merely touching
// window.localStorage throws SecurityError and would stop the whole module.
function storageGet(storageName, key) {
  try {
    return window[storageName].getItem(key);
  } catch {
    return null; // storage blocked (private mode): fall back to defaults
  }
}

function storageSet(storageName, key, value) {
  try {
    if (value === null) window[storageName].removeItem(key);
    else window[storageName].setItem(key, value);
  } catch {
    // Not persisted; the choice still applies to this visit.
  }
}

export const state = {
  lang: (() => {
    const saved = storageGet("localStorage", LANG_KEY);
    if (saved in STRINGS) return saved;
    return navigator.language?.toLowerCase().startsWith("en") ? "en" : "es";
  })(),
  sex: (() => {
    const fromUrl = new URLSearchParams(location.search).get("sexo");
    const match = Object.keys(SEX_PARAM).find((sex) => SEX_PARAM[sex] === fromUrl);
    if (match) return match;
    return storageGet("localStorage", SEX_KEY) === "male" ? "male" : "female";
  })(),
};

export function t(key, ...args) {
  const value = STRINGS[state.lang][key];
  return typeof value === "function" ? value(...args) : value;
}

export const strings = () => STRINGS[state.lang];

export function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// Bold the offending word inside the handle: "analopez" + "anal" → <b>anal</b>opez@
export function handleWithWord(handle, word) {
  const span = el("span");
  const start = word ? handle.indexOf(word) : -1;
  if (start < 0) {
    span.textContent = `${handle}@`;
    return span;
  }
  span.append(handle.slice(0, start), el("b", "", word), `${handle.slice(start + word.length)}@`);
  return span;
}

export const sexParam = (sex = state.sex) => SEX_PARAM[sex];

export function nameUrl(name) {
  return `/nombre.html?${new URLSearchParams({ nombre: name, sexo: sexParam() })}`;
}

export function listUrl() {
  return `/?${new URLSearchParams({ sexo: sexParam() })}`;
}

// Surnames travel between pages in sessionStorage, never in a URL (history, logs).
export function saveSurnames(surnames) {
  storageSet("sessionStorage", SURNAMES_KEY, surnames.length ? JSON.stringify(surnames) : null);
}

export function loadSurnames() {
  try {
    const parsed = JSON.parse(storageGet("sessionStorage", SURNAMES_KEY) || "[]");
    return Array.isArray(parsed) ? parsed.filter((s) => typeof s === "string").slice(0, 2) : [];
  } catch {
    return [];
  }
}

export function formatYears(years) {
  return years.join(state.lang === "es" ? " y " : " and ");
}

export function formatSource(data) {
  const [day, month, year] = data.census_date.split("-").reverse();
  return t("source", `${day}/${month}/${year}`, formatYears(data.birth_years));
}

/** Fill [data-i18n] nodes; sex-dependent strings receive the current sex. */
export function applyStaticStrings() {
  document.documentElement.lang = state.lang;
  document.title = t("htmlTitle", state.sex);
  for (const node of document.querySelectorAll("[data-i18n]")) {
    node.textContent = t(node.dataset.i18n, state.sex);
  }
  for (const node of document.querySelectorAll("[data-i18n-label]")) {
    node.setAttribute("aria-label", t(node.dataset.i18nLabel, state.sex));
  }
  for (const node of document.querySelectorAll("[data-i18n-placeholder]")) {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  }
  for (const button of document.querySelectorAll("[data-lang]")) {
    button.setAttribute("aria-pressed", String(button.dataset.lang === state.lang));
  }
  for (const button of document.querySelectorAll("[data-sex]")) {
    button.setAttribute("aria-pressed", String(button.dataset.sex === state.sex));
  }
}

/** Wire the ES/EN buttons; `onChange` re-renders page-specific content. */
export function bindLanguage(onChange) {
  for (const button of document.querySelectorAll("[data-lang]")) {
    button.addEventListener("click", () => {
      state.lang = button.dataset.lang;
      storageSet("localStorage", LANG_KEY, state.lang);
      applyStaticStrings();
      onChange();
    });
  }
}

export function setSex(sex) {
  state.sex = sex;
  storageSet("localStorage", SEX_KEY, sex);
  const url = new URL(location.href);
  url.searchParams.set("sexo", sexParam());
  history.replaceState(null, "", url);
  applyStaticStrings();
}
