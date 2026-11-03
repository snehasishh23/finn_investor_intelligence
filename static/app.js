"use strict";
const $ = (s) => document.querySelector(s);
const escapeHTML = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const E = escapeHTML;
const categories = {
  results: "Results",
  mgmt: "Management",
  lit: "Regulatory",
  ma: "M&A",
  fund: "Capital",
  capex: "Capex",
  rating: "Credit rating",
  div: "Dividend",
  ins: "Ownership",
  pr: "Business update",
  routine: "Routine",
};
function stored(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) ?? fallback;
  } catch {
    return fallback;
  }
}
const savedSettings = stored("finn-settings", {});
const state = {
  view: "digest",
  mode: "demo",
  hours: 24,
  filter: "all",
  data: null,
  loading: false,
  error: "",
  settings: {
    vol: 2,
    px: 3,
    cats: ["results", "mgmt", "ma", "lit", "capex"],
    ...savedSettings,
  },
  saved: new Set(stored("finn-saved", [])),
  report: null,
  researchBusy: false,
  researchError: "",
  ticker: "TCS",
  researchToken: 0,
  loadToken: 0,
};
if (!Array.isArray(state.settings.cats)) state.settings.cats = [];
const save = () => {
  try {
    localStorage.setItem("finn-settings", JSON.stringify(state.settings));
    localStorage.setItem("finn-saved", JSON.stringify([...state.saved]));
  } catch {}
};
const fmt = (n) =>
  Number.isFinite(n)
    ? n.toLocaleString("en-IN", { maximumFractionDigits: 2 })
    : "—";
const change = (n) =>
  `<span class="${n >= 0 ? "up" : "down"}">${n > 0 ? "+" : ""}${fmt(n)}%</span>`;
function delta(a, b) {
  return a == null || b == null || b <= 0 ? "—" : change((a / b - 1) * 100);
}
function safeURL(url) {
  try {
    const u = new URL(url);
    return ["https:"].includes(u.protocol) ? E(u.href) : "";
  } catch {
    return "";
  }
}
function sourceLink(url, label = "Original filing ↗") {
  const safe = safeURL(url);
  return safe
    ? `<a href="${safe}" target="_blank" rel="noopener noreferrer">${E(label)}</a>`
    : '<span class="muted">Illustrative · no original filing</span>';
}
async function api(path, options) {
  const response = await fetch(path, options);
  const raw = await response.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error(
      response.status === 504
        ? "The hosting time limit was reached. Retry to reuse cached extraction."
        : "The server did not return a research response. Please retry shortly.",
    );
  }
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Request failed. Please retry.",
    );
  return data;
}
function signals() {
  const d = state.data;
  return {
    quotes: (d?.P || []).filter(
      (p) => p.vol >= state.settings.vol || Math.abs(p.ch) >= state.settings.px,
    ),
    filings: (d?.A || []).filter((a) => state.settings.cats.includes(a.c)),
  };
}
function notice() {
  $("#notice").innerHTML =
    `<div class="notice ${state.mode === "live" ? "live" : ""}">${state.mode === "demo" ? "<b>DEMO WORKSPACE</b> · Fictional prices, announcements and research. Switch to Live for source data." : "<b>LIVE WORKSPACE</b> · EOD prices and exchange filings. Updates while this page is open."}${state.loading ? " · Refreshing…" : ""}</div>`;
}
function card(a) {
  const demoTable = a.res
    ? `<div class="table-scroll"><table><tr><th>₹ crore · demo</th><th>Current</th><th>QoQ</th><th>YoY</th></tr>${a.res.map((r) => `<tr><td>${E(r[0])}</td><td>${fmt(r[1])}</td><td>${delta(r[1], r[2])}</td><td>${delta(r[1], r[3])}</td></tr>`).join("")}</table></div>`
    : "";
  return `<article class="card ${a.p === 3 ? "material" : ""}"><div class="card-top"><div><span class="ticker">${E(a.t)}</span><span class="tag">${E(categories[a.c] || a.c)}</span></div><span class="muted">${Math.floor(a.h)}h ago</span></div><h3>${E(a.title)}</h3><p>${E(a.sum || "Open the exchange filing for details.")}</p>${demoTable}${a.bio ? `<p><b>${E(a.bio[0])}</b> · ${E(a.bio[1])}</p>` : ""}${a.bio_notice ? `<p>${E(a.bio_notice)}</p>` : ""}<div class="card-actions">${sourceLink(a.url)}<button class="text-button ${state.saved.has(a.id) ? "saved" : ""}" data-save="${E(a.id)}">${state.saved.has(a.id) ? "Saved ✓" : "Save for later"}</button>${state.mode === "live" && a.c === "results" && safeURL(a.url) ? `<button class="text-button" data-extract="${E(a.id)}">Extract results</button>` : ""}</div><div id="result-${E(a.id)}"></div></article>`;
}
function pageHead(eyebrow, title, intro) {
  return `<div class="page-head"><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="intro">${intro}</p></div>`;
}
function digest() {
  const data = state.data,
    rows = (data?.A || [])
      .filter((a) => state.filter !== "saved" || state.saved.has(a.id))
      .sort((a, b) => b.p - a.p || a.h - b.h);
  const material = rows.filter((a) => a.p > 1),
    routine = rows.filter((a) => a.p === 1);
  return (
    pageHead(
      "YOUR DAILY EDGE",
      "The noise, filtered.",
      "What changed across your portfolio. What deserves your attention.",
    ) +
    `<div class="stats"><div class="stat"><strong>${material.length}</strong><span>Priority filings</span></div><div class="stat"><strong>${signals().quotes.length}</strong><span>EOD signals</span></div><div class="stat"><strong>${routine.length}</strong><span>Routine filings</span></div></div><div class="toolbar"><div class="chips">${[24, 72, 168].map((h) => `<button class="chip ${state.hours === h ? "selected" : ""}" data-hours="${h}">${h === 24 ? "24 hours" : h === 72 ? "3 days" : "7 days"}</button>`).join("")}</div><button class="secondary" id="refresh" ${state.loading ? "disabled" : ""}>${state.loading ? "Refreshing…" : "↻ Refresh"}</button></div><div class="chips"><button class="chip ${state.filter === "all" ? "selected" : ""}" data-filter="all">All filings</button><button class="chip ${state.filter === "saved" ? "selected" : ""}" data-filter="saved">Saved</button></div><div class="section-label">PRIORITY BRIEFING <span>${material.length} ITEMS</span></div>${material.map(card).join("") || `<div class="empty">${state.loading ? "Checking your portfolio…" : "No priority filings in this view."}</div>`}${routine.length ? `<details><summary>${routine.length} routine filings · expand to review</summary>${routine.map(card).join("")}</details>` : ""}<details class="view-portfolio"><summary>View portfolio · ${data?.P?.length || 0} available quotes</summary>${quoteList()}</details>`
  );
}
function alerts() {
  const s = signals();
  return (
    pageHead(
      "YOUR SIGNAL RULES",
      "A higher signal.",
      "Choose what earns your attention. Rules are saved on this device.",
    ) +
    `<div class="card"><h2>What counts as unusual?</h2><label class="setting" for="volume">Volume vs prior 20 sessions<strong id="volume-label">${state.settings.vol}×</strong><input id="volume" type="range" min="1.2" max="5" step="0.1" value="${state.settings.vol}"></label><label class="setting" for="price">Absolute daily price move<strong id="price-label">${state.settings.px}%</strong><input id="price" type="range" min="1" max="10" step="0.5" value="${state.settings.px}"></label><p class="small muted">ANNOUNCEMENT TYPES</p><div class="chips">${Object.entries(
      categories,
    )
      .filter(([c]) => c !== "routine")
      .map(
        ([c, label]) =>
          `<button class="chip ${state.settings.cats.includes(c) ? "selected" : ""}" aria-pressed="${state.settings.cats.includes(c)}" data-category="${c}">${label}</button>`,
      )
      .join(
        "",
      )}</div><div class="settings-note">In-app signals refresh every 60 seconds while this page is visible. EOD signals use daily closes, not intraday prices. Announcement signals use the selected ${state.hours}h digest window. No background or device notifications.</div></div><div id="signal-results">${signalResults(s)}</div>`
  );
}
function signalResults(s) {
  return `<div class="section-label">${s.quotes.length} MARKET SIGNALS · ${s.filings.length} FILING SIGNALS</div>${s.quotes.map((p) => `<article class="card"><div class="card-top"><span class="ticker">${E(p.t)}</span><span class="muted">${E(p.as_of || "DEMO CLOSE")}</span></div><h3>${change(p.ch)} · ₹${fmt(p.px)}</h3><p>${fmt(p.vol)}× average volume${p.vol >= state.settings.vol ? " · Volume threshold crossed" : ""}${Math.abs(p.ch) >= state.settings.px ? " · Price threshold crossed" : ""}</p></article>`).join("")}${s.filings.map(card).join("") || (!s.quotes.length ? '<div class="empty">No signals match your current rules.</div>' : "")}`;
}
function citations(claim, report) {
  return (claim?.citations || [])
    .map((c) => {
      const src = report.sources.find((s) => s.id === c.source);
      return src
        ? `<a class="citation" href="${safeURL(src.url)}#page=${Number(c.page)}" target="_blank" rel="noopener noreferrer">[${E(c.source)} p${Number(c.page)}]</a>`
        : "";
    })
    .join("");
}
function renderClaim(claim, report) {
  return `${E(claim?.text || "No matching delivered evidence found.")}${citations(claim, report)}`;
}
const companies = {
  RELIANCE: "Reliance Industries",
  TCS: "Tata Consultancy Services",
  HDFCBANK: "HDFC Bank",
  INFY: "Infosys",
  ICICIBANK: "ICICI Bank",
  SUNPHARMA: "Sun Pharmaceutical",
  TATAMOTORS: "Tata Motors",
  ITC: "ITC",
  LT: "Larsen & Toubro",
  BHARTIARTL: "Bharti Airtel",
  ASIANPAINT: "Asian Paints",
  TITAN: "Titan Company",
  DIXON: "Dixon Technologies",
  ETERNAL: "Eternal",
  KPITTECH: "KPIT Technologies",
  PERSISTENT: "Persistent Systems",
};
function companyRows() {
  const query = (state.companyFilter || "").toLowerCase();
  const items = Object.entries(companies).filter(
    ([symbol, name]) =>
      (state.mode === "live" ||
        ["TCS", "DIXON", "INFY", "HDFCBANK"].includes(symbol)) &&
      (symbol + " " + name).toLowerCase().includes(query),
  );
  return (
    items
      .map(
        ([symbol, name]) =>
          `<button class="company-option ${state.ticker === symbol ? "selected" : ""}" data-ticker="${symbol}" ${state.researchBusy ? "disabled" : ""}><strong>${symbol}</strong><span>${E(name)}</span></button>`,
      )
      .join("") ||
    '<p class="muted small">No matching holding. Enter any NSE ticker in the research box.</p>'
  );
}
function sectionTab(title) {
  if (/cash/i.test(title)) return "cash";
  if (/trajectory|growth|trend/i.test(title)) return "trajectory";
  if (/bull|bear/i.test(title)) return "cases";
  return "snapshot";
}
function reportHTML(r) {
  const tabs = {
    snapshot: "Snapshot",
    trajectory: "Trajectory",
    cash: "Cash quality",
    guidance: "Guidance",
    cases: "Bull / bear",
    sources: "Sources",
  };
  const current = state.researchTab || "snapshot";
  const sections = r.sections.filter((s) => sectionTab(s.title) === current);
  let body = sections
    .map(
      (s) =>
        `<section class="research-section"><h3>${E(s.title)}</h3>${s.claims.map((c) => `<div class="claim">${renderClaim(c, r)}</div>`).join("")}${s.missing ? `<p class="muted small">${E(s.missing)}</p>` : ""}</section>`,
    )
    .join("");
  if (current === "guidance")
    body = `<section><h3>Promises, meet performance.</h3><p class="muted small">Earlier explicit guidance compared with matching later results.</p>${r.guidance.map((g) => `<div class="guidance-row"><div class="guidance-head">${E(g.period)}<span class="verdict ${E(g.status)}">${E(g.status)}</span></div><div class="comparison"><div><span>PROMISED</span><p>${renderClaim(g.promise, r)}</p></div><div><span>DELIVERED</span><p>${renderClaim(g.delivered, r)}</p></div></div></div>`).join("") || '<p class="muted">No explicit, comparable guidance was found. No verdict assigned.</p>'}</section>`;
  if (current === "sources")
    body = r.sources.length
      ? `<section><h3>Open the evidence.</h3>${r.sources.map((s) => `<div class="source">${sourceLink(s.url, `${s.id} · ${s.kind} · ${s.title}`)}<div class="muted small">${s.covered_pages.length} of ${s.pages} pages represented in analysed chunks${s.partial ? " · Partial coverage" : ""}</div></div>`).join("")}<p class="muted small">${E(r.evidence_notice)}</p>${r.models ? `<p class="muted small">Extraction: ${E(r.models.extraction)} · Synthesis: ${E(r.models.synthesis)}</p>` : ""}</section>`
      : '<p class="muted">Illustrative demo. No primary documents were analysed.</p>';
  return `<div class="report-heading"><div><div class="eyebrow">${E(r.ticker)} · NSE</div><h2>${E(companies[r.ticker] || r.ticker)}</h2></div><span class="evidence-badge">${r.mode === "demo" ? "ILLUSTRATIVE DEMO" : `${r.sources.length} PRIMARY DOCUMENTS`}</span></div>${r.mode === "demo" ? '<div class="notice">Fictional research example. Switch to Live for document analysis.</div>' : r.warnings.length ? `<details class="coverage-disclosure"><summary>Partial coverage · ${r.warnings.length} source notices</summary>${r.warnings.map((w) => `<p class="small muted">${E(w)}</p>`).join("")}</details>` : ""}<div class="research-tabs" role="tablist" aria-label="Research sections">${Object.entries(
    tabs,
  )
    .map(
      ([key, label]) =>
        `<button role="tab" aria-selected="${key === current}" class="research-tab ${key === current ? "selected" : ""}" data-research-tab="${key}">${label}</button>`,
    )
    .join(
      "",
    )}</div><div class="report-content" role="tabpanel">${body || '<p class="muted">This section was not established from the available evidence.</p>'}</div>`;
}
function researchView() {
  const content = state.researchBusy
    ? `<div class="research-loading"><div class="loading"></div><h2>Reading the primary sources.</h2><p class="muted">Extracting evidence and checking document/page references.</p><p id="research-progress" class="small muted" role="status">First runs take longer than cached research.</p></div>`
    : state.researchError
      ? `<div class="research-error" role="alert"><h2>Research could not finish.</h2><p>${E(state.researchError)}</p><button class="primary" id="retry-research">Retry research ↗</button></div>`
      : state.report
        ? reportHTML(state.report)
        : '<div class="research-welcome"><div class="eyebrow">BUSINESS · CASH · GUIDANCE</div><h2>Start with a company.<br>Follow the evidence.</h2><p class="muted">Choose a holding or enter any NSE ticker. Every live claim links to the annual report or earnings-call page behind it.</p></div>';
  return (
    pageHead(
      "ON-DEMAND DUE DILIGENCE",
      "Research, with evidence.",
      "Understand the business. Test the promises. Open the source.",
    ) +
    `<div class="research-workspace"><aside class="company-picker"><label class="eyebrow" for="company-filter">COMPANIES</label><input id="company-filter" aria-label="Filter companies" placeholder="Find a holding…" value="${E(state.companyFilter || "")}"><div id="company-list">${companyRows()}</div></aside><div class="research-detail"><form class="research-form" id="research-form"><input id="ticker" aria-label="NSE ticker" placeholder="Any NSE ticker, e.g. TCS" value="${E(state.ticker)}" maxlength="28" required><button class="primary" ${state.researchBusy ? "disabled" : ""}>${state.researchBusy ? "Reading…" : "Research ↗"}</button></form><p class="small muted">${state.mode === "demo" ? "Four fictional examples. Select Live above for source-grounded analysis." : "Annual reports and transcripts only · missing evidence stays unknown."}</p><article class="research-report">${content}</article></div></div>`
  );
}

function quoteList() {
  return (
    (state.data?.P || [])
      .map(
        (p) =>
          `<button class="quote" data-ticker="${E(p.t)}"><span><strong>${E(p.t)}</strong><small>${E(p.as_of || "Illustrative")} · ${fmt(p.vol)}× vol</small></span><span class="price">₹${fmt(p.px)}<br>${change(p.ch)}</span></button>`,
      )
      .join("") || '<p class="muted small">No market data available.</p>'
  );
}
function render() {
  document
    .querySelector(".layout")
    .classList.toggle("research-layout", state.view === "research");
  notice();
  $("#content").innerHTML = (
    state.view === "digest"
      ? digest
      : state.view === "alerts"
        ? alerts
        : researchView
  )();
  $("#holdings-list").innerHTML = quoteList();
  $("#coverage").textContent =
    `${state.data?.coverage?.quotes || 0} / 16 quotes available. ${state.mode === "demo" ? "Illustrative snapshot." : "Sources: Yahoo Finance · NSE."}`;
  $("#alert-count").textContent =
    signals().quotes.length + signals().filings.length;
  document.querySelectorAll("[data-view]").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === state.view);
    b.setAttribute(
      "aria-current",
      b.dataset.view === state.view ? "page" : "false",
    );
  });
  if (state.data?.warnings?.length && state.mode === "live")
    $("#notice").insertAdjacentHTML(
      "beforeend",
      state.data.warnings
        .map((w) => `<div class="notice">${E(w)}</div>`)
        .join(""),
    );
  if (state.error)
    $("#notice").insertAdjacentHTML(
      "beforeend",
      `<p class="error" role="alert">${E(state.error)}</p>`,
    );
}
async function load() {
  const token = ++state.loadToken;
  state.loading = true;
  state.error = "";
  render();
  try {
    const d = await api(`/api/data?hours=${state.hours}&mode=${state.mode}`);
    if (token === state.loadToken) state.data = d;
  } catch (error) {
    if (token === state.loadToken) state.error = error.message;
  } finally {
    if (token === state.loadToken) {
      state.loading = false;
      render();
    }
  }
}
async function waitJob(data) {
  if (!data.job_id) return data;
  for (let i = 0; i < 600; i++) {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    const job = await api("/api/jobs/" + data.job_id);
    if (job.status === "complete") return job.result;
    if (job.status === "failed") throw new Error(job.error);
  }
  throw new Error(
    "Research is still running. Retry to reconnect to the current job.",
  );
}
async function runResearch(symbol) {
  if (state.researchBusy) return;
  state.ticker = symbol.trim().toUpperCase().replace(/\.NS$/, "");
  state.researchTab = "snapshot";
  state.researchStarted = Date.now();
  state.view = "research";
  state.researchError = "";
  state.report = null;
  state.researchBusy = true;
  const token = ++state.researchToken;
  render();
  try {
    const d = await waitJob(
      await api(
        `/api/research/${encodeURIComponent(state.ticker)}?mode=${state.mode}`,
        { method: "POST" },
      ),
    );
    if (token === state.researchToken) state.report = d;
  } catch (error) {
    if (token === state.researchToken) state.researchError = error.message;
  } finally {
    if (token === state.researchToken) {
      state.researchBusy = false;
      render();
    }
  }
}
async function extractResults(id, button) {
  const element = $("#result-" + id);
  button.disabled = true;
  element.innerHTML =
    '<p class="muted small" role="status">Reading the results filing…</p>';
  try {
    const d = await waitJob(
      await api(`/api/filings/${encodeURIComponent(id)}/results`, {
        method: "POST",
      }),
    );
    element.innerHTML = `<div class="table-scroll"><table><tr><th>₹ crore</th>${d.periods.map((p) => `<th>${E(p || "Unavailable")}</th>`).join("")}<th>QoQ</th><th>YoY</th></tr>${d.rows.map((r) => `<tr><td>${E(r.metric)} ${sourceLink(d.url + "#page=" + r.page, "p" + r.page)}</td>${r.values.map((v) => `<td>${v == null ? "—" : fmt(v)}</td>`).join("")}<td>${delta(r.values[0], r.values[1])}</td><td>${delta(r.values[0], r.values[2])}</td></tr>`).join("")}</table></div><p class="small muted">${E(d.notice)}${d.partial ? " Only the first 60,000 characters were analysed." : ""}</p>`;
  } catch (error) {
    element.innerHTML = `<p class="error" role="alert">${E(error.message)}</p>`;
  } finally {
    button.disabled = false;
  }
}
document.addEventListener("click", (event) => {
  const b = event.target.closest("button");
  if (!b) return;
  if (b.dataset.view) {
    state.view = b.dataset.view;
    render();
    window.scrollTo(0, 0);
  }
  if (b.dataset.hours) {
    state.hours = Number(b.dataset.hours);
    load();
  }
  if (b.dataset.filter) {
    state.filter = b.dataset.filter;
    render();
  }
  if (b.dataset.save) {
    state.saved.has(b.dataset.save)
      ? state.saved.delete(b.dataset.save)
      : state.saved.add(b.dataset.save);
    save();
    render();
  }
  if (b.dataset.category) {
    const cats = state.settings.cats;
    state.settings.cats = cats.includes(b.dataset.category)
      ? cats.filter((c) => c !== b.dataset.category)
      : [...cats, b.dataset.category];
    save();
    render();
  }
  if (b.dataset.researchTab) {
    state.researchTab = b.dataset.researchTab;
    render();
  }
  if (b.dataset.ticker) runResearch(b.dataset.ticker);
  if (b.dataset.extract) extractResults(b.dataset.extract, b);
  if (b.id === "refresh") load();
  if (b.id === "retry-research") runResearch(state.ticker);
});
document.addEventListener("input", (event) => {
  if (event.target.id === "company-filter") {
    state.companyFilter = event.target.value;
    $("#company-list").innerHTML = companyRows();
  }
  if (event.target.id === "volume" || event.target.id === "price") {
    const volume = event.target.id === "volume";
    state.settings[volume ? "vol" : "px"] = Number(event.target.value);
    save();
    $(volume ? "#volume-label" : "#price-label").textContent =
      event.target.value + (volume ? "×" : "%");
    $("#signal-results").innerHTML = signalResults(signals());
    $("#alert-count").textContent =
      signals().quotes.length + signals().filings.length;
  }
});
document.addEventListener("submit", (event) => {
  if (event.target.id === "research-form") {
    event.preventDefault();
    runResearch($("#ticker").value);
  }
});
$("#mode").addEventListener("change", (event) => {
  state.mode = event.target.value;
  state.data = null;
  state.report = null;
  state.researchToken++;
  state.researchBusy = false;
  state.researchError = "";
  load();
});
$("#today").textContent = new Date().toLocaleDateString("en-IN", {
  weekday: "short",
  day: "numeric",
  month: "short",
  timeZone: "Asia/Kolkata",
});
setInterval(() => {
  if (
    state.mode === "live" &&
    !document.hidden &&
    !state.loading &&
    !state.researchBusy &&
    state.view !== "research"
  )
    load();
}, 60000);
load();

setInterval(() => {
  const el = $("#research-progress");
  if (el && state.researchBusy)
    el.textContent = `Reading sources · ${Math.floor((Date.now() - state.researchStarted) / 1000)} seconds elapsed. The first run may take a few minutes.`;
}, 1000);
