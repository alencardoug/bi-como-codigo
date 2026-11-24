// The page of Candidate B (docs/framework_prototype.md §2.3, §4). The engine and
// its parquet extension are loaded at start — they carry no data —; nothing is opened before the visitor
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
  // The parquet extension, pinned, instead of the engine's own fetch of it from
  // extensions.duckdb.org: autoloading off, then LOAD of the checked bytes. The
  // fragment names the file, from which DuckDB takes the extension's entry point.
  const setup = await db.connect();
  await setup.query("SET GLOBAL autoinstall_known_extensions = false");
  await setup.query("SET GLOBAL autoload_known_extensions = false");
  for (const [name, pin] of Object.entries(pins).filter(([, p]) => p.extension)) {
    const url = await pinned(name, "application/wasm");
    await setup.query(`LOAD '${url}#/${pin.extension}.duckdb_extension.wasm'`);
    URL.revokeObjectURL(url);
  }
  await setup.close();
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

// The vertical's popup: every series at the month under the pointer, read from the
// rows the chart draws. A series with no row that month says so, as the table does.
const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
let tip = null;
// The highlighted series: the legend entry under the pointer, else the line nearest it in the plot.
let near = null, nearLegend = null, highlighted = null;
function setNear(view, name) { near = name; apply(view); }
function apply(view) {
  const next = nearLegend ?? near;
  if (next === highlighted) return;
  highlighted = next;
  requestAnimationFrame(() => view.signal("perto", highlighted).runAsync());
}
const legendValue = (item) => (item?.mark?.role === "legend-label" || item?.mark?.role === "legend-symbol") ? item.datum?.value : undefined;
// Each series as the chart draws it: its points in plot pixels, in month order, a month with no
// row skipped as the line skips it. Computed once per view.
const drawn = new WeakMap();
function segments(view) {
  if (!drawn.has(view)) {
    const xs = view.scale("x"), ys = view.scale("y"), out = new Map();
    const mid = xs.bandwidth ? xs.bandwidth() / 2 : 0;  // a line passes through the middle of each month's band
    const order = new Map(xs.domain().map((m, i) => [m, i]));
    for (const r of view.data("rows")) {
      if (!out.has(r.root_category_name)) out.set(r.root_category_name, []);
      out.get(r.root_category_name).push({ i: order.get(r.year_month), x: xs(r.year_month) + mid, y: ys(r.net_revenue_amount) });
    }
    for (const pts of out.values()) pts.sort((a, b) => a.i - b.i);
    drawn.set(view, out);
  }
  return drawn.get(view);
}
function toSegment(px, py, a, b) {
  const dx = b.x - a.x, dy = b.y - a.y, len = dx * dx + dy * dy;
  const t = len ? Math.max(0, Math.min(1, ((px - a.x) * dx + (py - a.y) * dy) / len)) : 0;
  return Math.hypot(px - (a.x + t * dx), py - (a.y + t * dy));
}
function legendLabel(view, name) {
  return [...view.container().querySelectorAll(".role-legend-label text")].find((t) => t.textContent === name);
}
function monthTooltip(view, last) {
  if (!tip) { tip = el("div", { class: "chart-tip", role: "tooltip" }); tip.hidden = true; document.body.append(tip); }
  return (_handler, event, _item, value) => {
    if (!value || value.mes === undefined) { tip.hidden = true; setNear(view, null); return; }
    const month = value.mes;
    const rows = view.data("rows").filter((r) => r.year_month === month);
    const colour = view.scale("color");
    const byRoot = new Map(rows.map((r) => [r.root_category_name, r.net_revenue_amount]));
    const roots = [...colour.domain()].sort((a, b) => (byRoot.get(b) ?? -Infinity) - (byRoot.get(a) ?? -Infinity));
    tip.replaceChildren(el("strong", {}, month));
    if (month === last) tip.append(el("em", {}, report.partial.text));
    const list = el("table");
    for (const root of roots) {
      const tr = el("tr");
      const swatch = el("td"); swatch.append(el("span", { class: "swatch", style: `background:${colour(root)}` }));
      const has = byRoot.has(root);
      tr.append(swatch, el("td", {}, root), el("td", has ? {} : { "data-bice": "empty" }, has ? brl.format(byRoot.get(root)) : "Sem vendas neste recorte."));
      list.append(tr);
    }
    tip.append(list);
    tip.hidden = false;
    // The series whose drawn line passes within 8 px of the pointer: highlighted, and a click on the
    // plot acts as a click on its legend label (shift adds it).
    // The pointer in the lines' own coordinates, through the drawn path's screen matrix.
    const ctm = view.container().querySelector(".mark-line path")?.getScreenCTM();
    if (!ctm) return;
    const px = (event.clientX - ctm.e) / ctm.a, py = (event.clientY - ctm.f) / ctm.d;
    let near = null, best = 8;
    for (const [root, pts] of segments(view)) {
      for (let i = 1; i < pts.length; i++) {
        const d = toSegment(px, py, pts[i - 1], pts[i]);
        if (d < best) { best = d; near = root; }
      }
    }
    setNear(view, near);
    for (const tr of list.querySelectorAll("tr")) tr.classList.toggle("near", tr.children[1].textContent === near);
    const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
    const left = event.clientX + pad + w > innerWidth ? event.clientX - pad - w : event.clientX + pad;
    tip.style.left = `${left + scrollX}px`;
    tip.style.top = `${Math.max(scrollY + 4, event.clientY + scrollY - h / 2)}px`;
  };
}
async function render(current, last) {
  const loading = $("[data-bice=loading]");
  loading.hidden = false;
  const shown = await runner.view(report, current, last, query);
  if (chartView) chartView.finalize();
  const spec = globalThis.vegaLite.compile(report.chart.vega_lite).spec;
  chartView = new globalThis.vega.View(globalThis.vega.parse(spec), { renderer: "svg", container: $("[data-bice=chart]"), hover: false });
  chartView.tooltip(monthTooltip(chartView, last));
  near = null; nearLegend = null; highlighted = null;
  chartView.addEventListener("pointerover", (_event, item) => { const v = legendValue(item); if (v !== undefined) { nearLegend = v; apply(chartView); } });
  chartView.addEventListener("pointerout", (_event, item) => { if (legendValue(item) !== undefined) { nearLegend = null; apply(chartView); } });
  // A double-click on the plot clears what the legend selected: the vertical's area, on top, takes the
  // events the selection's own clearing would listen to.
  chartView.addEventListener("dblclick", () => { chartView.data("legenda_store", []); chartView.runAsync(); });
  chartView.addEventListener("click", (event, item) => {
    if (!near || !item || item.mark?.marktype !== "path") return;  // the vertical's area; the legend handles its own clicks
    const label = legendLabel(chartView, near);
    if (label) label.dispatchEvent(new MouseEvent("click", { bubbles: true, shiftKey: event.shiftKey, clientX: event.clientX, clientY: event.clientY }));
  });
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
