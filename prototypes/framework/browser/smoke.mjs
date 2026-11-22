// A smoke run of a page in headless Chrome, through the DevTools protocol: it
// waits for the login box, submits, reads what the page shows, changes the
// filter and logs out. It is no oracle — the browser check of
// docs/framework_prototype.md §2.6 compares cells with DuckDB's results; this
// only records that the page works end to end, and what it shows, for the
// clear mode (§7 step 2).
//
//   node smoke.mjs <url> <out.json> [screenshot.png]
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [url, outPath, shot] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const profile = mkdtempSync(join(tmpdir(), "bice-smoke-"));
const chrome = spawn(process.env.BICE_CHROME || "google-chrome", ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`,
  "--no-first-run", "--no-default-browser-check", "--disable-background-networking", "--disable-component-update", "--window-size=1200,2000", `--log-net-log=${join(profile, "net.json")}`, "about:blank"], { stdio: "ignore" });

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
  if (d.method === "Log.entryAdded") logs.push(`log: ${d.params.entry.text} ${d.params.entry.url || ""}`.trim());
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expression) => (await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true })).result?.result?.value;
const waitFor = async (selector, ms = 120000) => {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { if (await ev(`!!document.querySelector(${JSON.stringify(selector)})`)) return Date.now() - t0; await sleep(100); }
  return null;
};
const choose = async (selector, value) => {
  await ev(`(() => { const s = document.querySelector(${JSON.stringify(selector)}); s.value = ${JSON.stringify(value)}; s.dispatchEvent(new Event('change')); })()`);
  await sleep(300);
  return waitFor("[data-bice=loading][hidden]");
};
const rows = (selector, pattern) => ev(`[...document.querySelectorAll('${selector} tbody tr')].map(r => r.innerText.replace(/\\u00a0/g, ' ')).filter(t => ${pattern}.test(t))`);

const out = { url };
try {
  await send("Runtime.enable"); await send("Log.enable"); await send("Page.enable");
  const t0 = Date.now();
  await send("Page.navigate", { url });
  out.login_ms = await waitFor("[data-bice=password]:not([disabled])");
  await ev(`(() => { document.querySelector('[data-bice=password]').value = 'qualquer'; document.querySelector('[data-bice=submit]').click(); })()`);
  out.summary_ms = await waitFor("[data-bice=summary] tbody tr");
  await waitFor("[data-bice=loading][hidden]");
  out.login_error_shown = await ev(`!document.querySelector('[data-bice=login-error]').hidden`);
  out.filters = await ev(`[...document.querySelectorAll('[data-bice=filter] option')].map(o => o.value)`);
  out.months = await ev(`document.querySelectorAll('[data-bice=month] option').length`);
  out.chart_svg = await ev(`!!document.querySelector('[data-bice=chart] svg')`);
  out.by_filter = {};
  for (const f of out.filters) {
    await choose("[data-bice=filter]", f);
    out.by_filter[f] = {
      summary_rows: await ev(`document.querySelectorAll('[data-bice=summary] tbody tr').length`),
      empty_cells: await ev(`document.querySelectorAll('[data-bice=summary] td[data-bice=empty]').length`),
      empty_rows: await rows("[data-bice=summary]", "/Sem vendas/"),
      zero_rows: await rows("[data-bice=summary]", "/R\\$ 0,00/"),
      partial_notices: await ev(`document.querySelectorAll('[data-bice=summary] [data-bice=partial]').length`),
      detail_rows_last_month: await ev(`document.querySelectorAll('[data-bice=detail] tbody tr').length`),
      detail_partial: await ev(`!!document.querySelector('[data-bice=detail] [data-bice=partial]')`),
    };
  }
  if (shot) writeFileSync(shot, Buffer.from((await send("Page.captureScreenshot", { format: "png" })).result.data, "base64"));
  out.history_before_logout = await ev("history.length");
  await ev(`document.querySelector('[data-bice=logout]').click()`);
  await sleep(1000);
  out.after_logout = { login_ms: await waitFor("[data-bice=password]:not([disabled])", 60000), summary: await ev(`!!document.querySelector('[data-bice=summary]')`), history: await ev("history.length") };
  out.seconds = (Date.now() - t0) / 1000;
} catch (error) {
  out.error = String(error?.stack || error);
} finally {
  out.logs = logs;
  writeFileSync(outPath, JSON.stringify(out, null, 1) + "\n");
  ws.close();
  chrome.kill();
  await sleep(1500);
  try {  // every URL Chrome's network stack requested, the workers' included: the hosts reached
    const text = readFileSync(join(profile, "net.json"), "utf8");
    const urls = new Set([...text.matchAll(/"url":"(https?:[^"?#]+)/g)].map((m) => m[1]));  // no query: Chrome's own requests carry the client's address
    out.hosts = [...new Set([...urls].map((u) => new URL(u).host))].sort();
    out.cdn_urls = [...urls].filter((u) => !u.startsWith(new URL(url).origin)).sort();
  } catch (error) {
    out.hosts = `net log unreadable: ${error}`;
  }
  writeFileSync(outPath, JSON.stringify(out, null, 1) + "\n");
  rmSync(profile, { recursive: true, force: true });
}
