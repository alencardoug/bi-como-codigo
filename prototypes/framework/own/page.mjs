// The page of Candidate B (docs/framework_prototype.md §2.3, §4). The engine is
// loaded at start — it carries no data —; nothing is opened before the visitor
// submits; after login the Parquet is registered in DuckDB-WASM and every query
// of the report runs there, in the browser. Logout terminates the engine's
// worker and replaces the page (§2.3 item 7). Nothing is written to any store.
import * as duckdb from "@duckdb/duckdb-wasm";
import report from "./p01.report.json" with { type: "json" };
import pins from "./pins.mjs";
import * as runner from "./report.mjs";
import * as source from "./source.mjs";

const $ = (s) => document.querySelector(s);
const el = (tag, attrs = {}, text) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text !== undefined) e.textContent = text;
  return e;
};

// A pinned body, fetched with its integrity: the browser refuses other bytes.
async function pinned(name, type) {
  const pin = pins[name];
  const response = await fetch(pin.url, { integrity: pin.integrity, credentials: "omit", mode: "cors" });
  if (!response.ok) throw new Error(`${pin.url} answered ${response.status}`);
  return URL.createObjectURL(new Blob([await response.arrayBuffer()], { type }));
}

let engine = null;  // { db, worker }
async function startEngine() {
  const [workerUrl, wasmUrl] = await Promise.all([pinned("duckdb_worker", "text/javascript"), pinned("duckdb_wasm", "application/wasm")]);
  const worker = new Worker(workerUrl);
  const db = new duckdb.AsyncDuckDB(new duckdb.VoidLogger(), worker);
  await db.instantiate(wasmUrl);
  URL.revokeObjectURL(workerUrl);
  engine = { db, worker };
  return engine;
}
const ready = startEngine();

let conn = null;
async function query(sql, params) {
  const statement = await conn.prepare(sql);
  try {
    return (await statement.query(...params)).toArray().map((row) => row.toJSON());
  } finally {
    await statement.close();
  }
}

let chartView = null;
async function render(current, last) {
  const loading = $("[data-bice=loading]");
  loading.hidden = false;
  const shown = await runner.view(report, current, last, query);
  if (chartView) chartView.finalize();
  const spec = globalThis.vegaLite.compile(report.chart.vega_lite).spec;
  chartView = new globalThis.vega.View(globalThis.vega.parse(spec), { renderer: "svg", container: $("[data-bice=chart]"), hover: false });
  chartView.data("rows", shown.chart);
  await chartView.runAsync();
  for (const t of shown.tables) $(`[data-bice=${t.bice}]`).replaceWith(table(t));
  loading.hidden = true;
}

function table(t) {
  const out = el("table", { "data-bice": t.bice });
  out.append(el("caption", {}, t.title));
  const head = el("tr");
  for (const h of t.header) head.append(el("th", { scope: "col" }, h));
  const thead = el("thead");
  thead.append(head);
  out.append(thead);
  const body = el("tbody");
  if (t.empty) {
    const tr = el("tr");
    tr.append(el("td", { colspan: String(t.header.length), "data-bice": "empty" }, t.empty));
    body.append(tr);
  }
  const partialAt = new Set(t.partialRows);
  t.cells.forEach((row, i) => {
    if (partialAt.has(i) && !partialAt.has(i - 1)) {
      const note = el("tr");
      note.append(el("td", { colspan: String(t.header.length), "data-bice": "partial" }, report.partial.text));
      body.append(note);
    }
    const tr = el("tr");
    for (const c of row) tr.append(el("td", c.empty ? { "data-bice": "empty" } : {}, c.text));
    body.append(tr);
  });
  out.append(body);
  if (t.partial && t.partialRows.length === 0) {  // the detail of the last month
    const foot = el("tfoot");
    const tr = el("tr");
    tr.append(el("td", { colspan: String(t.header.length), "data-bice": "partial" }, report.partial.text));
    foot.append(tr);
    out.append(foot);
  }
  return out;
}

async function showReport() {
  const area = $("[data-bice=report]");
  const controls = await runner.inputs(report, query);
  const current = {};
  let last = null;
  for (const input of controls) {
    const select = $(`[data-bice=${input.bice}]`);
    select.replaceChildren(...input.options.map((v) => el("option", { value: v }, v)));
    select.value = input.initial;
    current[input.id] = input.initial;
    if (input.default === "last") last = input.last;
    select.addEventListener("change", () => { current[input.id] = select.value; render(current, last); });
  }
  area.append(el("table", { "data-bice": "summary" }), el("table", { "data-bice": "detail" }));  // after the chart (§2.3)
  $("[data-bice=login]").hidden = true;
  area.hidden = false;
  await render(current, last);
}

$("[data-bice=login]").addEventListener("submit", async (event) => {
  event.preventDefault();
  const password = $("[data-bice=password]").value;
  $("[data-bice=login-error]").hidden = true;
  $("[data-bice=submit]").disabled = true;
  try {
    const parquet = await source.open(password);
    if (!parquet) {
      $("[data-bice=login-error]").hidden = false;
      return;
    }
    const { db } = await ready;
    await db.registerFileBuffer("p01.parquet", parquet);
    conn = await db.connect();
    await conn.query(`create table ${report.table} as select * from read_parquet('p01.parquet')`);
    await db.dropFile("p01.parquet");
    await showReport();
  } finally {
    $("[data-bice=submit]").disabled = false;
  }
});

$("[data-bice=logout]").addEventListener("click", async () => {
  if (chartView) chartView.finalize();
  if (engine) engine.worker.terminate();  // the worker, its database and its registered files end here
  location.replace(location.pathname);
});

ready.then(() => { $("[data-bice=password]").disabled = false; }, (error) => {
  $("[data-bice=engine-error]").hidden = false;
  console.error(error);
});
