// The browser diagnostic's driver (docs/framework_prototype.md §2.5.3).
//
// Starts headless Chrome on a fresh profile used for this journey only, attaches
// the DevTools protocol to every target it can reach — recursively, paused at
// start —, injects ./instrument.js before any page script, runs the fixed
// journey against the page contract (data-bice attributes), and writes what it
// observed, and what it could not, to <out>/raw.json, the response bodies to
// <out>/bodies/. It judges nothing: diagnose.py reads what it wrote.
//
//   node diagnostic.mjs <config.json>
//
// config: { url, out, profile, password, wrong, chrome?, fulfill?: {url: b64} }

import { spawn } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const config = JSON.parse(readFileSync(process.argv[2], "utf8"));
const here = path.dirname(fileURLToPath(import.meta.url));
const instrument = readFileSync(path.join(here, "instrument.js"), "utf8");
mkdirSync(path.join(config.out, "bodies"), { recursive: true });

const raw = { events: [], marks: [], committed: [], targets: {}, requests: {}, unobserved: [], end: {}, errors: [] };
const wall = () => Date.now();
const trace = (...a) => { if (process.env.BICE_TRACE) console.error(new Date().toISOString(), ...a); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const chrome = spawn(config.chrome || "google-chrome", [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--disable-background-networking",
  "--disable-component-update", "--disable-sync",
  // Only the local server resolves: Chrome's own requests to Google (autofill,
  // the search page's async calls) would otherwise fill the HTTP cache with
  // bodies that are no part of the journey, read as leads (PROTO-3-09). A
  // pinned third-party body is fulfilled by interception, before any lookup.
  "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1", "--disable-features=AutofillServerCommunication",
  `--user-data-dir=${config.profile}`, "--remote-debugging-port=0", "about:blank",
], { stdio: ["ignore", "ignore", "pipe"] });
const wsUrl = await new Promise((resolve, reject) => {
  let err = "";
  chrome.stderr.on("data", (d) => { err += d; const m = err.match(/DevTools listening on (ws:\/\/\S+)/); if (m) resolve(m[1]); });
  chrome.on("exit", (code) => reject(new Error(`chrome exited ${code}: ${err.slice(-2000)}`)));
});

const ws = new WebSocket(wsUrl);
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let nextId = 0;
const pending = new Map();
const handlers = [];
ws.addEventListener("message", (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id !== undefined && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); return; }
  for (const h of handlers) { try { h(msg); } catch (e) { raw.errors.push(String(e)); } }
});
const send = (method, params = {}, sessionId, ms = 60000) => new Promise((resolve) => {
  const id = ++nextId;
  const timer = setTimeout(() => { pending.delete(id); resolve({ error: { message: `no answer to ${method} in ${ms} ms` } }); }, ms);
  pending.set(id, (msg) => { clearTimeout(timer); resolve(msg); });
  trace("send", method);
  ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
});
const call = async (method, params, sessionId) => {
  const r = await send(method, params, sessionId);
  if (r.error) throw new Error(`${method}: ${r.error.message}`);
  return r.result;
};

let pageSession = null;
let bodyCount = 0;
const autoAttach = { autoAttach: true, waitForDebuggerOnStart: true, flatten: true };

handlers.push(async (msg) => {
  const { method, params, sessionId } = msg;
  if (method === "Target.attachedToTarget") {
    const s = params.sessionId;
    const info = params.targetInfo;
    if (/^(chrome|chrome-extension|devtools):/.test(info.url) || ["browser_ui", "background_page", "tab"].includes(info.type)) {
      await send("Runtime.runIfWaitingForDebugger", {}, s);  // Chrome's own targets: not the page's
      await send("Target.detachFromTarget", { sessionId: s });
      return;
    }
    raw.targets[info.targetId] = { type: info.type, url: info.url, attached: wall(), session: s };
    // Every setup step rejects on a protocol error, so that a collector that
    // could not start is listed as unobserved (PROTO-1-12).
    const steps = [call("Runtime.enable", {}, s), call("Network.enable", {}, s), call("Target.setAutoAttach", autoAttach, s)];
    if (info.type === "page" || info.type === "iframe") {
      steps.push(call("Page.enable", {}, s), call("Page.addScriptToEvaluateOnNewDocument", { source: instrument }, s), call("DOMStorage.enable", {}, s));
      if (config.fulfill) steps.push(call("Fetch.enable", { patterns: Object.keys(config.fulfill).map((u) => ({ urlPattern: u })) }, s));
      if (info.type === "page" && !pageSession) pageSession = s;
    } else {
      // A worker is held before its first script by an instrumentation
      // breakpoint, where the hooks are evaluated; then it runs (Debugger.paused).
      raw.targets[info.targetId].pendingInstrument = true;
      steps.push(call("Debugger.enable", {}, s), call("Debugger.setInstrumentationBreakpoint", { instrumentation: "beforeScriptExecution" }, s));
    }
    const results = await Promise.allSettled(steps);
    results.forEach((r, n) => { if (r.status === "rejected") raw.unobserved.push({ target: info.type, url: info.url, what: `collector setup step ${n}`, why: String(r.reason) }); });
    await send("Runtime.runIfWaitingForDebugger", {}, s);
  } else if (method === "Debugger.paused") {
    const entry = Object.values(raw.targets).find((t) => t.session === sessionId);
    if (entry && entry.pendingInstrument && params.reason === "instrumentation") {
      entry.pendingInstrument = false;
      const r = await send("Runtime.evaluate", { expression: instrument }, sessionId, 10000);
      if (r.error || r.result?.exceptionDetails) raw.unobserved.push({ target: entry.type, url: entry.url, what: "hooks", why: r.error?.message || r.result.exceptionDetails.text });
      await send("Debugger.removeInstrumentationBreakpoint", { instrumentation: "beforeScriptExecution" }, sessionId);
      entry.instrumented = true;
    }
    await send("Debugger.resume", {}, sessionId);
  } else if (method === "Target.detachedFromTarget") {
    for (const t of Object.values(raw.targets)) if (t.session === params.sessionId) t.detached = wall();
  } else if (method === "DOMStorage.domStorageItemAdded" || method === "DOMStorage.domStorageItemUpdated") {
    raw.committed.push({ store: params.storageId.isLocalStorage ? "localStorage" : "sessionStorage", op: method.split(".")[1], key: params.key, value: params.newValue, t: wall() });
  } else if (method === "DOMStorage.domStorageItemRemoved" || method === "DOMStorage.domStorageItemsCleared") {
    raw.committed.push({ store: params.storageId.isLocalStorage ? "localStorage" : "sessionStorage", op: method.split(".")[1], key: params.key ?? null, t: wall() });
  } else if (method === "Storage.cacheStorageContentUpdated" || method === "Storage.cacheStorageListUpdated" || method === "Storage.indexedDBContentUpdated" || method === "Storage.indexedDBListUpdated") {
    raw.committed.push({ store: method.includes("cache") ? "CacheStorage" : "indexedDB", op: method.split(".")[1], key: params.cacheName ?? params.databaseName ?? null, t: wall() });
    if (method === "Storage.cacheStorageContentUpdated") {
      // Read the cache's content when it changes, so a write deleted before the end is still seen (PROTO-2-09).
      try {
        const names = await call("CacheStorage.requestCacheNames", { securityOrigin: params.origin }, sessionId);
        for (const cache of names.caches.filter((x) => x.cacheName === params.cacheName)) {
          const entries = await call("CacheStorage.requestEntries", { cacheId: cache.cacheId, skipCount: 0, pageSize: 100 }, sessionId);
          for (const entry of entries.cacheDataEntries) {
            const res = await call("CacheStorage.requestCachedResponse", { cacheId: cache.cacheId, requestURL: entry.requestURL, requestHeaders: entry.requestHeaders }, sessionId);
            raw.committed.push({ store: "CacheStorage", op: "content read", key: entry.requestURL, value_b64: res.response.body, t: wall() });
          }
        }
      } catch (e) {
        raw.unobserved.push({ what: `CacheStorage content of ${params.cacheName}`, why: String(e) });
      }
    }
  } else if (method === "Runtime.consoleAPICalled") {
    const a = params.args || [];
    if (a[0] && a[0].value === "__bice__" && a[1]) {
      const target = Object.entries(raw.targets).find(([, t]) => t.session === sessionId);
      raw.events.push({ ...JSON.parse(a[1].value), target: target ? target[0] : null, targetType: target ? target[1].type : null });
    }
  } else if (method === "Network.requestWillBeSent") {
    raw.requests[params.requestId] = { url: params.request.url, method: params.request.method, session: sessionId, wallTime: params.wallTime, timestamp: params.timestamp };
  } else if (method === "Network.responseReceived") {
    const r = raw.requests[params.requestId] || (raw.requests[params.requestId] = {});
    Object.assign(r, { status: params.response.status, fromDiskCache: params.response.fromDiskCache, fromServiceWorker: params.response.fromServiceWorker, encoding: params.response.headers["content-encoding"] || params.response.headers["Content-Encoding"] || null });
  } else if (method === "Network.requestServedFromCache") {
    (raw.requests[params.requestId] ||= {}).fromMemoryCache = true;
  } else if (method === "Network.loadingFinished") {
    const r = raw.requests[params.requestId] || (raw.requests[params.requestId] = {});
    r.encodedDataLength = params.encodedDataLength;
    const body = await send("Network.getResponseBody", { requestId: params.requestId }, sessionId);
    if (body.error) { r.body = null; raw.unobserved.push({ url: r.url, what: "response body", why: body.error.message }); return; }
    const file = `${++bodyCount}.bin`;
    writeFileSync(path.join(config.out, "bodies", file), Buffer.from(body.result.body, body.result.base64Encoded ? "base64" : "utf8"));
    r.body = file;
  } else if (method === "Network.loadingFailed") {
    (raw.requests[params.requestId] ||= {}).failed = params.errorText;
  } else if (method === "Fetch.requestPaused") {
    const b64 = config.fulfill[params.request.url];
    // The type the host serves it as: a WASM by `application/wasm`, which instantiateStreaming requires.
    const type = /\.wasm(?:$|[?#])/.test(params.request.url) ? "application/wasm" : "text/javascript";
    if (b64 !== undefined) await send("Fetch.fulfillRequest", { requestId: params.requestId, responseCode: 200, responseHeaders: [{ name: "Content-Type", value: type }, { name: "Access-Control-Allow-Origin", value: "*" }], body: b64 }, sessionId);
    else await send("Fetch.continueRequest", { requestId: params.requestId }, sessionId);
  }
});

await call("Target.setDiscoverTargets", { discover: true });
await call("Target.setAutoAttach", autoAttach);
const { targetId } = await call("Target.createTarget", { url: "about:blank" });
for (let i = 0; i < 100 && !pageSession; i++) await sleep(50);
if (!pageSession) throw new Error("the page target was not attached");

if (config.baseline) {  // a pristine profile: Chrome on about:blank, closed through the protocol
  await sleep(2000);
  await send("Browser.close").catch(() => {});
  await new Promise((r) => { chrome.on("exit", r); setTimeout(r, 10000); });
  writeFileSync(path.join(config.out, "raw.json"), JSON.stringify({ baseline: true }));
  process.exit(0);
}

const evaluate = async (expression) => {
  const r = await call("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }, pageSession);
  if (r.exceptionDetails) throw new Error(`evaluate: ${r.exceptionDetails.text} ${r.exceptionDetails.exception?.description || ""}`);
  return r.result.value;
};
const waitFor = async (selector, ms = 60000) => {
  const until = wall() + ms;
  while (wall() < until) {
    try { if (await evaluate(`!!document.querySelector(${JSON.stringify(selector)})`)) return true; } catch { /* navigating */ }
    await sleep(50);
  }
  return false;
};
const step = (name) => { trace("step", name); raw.steps = [...(raw.steps || []), name]; };
const mark = async (name) => raw.marks.push({ mark: name, t: await evaluate("performance.timeOrigin + performance.now()") });
const submit = (password) => evaluate(`(() => {
  const input = document.querySelector('[data-bice=password]');
  input.value = ${JSON.stringify(password)};
  input.dispatchEvent(new Event('input', { bubbles: true }));
  document.querySelector('[data-bice=submit]').click();
  return true;
})()`);
const choose = (selector, value) => evaluate(`(() => {
  const s = document.querySelector(${JSON.stringify(selector)});
  s.value = ${JSON.stringify(value)};
  s.dispatchEvent(new Event('change', { bubbles: true }));
  return true;
})()`);
const options = (selector) => evaluate(`[...document.querySelectorAll(${JSON.stringify(selector + " option")})].map(o => o.value)`);

try {
  step("navigate");
  const origin = new URL(config.url).origin;
  for (const m of ["Storage.trackCacheStorageForOrigin", "Storage.trackIndexedDBForOrigin"]) {
    const r = await send(m, { origin }, pageSession);
    if (r.error) raw.unobserved.push({ what: m, why: r.error.message });
  }
  await call("Page.navigate", { url: config.url }, pageSession);
  raw.journey = { loginBox: await waitFor("[data-bice=password]:not([disabled])") };
  raw.end.historyAtStart = await evaluate("history.length");
  await mark("submit");
  step("wrong");
  await submit(config.wrong);
  raw.journey.wrongShown = await waitFor("[data-bice=login-error]:not([hidden])", 30000);
  await mark("submit");
  step("right");
  await submit(config.password);
  raw.journey.summary = await waitFor("[data-bice=summary]", 120000);
  if (raw.journey.summary) {
    const filters = await options("[data-bice=filter]");
    const months = await options("[data-bice=month]");
    const picked = [4, 6, months.length - 1].filter((i) => i >= 0 && i < months.length).map((i) => months[i]);
    for (const f of filters) { await choose("[data-bice=filter]", f); await sleep(200); for (const m of picked) { await choose("[data-bice=month]", m); await sleep(200); } }
    raw.journey.filters = filters.length;
    raw.journey.months = picked.length;
  }
  step("filters done");
  raw.end.historyBeforeLogout = await evaluate("history.length");
  raw.end.titleBeforeLogout = await evaluate("document.title");
  await mark("logout");
  await evaluate("document.querySelector('[data-bice=logout]').click(), true");
  await sleep(500);
  step("logout");
  raw.journey.newLogin = await waitFor("[data-bice=password]:not([disabled])", 30000);
  raw.journey.summaryAfterLogout = await evaluate("!!document.querySelector('[data-bice=summary]')");
  await sleep(1000);
  raw.end.targets = (await call("Target.getTargets")).targetInfos.map((t) => ({ id: t.targetId, type: t.type, url: t.url }));
  raw.end.historyAfterLogout = await evaluate("history.length");
  step("enumerate");
  await mark("enumerate");
  raw.end.readable = await evaluate(readFileSync(path.join(here, "enumerate.js"), "utf8"));
  raw.end.cookies = (await call("Storage.getCookies", {})).cookies.map((c) => ({ name: c.name, value: c.value, domain: c.domain, httpOnly: c.httpOnly }));
  step("back");
  await send("Runtime.evaluate", { expression: "history.back(), true" }, pageSession, 5000);
  await sleep(1500);
  raw.end.afterBack = await evaluate("({ href: location.href, summary: !!document.querySelector('[data-bice=summary]') })").catch((e) => ({ error: String(e) }));
} catch (e) {
  raw.errors.push(String(e && e.stack || e));
}
await sleep(500);
raw.closedAt = wall();
await send("Browser.close").catch(() => {});
await new Promise((r) => { chrome.on("exit", r); setTimeout(r, 5000); });
writeFileSync(path.join(config.out, "raw.json"), JSON.stringify(raw, null, 1));
process.exit(0);
