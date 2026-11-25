// A report page (docs/report_page.md §3): the declaration named by
// <main data-bice-declaration>, the engine started on load, and nothing
// opened before the visitor submits. After login the report's Parquet is a
// table in DuckDB-WASM and every query runs there, in the browser. Logout ends
// the engine's worker and replaces the page. Nothing is written to any store.
import * as engine from "./engine.mjs";
import * as source from "./source.mjs";
import * as runner from "./report.mjs";
import { Chart } from "./chart.mjs";
import { el, table } from "./tables.mjs";

const $ = (s) => document.querySelector(s);
const declaration = new URL($("main").dataset.biceDeclaration, location.href);
const report = await (await fetch(declaration, { cache: "no-cache" })).json();

$("[data-bice=question]").textContent = report.question;
$("[data-bice=chart-title]").textContent = report.chart.title;

let running = null;  // the engine: { db, worker }
const ready = engine.start().then((e) => (running = e));
let chart = null;

async function render(query, current, last, domain) {
  const loading = $("[data-bice=loading]");
  loading.hidden = false;
  const shown = await runner.view(report, current, last, query);
  await chart.draw(shown.chart, domain);
  $("[data-bice=tables]").replaceChildren(...shown.tables.map((t) => table(t, report.partial.text)));
  loading.hidden = true;
}

async function showReport(query) {
  const controls = await runner.inputs(report, query);
  const domain = await runner.values(report, report.chart.series_domain, query);
  const current = {};
  let last = null;
  for (const input of controls) {
    const select = $(`[data-bice=${input.bice}]`);
    select.replaceChildren(...input.options.map((v) => el("option", { value: v }, v)));
    select.value = input.initial;
    current[input.id] = input.initial;
    if (input.default === "last") last = input.last;
  }
  chart = new Chart({
    plot: $("[data-bice=chart]"), labels: $("[data-bice=labels]"), legend: $("[data-bice=legend]"),
    tip: $("[data-bice=tip]"), announce: $("[data-bice=announce]"),
  }, report, last);
  for (const input of controls) {
    const select = $(`[data-bice=${input.bice}]`);
    select.addEventListener("change", () => { current[input.id] = select.value; render(query, current, last, domain); });
  }
  $("[data-bice=login]").hidden = true;
  $("[data-bice=report]").hidden = false;
  await render(query, current, last, domain);
  $("[data-bice=filter]").focus();
}

$("[data-bice=login]").addEventListener("submit", async (event) => {
  event.preventDefault();
  const password = $("[data-bice=password]").value;
  $("[data-bice=login-error]").hidden = true;
  $("[data-bice=submit]").disabled = true;
  try {
    const parquet = await source.open(report.id, report.profile, password);
    if (!parquet) {
      $("[data-bice=login-error]").hidden = false;
      $("[data-bice=password]").select();
      return;
    }
    await ready;
    await showReport(await engine.load(running, report.table, parquet));
  } finally {
    $("[data-bice=submit]").disabled = false;
  }
});

$("[data-bice=logout]").addEventListener("click", () => {
  if (chart) chart.finalize();
  if (running) running.worker.terminate();  // the worker, its database and its registered files end here
  location.replace(location.pathname);
});

ready.then(() => { $("[data-bice=password]").disabled = false; }, (error) => {
  $("[data-bice=engine-error]").hidden = false;
  console.error(error);
});
