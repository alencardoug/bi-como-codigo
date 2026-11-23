// The timed journey of docs/framework_prototype.md §2.7: one Chrome process on
// the profile it is given, `priming` standard journeys — login, the summary
// complete with every request finished, logout — each followed by
// quiescence, and then the measured one, with every request of every target
// it can attach (page, workers), a trace of the `devtools.timeline` and `v8`
// categories, and the page marks of one script injected before any page
// script runs: navigation start, the login box present, submit, and the first
// moment every expected cell of the summary is present with its text. The
// injected script submits itself, as soon as the password field is present and
// enabled. It reads and records; `measure.py` judges nothing either, it counts.
//
//   node journey.mjs <config.json>
//
// config: {chrome?, profile, url, password, expected: [[mês, raiz, receita, unidades], ...], priming, out}
import { spawn } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";

const config = JSON.parse(readFileSync(process.argv[2], "utf8"));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const chrome = spawn(config.chrome || "google-chrome", [
  "--headless=new", "--no-first-run", "--no-default-browser-check", "--disable-background-networking", "--disable-component-update",
  "--disable-sync", "--disable-features=AutofillServerCommunication",
  "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1, EXCLUDE cdn.jsdelivr.net, EXCLUDE extensions.duckdb.org",
  "--window-size=1200,2000", `--user-data-dir=${config.profile}`, "--remote-debugging-port=0", "about:blank",
], { stdio: ["ignore", "ignore", "pipe"] });
const wsUrl = await new Promise((resolve, reject) => {
  let err = "";
  chrome.stderr.on("data", (d) => { err += d; const m = err.match(/DevTools listening on (ws:\/\/\S+)/); if (m) resolve(m[1]); });
  chrome.on("exit", (code) => reject(new Error(`chrome exited ${code}`)));
});
const ws = new WebSocket(wsUrl);
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let nextId = 0;
const pending = new Map();
const handlers = [];
ws.addEventListener("message", (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id !== undefined && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); return; }
  for (const h of handlers) h(msg);
});
const send = (method, params = {}, sessionId) => new Promise((resolve) => {
  const id = ++nextId;
  pending.set(id, resolve);
  ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
});

// The page's marks, on one clock: performance.timeOrigin + performance.now(), wall milliseconds.
const injected = `(() => {
  const expected = ${JSON.stringify(config.expected)};
  const opensWith = ${JSON.stringify(config.password)};
  const marks = window.__biceMarks = [];
  const mark = (name) => marks.push({ mark: name, t: performance.timeOrigin + performance.now() });
  // Navigation starts when the document's request does, not when this script runs: the document's time
  // origin, on the same clock as every other mark (CMP-1-11).
  marks.push({ mark: "navigation", t: performance.timeOrigin });
  const text = (e) => e.textContent.replace(/\\u00a0|\\u202f/g, " ").trim();
  let state = "login";
  const shownSummary = () => {
    const w = document.querySelector("[data-bice=summary]");
    if (!w) return null;
    return w.tagName === "TABLE" ? w : [...w.querySelectorAll("table")].find((x) => !x.closest("dialog"));
  };
  const complete = () => {
    const t = shownSummary();
    if (!t) return false;
    const rows = new Set([...t.querySelectorAll("tr")].filter((r) => !r.closest("thead, tfoot")).map((r) => [...r.querySelectorAll("td")].map(text).join("\\u0001")));
    return expected.every((r) => rows.has(r.join("\\u0001")));
  };
  const step = () => {
    if (state === "login") {
      const field = document.querySelector("[data-bice=password]:not([disabled])");
      if (!field) return;
      mark("login_box");
      state = "submitted";
      field.value = opensWith;
      field.dispatchEvent(new Event("input", { bubbles: true }));
      mark("submit");
      document.querySelector("[data-bice=submit]").click();
    } else if (state === "submitted" && complete()) {
      mark("summary");
      state = "done";
      observer.disconnect();
    }
  };
  const observer = new MutationObserver(step);
  const start = () => { observer.observe(document, { subtree: true, childList: true, attributes: true, characterData: true }); step(); };
  if (document.readyState === "loading") document.addEventListener("readystatechange", start, { once: true }); else start();
})();`;

async function journey(measured) {
  const { result: { targetId } } = await send("Target.createTarget", { url: "about:blank" });
  const { result: { sessionId } } = await send("Target.attachToTarget", { targetId, flatten: true });
  const record = { page: null, requests: {}, sessions: {}, workers: [], trace: [], trace_lost: null };
  const sessions = new Set([sessionId]);
  // A request is one by its id across sessions: a worker's script is sent in the page's session and
  // answered in the worker's, a fetch's extra info can come in its parent's (CMP-2-07).
  const byId = new Map();
  record.page = sessionId;
  const on = (msg) => {
    if (!msg.sessionId || !sessions.has(msg.sessionId)) return;
    if (msg.method === "Target.attachedToTarget") { attach(msg); return; }  // a worker waits for us, measured or not
    if (!msg.method?.startsWith("Network.")) return;  // every journey's, the priming ones' too: their requests must finish (CMP-1-10)
    const p = msg.params;
    if (p.requestId === undefined) return;
    let key = `${msg.sessionId}:${p.requestId}`;
    if (!record.requests[key] && byId.has(p.requestId)) key = byId.get(p.requestId);
    if (!record.requests[key]) { record.requests[key] = { session: msg.sessionId, events: [] }; byId.set(p.requestId, key); }
    const r = record.requests[key];
    const s = msg.sessionId === r.session ? undefined : msg.sessionId;  // an event of another session keeps its own clock
    switch (msg.method) {
      case "Network.requestWillBeSent":
        if (p.redirectResponse) {  // a redirect reuses the request's id: each hop is kept, never overwritten (CMP-1-11)
          (r.hops ??= []).push({ url: r.url, status: p.redirectResponse.status, encoded: p.redirectResponse.encodedDataLength, ts: p.timestamp });
        }
        r.url = p.request.url; r.method = p.request.method; r.type = p.type;
        r.events.push({ e: "sent", ts: p.timestamp, wall: p.wallTime, redirect: !!p.redirectResponse });
        (record.sessions[msg.sessionId] ??= []).push([p.timestamp, p.wallTime]);
        break;
      case "Network.responseReceived": {
        const h = Object.fromEntries(Object.entries(p.response.headers).map(([k, v]) => [k.toLowerCase(), v]));
        r.status = p.response.status; r.from_disk = !!p.response.fromDiskCache; r.from_sw = !!p.response.fromServiceWorker;
        r.encoding = h["content-encoding"] || null; r.content_length = h["content-length"] || null;
        r.events.push({ e: "response", ts: p.timestamp, s });
        break;
      }
      case "Network.responseReceivedExtraInfo": r.wire_status = p.statusCode; break;
      case "Network.requestServedFromCache": r.from_memory = true; break;
      case "Network.dataReceived": r.events.push({ e: "data", ts: p.timestamp, encoded: p.encodedDataLength, decoded: p.dataLength, s }); break;
      case "Network.loadingFinished": r.finished = { ts: p.timestamp, encoded: p.encodedDataLength, s }; break;
      case "Network.loadingFailed": r.failed = { ts: p.timestamp, error: p.errorText, canceled: !!p.canceled, s }; break;
    }
  };
  async function attach(msg) {
    const child = msg.params.sessionId;
    sessions.add(child);
    record.workers.push({ type: msg.params.targetInfo.type, url: msg.params.targetInfo.url, session: child });
    await send("Network.enable", {}, child);
    await send("Target.setAutoAttach", { autoAttach: true, waitForDebuggerOnStart: true, flatten: true }, child);
    await send("Runtime.runIfWaitingForDebugger", {}, child);
  }
  handlers.push(on);
  await send("Network.enable", {}, sessionId);
  await send("Page.enable", {}, sessionId);
  await send("Runtime.enable", {}, sessionId);
  const { result: { identifier: script } } = await send("Page.addScriptToEvaluateOnNewDocument", { source: injected }, sessionId);
  await send("Target.setAutoAttach", { autoAttach: true, waitForDebuggerOnStart: true, flatten: true }, sessionId);
  let traceDone = null;
  if (measured) {
    traceDone = new Promise((resolve) => handlers.push((m) => {
      if (m.method === "Tracing.dataCollected") record.trace.push(...m.params.value);
      if (m.method === "Tracing.tracingComplete") { record.trace_lost = !!m.params.dataLossOccurred; resolve(); }
    }));
    await send("Tracing.start", { traceConfig: { includedCategories: ["devtools.timeline", "v8", "disabled-by-default-v8.compile", "v8.wasm"] }, transferMode: "ReportEvents" });
  }
  const t0 = Date.now();
  await send("Page.navigate", { url: config.url }, sessionId);
  const ev = async (e) => (await send("Runtime.evaluate", { expression: e, returnByValue: true }, sessionId)).result?.result?.value;
  let marks = [];
  while (Date.now() - t0 < 300000) {
    marks = (await ev("window.__biceMarks || []")) || [];
    if (marks.some((m) => m.mark === "summary")) break;
    await sleep(100);
  }
  // Every request of the engine and the package finished: no request in flight for 2 s.
  // blob: and data: URLs are no network: a worker started from a blob gets no loadingFinished.
  // A worker's script answered with no completion any session reported is no transfer still running:
  // it is kept unattributed, its bytes unknown to the counting, never waited for (CMP-2-07).
  const answered = (r) => r.status !== undefined || r.wire_status !== undefined;
  const bootstrap = (r) => answered(r) && record.workers.some((w) => w.url === r.url);
  const inflight = () => Object.values(record.requests).filter((r) => r.url && /^https?:/.test(r.url) && !r.finished && !r.failed && !bootstrap(r)).length;
  let quiet = Date.now();
  while (Date.now() - t0 < 360000 && Date.now() - quiet < 2000) { if (inflight()) quiet = Date.now(); await sleep(100); }
  const settled = { summary: marks.some((m) => m.mark === "summary"), quiet: !inflight() };
  for (const r of Object.values(record.requests)) if (r.url && !r.finished && !r.failed && bootstrap(r)) r.unattributed = true;
  if (measured) { await send("Tracing.end"); await traceDone; }
  if (!measured) {  // the priming journey ends with logout, as a visitor's does — and the new login page is not submitted
    await send("Page.removeScriptToEvaluateOnNewDocument", { identifier: script }, sessionId);
    const loggedOut = await ev(`!!document.querySelector('[data-bice=logout]')`);
    await ev(`document.querySelector('[data-bice=logout]')?.click()`);
    await sleep(3000);
    // logout confirmed: the login box back and no summary on the page (CMP-1-10)
    settled.logout = loggedOut && !!(await ev(`!!document.querySelector('[data-bice=password]') && !document.querySelector('[data-bice=summary] td')`));
  }
  handlers.splice(handlers.indexOf(on), 1);
  await send("Target.closeTarget", { targetId });
  // Quiescence, between journeys only — the measured one is the last of its process: no target of
  // the journey left for two seconds. A service worker of the origin is such a target until Chrome
  // stops it; how long that took is kept as evidence of the priming.
  let quiescence = null;
  if (!measured) {
    const q0 = Date.now();
    let since = Date.now(), left = [];
    while (Date.now() - since < 2000 && Date.now() - q0 < 900000) {
      const { result } = await send("Target.getTargets");
      left = result.targetInfos.filter((t) => t.type !== "browser" && t.url.startsWith(new URL(config.url).origin));
      if (left.length) since = Date.now();
      await sleep(200);
    }
    quiescence = { seconds: (Date.now() - q0) / 1000, reached: !left.length, left: left.map((t) => t.type) };
  }
  if (!measured) record.requests = {};  // a priming journey is evidence of its completion, not measured
  return { marks, ...record, settled, quiescence, seconds: (Date.now() - t0) / 1000 };
}

const out = { url: config.url, priming: config.priming, primed: [] };
try {
  for (let i = 0; i < config.priming; i++) {
    const p = await journey(false);
    out.primed.push({ marks: p.marks, seconds: p.seconds, settled: p.settled, quiescence: p.quiescence });
  }
  out.measured = await journey(true);
} catch (error) {
  out.error = String(error?.stack || error);
} finally {
  writeFileSync(config.out, JSON.stringify(out) + "\n");
  ws.close();
  chrome.kill();
  await sleep(1000);
  process.exit(0);
}
