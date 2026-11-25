// The browser side of the report page's checks 1 to 3 (docs/report_page.md §4,
// N119): headless Chrome through the DevTools protocol, no npm package. It
// logs in, reads what the page shows — tables, the chart's SVG geometry, the
// popup at every month under every filter, the legend's and the keyboard's and
// touch's effects, the tab order, focus, a narrow screen and both colour
// schemes — and prints it as JSON. It judges nothing: tests/test_report_page.py
// compares it with what the package holds.
//
//   node tests/browser/report_page.mjs <url> <password> <cdn-cache> <cdn.json>
//
// The pinned third-party bodies are served from <cdn-cache>, by their sha256,
// through the protocol's Fetch domain: the browser still checks each one's
// integrity. BICE_CHROME names Chrome's binary.
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [url, password, cache, cdnPath] = process.argv.slice(2);
const pins = new Map(JSON.parse(readFileSync(cdnPath, "utf8")).files.map((f) => [f.url, f]));
const TYPES = { ".mjs": "text/javascript", ".js": "text/javascript", ".wasm": "application/wasm" };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const profile = mkdtempSync(join(tmpdir(), "bice-report-"));
const chrome = spawn(process.env.BICE_CHROME || "google-chrome", ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`,
  "--no-first-run", "--no-default-browser-check", "--disable-background-networking", "--disable-component-update",
  "--window-size=1280,900", "--hide-scrollbars", "about:blank"], { stdio: "ignore" });
const exited = new Promise((r) => chrome.once("exit", r));
// Chrome is waited for before its profile is removed: it writes there until it exits.
const done = async (code) => {
  try { chrome.kill(); } catch { /* gone */ }
  await Promise.race([exited, sleep(5000)]);
  try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 }); } catch { /* left in the temporary folder */ }
  process.exit(code);
};
setTimeout(() => { console.error("timeout"); done(2); }, 170_000);

let port = null;
for (let i = 0; i < 150 && !port; i++) { try { port = readFileSync(join(profile, "DevToolsActivePort"), "utf8").split("\n")[0]; } catch { await sleep(100); } }
let target = null;
for (let i = 0; i < 150 && !target; i++) { try { target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page"); } catch { await sleep(100); } }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const pending = new Map();
const errors = [];
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
ws.addEventListener("message", async (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); return; }
  if (d.method === "Runtime.exceptionThrown") errors.push(d.params.exceptionDetails.exception?.description?.split("\n")[0] || "exception");
  if (d.method === "Fetch.requestPaused") {
    const pin = pins.get(d.params.request.url);
    if (!pin) return send("Fetch.continueRequest", { requestId: d.params.requestId });
    const ext = pin.url.slice(pin.url.lastIndexOf("."));
    const body = readFileSync(join(cache, pin.sha256)).toString("base64");
    send("Fetch.fulfillRequest", { requestId: d.params.requestId, responseCode: 200, body, responseHeaders: [
      { name: "Content-Type", value: TYPES[ext] || "application/octet-stream" }, { name: "Access-Control-Allow-Origin", value: "*" }] });
  }
});
const ev = async (expression) => {
  const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (r.result?.exceptionDetails) throw new Error("evaluate: " + JSON.stringify(r.result.exceptionDetails).slice(0, 400));
  return r.result?.result?.value;
};
const waitFor = async (expr, ms = 60_000) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { if (await ev(expr)) return; await sleep(100); } throw new Error("timeout: " + expr); };
const CODES = { Tab: 9, Enter: 13, Escape: 27, End: 35, Home: 36, ArrowLeft: 37, ArrowRight: 39 };
const key = async (k, shift = false) => {
  for (const type of ["keyDown", "keyUp"]) await send("Input.dispatchKeyEvent", { type, key: k, code: k, windowsVirtualKeyCode: CODES[k], modifiers: shift ? 8 : 0 });
};
const settled = async () => { await sleep(50); await waitFor(`document.querySelector("[data-bice=loading]").hidden`); await ev(`new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r(true))))`); };

// What the page shows, read in the page.
const READ = String.raw`(() => {
  // a crosstab's empty cell is read as what is seen and what is said; a row header as such
  const cell = (td) => td.querySelector("[aria-hidden=true]") ? { mark: td.querySelector("[aria-hidden=true]").textContent, said: td.querySelector(".visually-hidden").textContent }
    : td.matches("th[scope=row]") ? { row: td.textContent } : td.textContent;
  const cells = (t) => [...t.querySelectorAll("tbody tr, tfoot tr")].map((tr) => tr.classList.contains("note") || tr.parentElement.tagName === "TFOOT"
    ? { note: tr.textContent } : [...tr.children].map(cell));
  const all = [...document.querySelectorAll("[data-bice=tables] table")];
  const tables = Object.fromEntries(all.map((t) => [t.dataset.bice, cells(t)]));
  const heads = Object.fromEntries(all.map((t) => [t.dataset.bice, [...t.querySelectorAll("thead th")].map((th) => th.textContent)]));
  const keys = Object.fromEntries(all.map((t) => [t.dataset.bice, t.closest(".table-scroll").querySelector("[data-bice=key]")?.textContent ?? null]));
  const svg = document.querySelector("[data-bice=chart] svg");
  const at = (el) => { const m = el.getScreenCTM(); return [m.e, m.f]; };
  const xLabels = [...svg.querySelectorAll(".role-axis-label text")].filter((t) => /^\d{4}-\d{2}$/.test(t.textContent)).map((t) => [t.textContent, at(t)[0]]);
  const yLabels = [...svg.querySelectorAll(".role-axis-label text")].filter((t) => !/^\d{4}-\d{2}$/.test(t.textContent)).map((t) => [t.textContent, at(t)[1]]);
  // the grid lines stand exactly at the ticks the labels name; a label's own anchor sits off its tick
  const yGrid = [...svg.querySelectorAll(".role-axis-grid > *")].map((g) => { const r = g.getBoundingClientRect(); return r.top + r.height / 2; });
  const lines = [...svg.querySelectorAll(".mark-line path")].map((p) => {
    const m = p.getScreenCTM();
    const runs = (p.getAttribute("d") || "").replace(/Z/g, "").split("M").filter(Boolean).map((run) => run.split("L").map((pt) => { const [x, y] = pt.split(",").map(Number); return [m.a * x + m.e, m.d * y + m.f]; }));
    return { layer: p.parentElement.getAttribute("class"), stroke: p.getAttribute("stroke"), opacity: Number(p.getAttribute("opacity") ?? 1), dash: p.getAttribute("stroke-dasharray"), runs };
  });
  const legend = [...document.querySelectorAll(".legend-item")].map((b) => [b.textContent, getComputedStyle(b.querySelector(".key")).backgroundColor, b.getAttribute("aria-pressed")]);
  return { tables, heads, keys, xLabels, yLabels, yGrid, lines, legend, partialMark: [...svg.querySelectorAll(".layer_3_marks text")].map((t) => t.textContent) };
})()`;
const TIP = String.raw`(() => { const t = document.querySelector("[data-bice=tip]"); if (t.hidden) return null;
  const rule = document.querySelector("[data-bice=chart] .layer_2_marks > *")?.getBoundingClientRect();
  return { month: t.querySelector("strong")?.textContent, notice: t.querySelector("em")?.textContent ?? null, ruleX: rule ? rule.left + rule.width / 2 : null,
  rows: [...t.querySelectorAll("tr")].map((tr) => [tr.children[1].textContent, tr.children[2].textContent, tr.classList.contains("near")]) }; })()`;
const RGB = (name) => `getComputedStyle(document.documentElement).getPropertyValue(${JSON.stringify(name)}).trim()`;
const STROKES = String.raw`Object.fromEntries([...document.querySelectorAll("[data-bice=chart] .layer_0_layer_0_marks path")].map((p) => [p.getAttribute("stroke"), Number(p.getAttribute("opacity") ?? 1)]))`;
const chartBox = async () => ev(`(() => { const r = document.querySelector("[data-bice=chart]").getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()`);

await send("Runtime.enable");
await send("Page.enable");
await send("Fetch.enable", { patterns: [{ urlPattern: "https://cdn.jsdelivr.net/*" }, { urlPattern: "https://extensions.duckdb.org/*" }] });
await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url });
await waitFor(`!!document.querySelector("[data-bice=password]") && !document.querySelector("[data-bice=password]").disabled`);
const out = { errors };
await send("Emulation.setDeviceMetricsOverride", { width: 360, height: 800, deviceScaleFactor: 1, mobile: true });
out.loginOverflow = await ev(`document.documentElement.scrollWidth - innerWidth`);
await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });

// A wrong password opens nothing.
await ev(`document.querySelector("[data-bice=password]").value = "nao-e-a-senha"; document.querySelector("[data-bice=login]").requestSubmit(); true`);
await waitFor(`!document.querySelector("[data-bice=login-error]").hidden`);
out.wrongPassword = await ev(`({ error: !document.querySelector("[data-bice=login-error]").hidden, report: !document.querySelector("[data-bice=report]").hidden })`);

await ev(`document.querySelector("[data-bice=password]").value = ${JSON.stringify(password)}; document.querySelector("[data-bice=login]").requestSubmit(); true`);
await waitFor(`!!document.querySelector("[data-bice=chart] svg")`);
await settled();
out.inputs = await ev(`Object.fromEntries(["filter", "month"].map((b) => { const s = document.querySelector("[data-bice=" + b + "]"); return [b, { options: [...s.options].map((o) => o.value), value: s.value }]; }))`);
out.question = await ev(`document.querySelector("[data-bice=question]").textContent`);

// Check 1, per filter: tables, chart, and the popup at every month.
out.views = {};
for (const filter of out.inputs.filter.options) {
  await ev(`(() => { const s = document.querySelector("[data-bice=filter]"); s.value = ${JSON.stringify(filter)}; s.dispatchEvent(new Event("change")); return true; })()`);
  await settled();
  const view = await ev(READ);
  await ev(`document.querySelector("[data-bice=chart]").focus(); true`);
  await key("Home");
  view.popups = [];
  for (let i = 0; i < out.inputs.month.options.length; i++) {
    await sleep(30);
    await ev(`new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r(true))))`);
    view.popups.push(await ev(TIP));
    await key("ArrowRight");
  }
  await key("Escape");
  view.announce = null;
  out.views[filter] = view;
}

// Check 2: the interactions, under every channel.
await ev(`(() => { const s = document.querySelector("[data-bice=filter]"); s.value = ${JSON.stringify(out.inputs.filter.options[0])}; s.dispatchEvent(new Event("change")); return true; })()`);
await settled();
const it = {};
const legendAt = async (n) => ev(`(() => { const r = document.querySelectorAll(".legend-item")[${n}].getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()`);
const click = async ([x, y], shift = false, count = 1) => {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  for (let c = 1; c <= count; c++) {
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: c, modifiers: shift ? 8 : 0 });
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: c, modifiers: shift ? 8 : 0 });
  }
  await sleep(150);
};
const away = async () => { await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 1, y: 1 }); await sleep(200); };
const state = async () => ({ strokes: await ev(STROKES), pressed: await ev(`[...document.querySelectorAll(".legend-item")].map((b) => b.getAttribute("aria-pressed"))`),
  all: await ev(`!document.querySelector(".legend-all").hidden`) });
await click(await legendAt(1));
await away();
it.isolateSecond = await state();
await click(await legendAt(2), true);
await away();
it.addThird = await state();
const box = await chartBox();
await click([box[0] + box[2] / 2, box[1] + 4], false, 2);
await away();
it.doubleClickPlot = await state();
await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 1, y: 1 });
const [lx, ly] = await legendAt(0);
await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: lx, y: ly });
await sleep(200);
it.hoverFirst = await state();
await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 1, y: 1 });
await sleep(200);
it.hoverAway = await state();
// a click on a line, where one series stands alone: its first point
const lone = await ev(String.raw`(() => {
  const paths = [...document.querySelectorAll("[data-bice=chart] .layer_0_layer_0_marks path")];
  const pts = paths.map((p) => { const m = p.getScreenCTM(); return (p.getAttribute("d") || "").split(/[ML]/).filter(Boolean).map((s) => { const [x, y] = s.split(",").map(Number); return [m.a * x + m.e, m.d * y + m.f]; }); });
  for (let i = 0; i < pts.length; i++) for (const [x, y] of pts[i]) {
    if (pts.every((other, j) => j === i || other.every(([ox, oy]) => Math.hypot(ox - x, oy - y) > 24))) return { stroke: paths[i].getAttribute("stroke"), at: [x, y] };
  }
  return null; })()`);
if (lone) {
  await click(lone.at);
  it.clickLine = { stroke: lone.stroke, ...(await state()) };
  await click([box[0] + box[2] / 2, box[1] + 4], false, 2);
}
// the keyboard
await ev(`document.querySelector("[data-bice=chart]").focus(); true`);
await key("End");
await sleep(100);
it.keyEnd = { tip: await ev(TIP), announce: await ev(`document.querySelector("[data-bice=announce]").textContent`) };
await key("ArrowLeft");
await sleep(100);
it.keyLeft = await ev(TIP);
await key("Escape");
it.keyEscape = await ev(TIP);
const order = await ev(`[...document.querySelectorAll(".legend-item")].map((b) => b.textContent)`);
await ev(`document.querySelectorAll(".legend-item")[1].focus(); true`);
await key("Enter", true);
await sleep(150);
it.shiftEnter = { order, ...(await state()) };
await ev(`document.querySelector(".legend-all").click(); true`);
await sleep(150);
it.restored = await state();

// Check 3: tab order and focus, from the top of the page.
await ev(`document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0); true`);
await click([2, 2]);
it.tabs = [];
for (let n = 0; n < 16; n++) {
  await key("Tab");
  const f = await ev(`(() => { const a = document.activeElement; if (!a || a === document.body) return null;
    const s = getComputedStyle(a); return { tag: a.tagName.toLowerCase(), bice: a.dataset.bice || null, cls: a.className || null, text: (a.getAttribute("aria-label") || a.textContent || "").trim().slice(0, 40),
    outline: s.outlineStyle !== "none" && parseFloat(s.outlineWidth) > 0 }; })()`);
  if (!f) break;
  it.tabs.push(f);
}
await key("Escape");
out.interactions = it;

// Narrow: 360 px, touch.
await send("Emulation.setDeviceMetricsOverride", { width: 360, height: 800, deviceScaleFactor: 1, mobile: true });
await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 });
await sleep(1500);
await settled();
out.narrow = { overflow: await ev(`document.documentElement.scrollWidth - innerWidth`) };
const nb = await chartBox();
await ev(`window.scrollTo(0, ${nb[1]} - 100); true`);
const nb2 = await chartBox();
const tap = [nb2[0] + nb2[2] * 0.5, nb2[1] + nb2[3] * 0.5];
await send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: tap[0], y: tap[1] }] });
await send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
await sleep(400);
out.narrow.tap = { x: tap[0], tip: await ev(TIP), pressed: await ev(`[...document.querySelectorAll(".legend-item")].map((b) => b.getAttribute("aria-pressed"))`),
  labels: (await ev(READ)).xLabels };
await send("Emulation.setTouchEmulationEnabled", { enabled: false });
await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });

// Both colour schemes, as the computed tokens and the chart's strokes.
out.schemes = {};
for (const scheme of ["light", "dark"]) {
  await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: scheme }] });
  await sleep(500);
  await settled();
  out.schemes[scheme] = {
    surface: await ev(RGB("--surface")), text: await ev(RGB("--text")), muted: await ev(RGB("--text-2")),
    body: await ev(`[getComputedStyle(document.body).backgroundColor, getComputedStyle(document.body).color]`),
    tokens: await ev(`[1, 2, 3, 4, 5, 6, 7, 8].map((i) => getComputedStyle(document.documentElement).getPropertyValue("--series-" + i).trim()).filter(Boolean)`),
    strokes: await ev(`[...new Set([...document.querySelectorAll("[data-bice=chart] .layer_0_layer_0_marks path")].map((p) => p.getAttribute("stroke")))]`),
  };
}

// Logout replaces the page; nothing of the report is left in it.
await ev(`document.querySelector("[data-bice=logout]").click(); true`);
await sleep(300);
await waitFor(`document.readyState === "complete" && !!document.querySelector("[data-bice=login]") && document.querySelector("[data-bice=report]").hidden`);
out.afterLogout = await ev(`({ tables: document.querySelectorAll("[data-bice=tables] table").length, svg: document.querySelectorAll("[data-bice=chart] svg").length })`);

process.stdout.write(JSON.stringify(out));
await done(0);
