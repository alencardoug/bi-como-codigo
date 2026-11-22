// The browser check's driver (docs/framework_prototype.md §2.6): headless
// Chrome through the DevTools protocol, on a page of the data-bice contract.
// It reads, and judges nothing: a wrong password, then the right one; under
// every filter the summary's header and cells; under every filter and each
// month asked for, the detail's; the notices; logout; and every URL Chrome's
// network stack requested. `check.py` holds the oracle and the comparator.
//
//   node check.mjs <config.json>
//
// config: {url, out, password, wrong, months: [year_month, ...], chrome?}
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const config = JSON.parse(readFileSync(process.argv[2], "utf8"));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const profile = mkdtempSync(join(tmpdir(), "bice-check-"));
// Only the local origin and the two declared third-party hosts resolve: Chrome's own
// requests to its vendor's services never reach the network, nor the record.
const chrome = spawn(config.chrome || "google-chrome", ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`,
  "--no-first-run", "--no-default-browser-check", "--disable-background-networking", "--disable-component-update", "--disable-sync",
  "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1, EXCLUDE cdn.jsdelivr.net, EXCLUDE extensions.duckdb.org",
  "--disable-features=AutofillServerCommunication",
  "--window-size=1200,2000", `--log-net-log=${join(profile, "net.json")}`, "about:blank"], { stdio: "ignore" });

let port = null;
for (let i = 0; i < 100 && !port; i++) {
  try { port = readFileSync(join(profile, "DevToolsActivePort"), "utf8").split("\n")[0]; } catch { await sleep(100); }
}
let target = null;
for (let i = 0; i < 100 && !target; i++) {
  try { target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page"); } catch { await sleep(100); }
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const pending = new Map();
const logs = [];
ws.addEventListener("message", (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); return; }
  if (d.method === "Runtime.exceptionThrown") logs.push(`exception: ${d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text}`);
  if (d.method === "Runtime.consoleAPICalled" && ["error", "warning"].includes(d.params.type)) logs.push(`${d.params.type}: ${d.params.args.map((a) => a.value ?? a.description).join(" ")}`);
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expression) => (await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true })).result?.result?.value;
const waitFor = async (expression, ms = 120000) => {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { if (await ev(expression)) return Date.now() - t0; await sleep(100); }
  return null;
};
const present = (selector) => `!!document.querySelector(${JSON.stringify(selector)})`;
// Settled: the page's loading marker hidden, where it has one, and then both tables unchanged
// for 1.5 s — a page with no marker, as Evidence's, is read once its queries have stopped
// changing what it shows.
const settled = async () => {
  if (await ev(present("[data-bice=loading]"))) await waitFor(present("[data-bice=loading][hidden]"));
  let last = null, since = Date.now();
  const t0 = Date.now();
  while (Date.now() - t0 < 120000) {
    const now = JSON.stringify([await read("summary"), await read("detail")]);
    if (now !== last) { last = now; since = Date.now(); } else if (Date.now() - since >= 1500) return Date.now() - t0;
    await sleep(250);
  }
  return null;
};
const choose = async (selector, value) => {
  await ev(`(() => { const s = document.querySelector(${JSON.stringify(selector)}); s.value = ${JSON.stringify(value)}; s.dispatchEvent(new Event('change')); })()`);
  await sleep(200);
  return settled();
};
// A table as the DOM has it: its header, its rows of cells — each cell's text, NBSP as a
// space — and the notices among its rows, in its foot and, marked by the contract, beside it
// in its wrapper. A wrapper with no table — an empty detail — has notices only.
const read = (bice) => ev(`(() => {
  const wrapper = document.querySelector('[data-bice=${bice}]');
  if (!wrapper) return null;
  const text = (e) => e.textContent.replace(/\\u00a0|\\u202f/g, ' ').trim();
  // The table shown: Evidence's DataTable keeps a full-screen copy, rows cut to the window, in a dialog before it.
  const t = wrapper.tagName === 'TABLE' ? wrapper : [...wrapper.querySelectorAll('table')].find((x) => !x.closest('dialog'));
  const beside = [...wrapper.querySelectorAll('p[data-bice=partial], p[data-bice=empty], div[data-bice=partial], div[data-bice=empty]')]
    .map((e) => ({ at: 'beside', text: text(e), ...(e.dataset.bice === 'empty' ? { empty_table: true } : {}) }));
  if (!t) return { header: [], rows: [], notices: beside };
  const rows = [], notices = [...beside];
  for (const tr of [...t.querySelectorAll('tr')].filter((r) => !r.closest('thead, tfoot'))) {  // Evidence's rows sit in no tbody
    const tds = [...tr.querySelectorAll('td')];
    if (tds.length === 1 && tds[0].dataset.bice === 'partial') { notices.push({ at: rows.length, text: text(tds[0]) }); continue; }
    if (tds.length === 1 && tds[0].hasAttribute('colspan')) { notices.push({ at: rows.length, text: text(tds[0]), empty_table: true }); continue; }
    rows.push(tds.map(text));
  }
  for (const td of t.querySelectorAll('tfoot td')) notices.push({ at: 'foot', text: text(td) });
  const heads = t.querySelectorAll('thead tr');  // the last header row: Evidence's first is of empty cells
  return { header: heads.length ? [...heads[heads.length - 1].querySelectorAll('th')].map(text) : [], rows, notices };
})()`);

const out = { url: config.url };
try {
  await send("Runtime.enable"); await send("Page.enable");
  const t0 = Date.now();
  await send("Page.navigate", { url: config.url });
  out.login_ms = await waitFor(present("[data-bice=password]:not([disabled])"));
  const submit = (pw) => ev(`(() => { const i = document.querySelector('[data-bice=password]'); i.value = ${JSON.stringify(pw)};
    i.dispatchEvent(new Event('input', { bubbles: true })); document.querySelector('[data-bice=submit]').click(); })()`);
  await submit(config.wrong);
  out.wrong = { error_ms: await waitFor(present("[data-bice=login-error]:not([hidden])"), 60000) };
  out.wrong.opened = await ev(`!!document.querySelector('table[data-bice=summary], [data-bice=summary] table, [data-bice=report]:not([hidden])')`);
  await waitFor(present("[data-bice=password]:not([disabled])"));
  await submit(config.password);
  out.summary_ms = await waitFor(present("table[data-bice=summary] td, [data-bice=summary] table td"));
  await settled();
  // Each filter by its label, as the visitor reads it — B's "todos" is its value, Evidence's is "%".
  out.filters = await ev(`[...document.querySelectorAll('[data-bice=filter] option')].map(o => [o.value, o.textContent.trim()])`);
  out.months = await ev(`[...document.querySelectorAll('[data-bice=month] option')].map(o => o.value)`);
  out.by_filter = {};
  for (const [value, f] of out.filters) {
    await choose("[data-bice=filter]", value);
    const seen = { summary: await read("summary"), detail: {} };
    for (const m of config.months) {
      await choose("[data-bice=month]", m);
      seen.detail[m] = await read("detail");
    }
    out.by_filter[f] = seen;
  }
  out.history_before_logout = await ev("history.length");
  await ev(`document.querySelector('[data-bice=logout]').click()`);
  await sleep(1000);
  out.after_logout = {
    login_ms: await waitFor(present("[data-bice=password]:not([disabled])"), 60000),
    summary: await ev(`!!document.querySelector('[data-bice=summary]')`),
    history: await ev("history.length"),
  };
  out.seconds = (Date.now() - t0) / 1000;
} catch (error) {
  out.error = String(error?.stack || error);
} finally {
  out.logs = logs;
  ws.close();
  chrome.kill();
  await sleep(1500);
  try {  // every URL Chrome's network stack requested, the workers' included
    const text = readFileSync(join(profile, "net.json"), "utf8");
    const urls = new Set([...text.matchAll(/"url":"(https?:[^"?#]+)/g)].map((m) => m[1]));
    out.hosts = [...new Set([...urls].map((u) => new URL(u).host))].sort();
    out.third_party_urls = [...urls].filter((u) => !u.startsWith(new URL(config.url).origin)).sort();
  } catch (error) {
    out.hosts = null;
    out.net_log_error = String(error);
  }
  writeFileSync(config.out, JSON.stringify(out, null, 1) + "\n");
  rmSync(profile, { recursive: true, force: true });
}
