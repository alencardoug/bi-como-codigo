// Screenshots of one page of stage 2.3 in headless Chrome, through the DevTools protocol:
// the login box, the whole page after login, and the chart under each filter, named by
// the filter's label. It reads what the page shows and judges nothing: chart_oracle.py
// says what each chart should show.
//
//   node shots.mjs <url> <out-dir> <prefix> <password>
//
// CHART: the chart's selector (default "[data-bice=chart]"); SETTLE_MS: the wait after a
// filter changes, for the chart's animation (default 2500); BICE_CHROME: Chrome's binary.
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [url, outDir, prefix, password] = process.argv.slice(2);
mkdirSync(outDir, { recursive: true });
const CHART = process.env.CHART || "[data-bice=chart]";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const profile = mkdtempSync(join(tmpdir(), "bice-shots-"));
const chrome = spawn(process.env.BICE_CHROME || "google-chrome", ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`,
  "--no-first-run", "--no-default-browser-check", "--disable-background-networking", "--disable-component-update", "--window-size=1280,900", "--hide-scrollbars", "about:blank"], { stdio: "ignore" });
let port = null;
for (let i = 0; i < 100 && !port; i++) { try { port = readFileSync(join(profile, "DevToolsActivePort"), "utf8").split("\n")[0]; } catch { await sleep(100); } }
let target = null;
for (let i = 0; i < 100 && !target; i++) { try { target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page"); } catch { await sleep(100); } }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const pending = new Map();
ws.addEventListener("message", (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } });
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expression) => (await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true })).result?.result?.value;
const waitFor = async (selector, ms = 120000) => {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { if (await ev(`!!document.querySelector(${JSON.stringify(selector)})`)) return true; await sleep(100); }
  throw new Error(`timeout: ${selector}`);
};
const settled = async () => { if (await ev(`!!document.querySelector('[data-bice=loading]')`)) await waitFor("[data-bice=loading][hidden]"); };
const shoot = async (name, selector) => {
  const params = { format: "png", captureBeyondViewport: true };
  if (selector) {
    const r = await ev(`(async () => { const e = document.querySelector(${JSON.stringify(selector)}); e.scrollIntoView({ block: "center" }); await new Promise(r => setTimeout(r, 800)); const b = e.getBoundingClientRect(); return { x: b.x + scrollX, y: b.y + scrollY, width: b.width, height: b.height }; })()`);
    params.clip = { x: Math.max(0, r.x - 8), y: Math.max(0, r.y - 8), width: r.width + 16, height: r.height + 16, scale: 2 };
  } else {
    const h = await ev("document.documentElement.scrollHeight");
    params.clip = { x: 0, y: 0, width: 1280, height: h, scale: 1 };
  }
  const file = join(outDir, `${prefix}_${name}.png`);
  writeFileSync(file, Buffer.from((await send("Page.captureScreenshot", params)).result.data, "base64"));
  console.log(file);
};
const out = { url, filters: [] };
try {
  await send("Runtime.enable"); await send("Page.enable");
  await send("Page.navigate", { url });
  await waitFor("[data-bice=password]:not([disabled])");
  await sleep(1500);
  await shoot("01_login");
  await ev(`(() => { const i = document.querySelector('[data-bice=password]'); i.value = ${JSON.stringify(password)};
    i.dispatchEvent(new Event('input', { bubbles: true })); document.querySelector('[data-bice=submit]').click(); })()`);
  await waitFor("[data-bice=summary] tr td");
  await settled();
  await waitFor(`${CHART} svg, ${CHART} canvas`);
  await sleep(3000);
  await shoot("02_page");
  const filters = await ev(`[...document.querySelectorAll('[data-bice=filter] option')].map(o => [o.value, o.textContent.trim()])`);
  let n = 3;
  for (const [value, label] of filters) {
    await ev(`(() => { const s = document.querySelector('[data-bice=filter]'); s.value = ${JSON.stringify(value)}; s.dispatchEvent(new Event('change')); })()`);
    await sleep(300);
    await settled();
    await sleep(Number(process.env.SETTLE_MS || 2500));
    const slug = label.normalize("NFD").replace(/[^\w]+/g, "_").toLowerCase();
    await shoot(`${String(n++).padStart(2, "0")}_chart_${slug}`, CHART);
    out.filters.push({ value, label });
  }
} catch (error) {
  out.error = String(error?.stack || error);
  console.error(out.error);
} finally {
  writeFileSync(join(outDir, `${prefix}_shots.json`), JSON.stringify(out, null, 1) + "\n");
  ws.close(); chrome.kill(); await sleep(1000);
  rmSync(profile, { recursive: true, force: true });
}
