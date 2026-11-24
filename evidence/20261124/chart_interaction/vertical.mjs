// The vertical of the chart demonstration (README), driven in headless Chrome through the DevTools
// protocol: the popup at a month, near a line, after a click near it, at the partial month, off the
// plot, on a legend label, shift-click on it, and under fixture_canal_c at 2150-09, where
// fixture_raiz_3 has no row (G). Records the popup's text and the series at full opacity after
// each step, and screenshots; it judges nothing.
//
//   node vertical.mjs <url> <out-dir> <password>      BICE_CHROME: Chrome's binary
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
const [url, outDir, password] = process.argv.slice(2);
mkdirSync(outDir, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const profile = mkdtempSync(join(tmpdir(), "bice-int-"));
const chrome = spawn(process.env.BICE_CHROME || "google-chrome", ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "--no-first-run",
  "--no-default-browser-check", "--disable-background-networking", "--window-size=1280,900", "--hide-scrollbars", "about:blank"], { stdio: "ignore" });
let port = null; for (let i = 0; i < 100 && !port; i++) { try { port = readFileSync(join(profile, "DevToolsActivePort"), "utf8").split("\n")[0]; } catch { await sleep(100); } }
let target = null; for (let i = 0; i < 100 && !target; i++) { try { target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page"); } catch { await sleep(100); } }
const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise((r) => ws.addEventListener("open", r));
let id = 0; const pending = new Map(); const logs = [];
ws.addEventListener("message", (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); return; }
  if (d.method === "Log.entryAdded") logs.push("log: " + d.params.entry.text + " " + (d.params.entry.url || "")); if (d.method === "Runtime.exceptionThrown") logs.push("exception: " + (d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text));
  if (d.method === "Runtime.consoleAPICalled" && ["error", "warning", "warn"].includes(d.params.type)) logs.push(d.params.type + ": " + d.params.args.map((a) => a.value ?? a.description).join(" ")); });
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expression) => (await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true })).result?.result?.value;
const waitFor = async (sel, ms = 120000) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { if (await ev(`!!document.querySelector(${JSON.stringify(sel)})`)) return; await sleep(100); } throw new Error("timeout " + sel); };
const mouse = (type, x, y, extra = {}) => send("Input.dispatchMouseEvent", { type, x, y, button: extra.button || "none", clickCount: extra.clickCount || 0, modifiers: extra.modifiers || 0, pointerType: "mouse" });
const move = async (x, y) => { await mouse("mouseMoved", x, y); await sleep(400); };
const click = async (x, y, modifiers = 0) => { await mouse("mouseMoved", x, y); await mouse("mousePressed", x, y, { button: "left", clickCount: 1, modifiers }); await mouse("mouseReleased", x, y, { button: "left", clickCount: 1, modifiers }); await sleep(500); };
const label = (name) => ev(`(() => { const t = [...document.querySelectorAll('[data-bice=chart] .role-legend-label text')].find(e => e.textContent === ${JSON.stringify(name)}); const b = t.getBoundingClientRect(); return { x: b.x + b.width / 2, y: b.y + b.height / 2 }; })()`);
// a point on the visible line of a series, found by its colour in the legend
const linePoint = (name, frac) => ev(`(() => {
  const labels = [...document.querySelectorAll('[data-bice=chart] .role-legend-label text')].map(e => e.textContent);
  const i = labels.indexOf(${JSON.stringify(name)});
  const sym = document.querySelectorAll('[data-bice=chart] .role-legend-symbol path')[i];
  const colour = sym.getAttribute('stroke') || sym.getAttribute('fill');
  const path = [...document.querySelectorAll('[data-bice=chart] .mark-line path')].find(p => p.getAttribute('stroke') === colour && Number(p.getAttribute('opacity') ?? 1) > 0.01);
  const pt = path.getPointAtLength(path.getTotalLength() * ${frac}); const m = path.getScreenCTM();
  return { x: pt.x * m.a + pt.y * m.c + m.e, y: pt.x * m.b + pt.y * m.d + m.f, colour };
})()`);
const opacities = () => ev(`(() => { const labels = [...document.querySelectorAll('[data-bice=chart] .role-legend-label text')].map(e => e.textContent);
  const syms = [...document.querySelectorAll('[data-bice=chart] .role-legend-symbol path')];
  const paths = [...document.querySelectorAll('[data-bice=chart] .mark-line path')].filter(p => Number(p.getAttribute('opacity') ?? 1) > 0.01);
  return Object.fromEntries(labels.map((l, i) => { const c = syms[i].getAttribute('stroke') || syms[i].getAttribute('fill'); const p = paths.find(q => q.getAttribute('stroke') === c);
    return [l, { line: p?.getAttribute('opacity') ?? '1', width: p?.getAttribute('stroke-width'), legend: syms[i].getAttribute('opacity') ?? '1' }]; })); })()`);
const shot = async (name) => { const r = await ev(`(() => { const b = document.querySelector('[data-bice=chart]').getBoundingClientRect(); return { x: b.x + scrollX, y: b.y + scrollY, width: b.width, height: b.height }; })()`);
  writeFileSync(join(outDir, name + ".png"), Buffer.from((await send("Page.captureScreenshot", { format: "png", clip: { x: r.x - 8, y: r.y - 8, width: r.width + 16, height: r.height + 16, scale: 1.5 } })).result.data, "base64")); };

const tickX = (i) => ev(`(() => { const ax = [...document.querySelectorAll('[data-bice=chart] g.role-axis')].find(g => (g.getAttribute('aria-label') || '').startsWith('X-axis'));
  const b = ax.querySelectorAll('.role-axis-tick line, .role-axis-tick path')[${i}].getBoundingClientRect(); return b.x + b.width / 2; })()`);
const plotY = () => ev(`document.querySelector('[data-bice=chart] svg').getBoundingClientRect().y + 120`);
const tipText = () => ev(`(() => { const t = document.querySelector('.chart-tip'); return t && !t.hidden ? t.innerText : null; })()`);
const view = async (name) => { writeFileSync(join(outDir, name + ".png"), Buffer.from((await send("Page.captureScreenshot", { format: "png" })).result.data, "base64")); };
const choose = async (v) => { await ev(`(() => { const s = document.querySelector('[data-bice=filter]'); s.value = ${JSON.stringify("__V__")}; s.dispatchEvent(new Event('change')); })()`.replace("__V__", v)); await sleep(500); await waitFor("[data-bice=loading][hidden]"); await sleep(1500); await ev(`document.querySelector('[data-bice=chart]').scrollIntoView({ block: 'center' })`); await sleep(400); };
const dot = (name) => ev(`(() => { const labels = [...document.querySelectorAll('[data-bice=chart] .role-legend-label text')].map(e => e.textContent);
  const sym = document.querySelectorAll('[data-bice=chart] .role-legend-symbol path')[labels.indexOf(${JSON.stringify("__N__")})];
  const c = sym.getAttribute('stroke') || sym.getAttribute('fill');
  const d = [...document.querySelectorAll('[data-bice=chart] .mark-symbol path')].find(p => p.getAttribute('fill') === c);
  if (!d) return null; const b = d.getBoundingClientRect(); return { x: b.x + b.width / 2, y: b.y + b.height / 2 }; })()`.replace("__N__", name));
const lit = async () => Object.entries(await opacities()).filter(([, x]) => x.line === '1').map(([n]) => n.slice(-1)).join(",");
const out = { steps: {} };
try {
  await send("Runtime.enable"); await send("Log.enable"); await send("Page.enable"); await send("Page.navigate", { url });
  await waitFor("[data-bice=password]:not([disabled])");
  await ev(`(() => { const i = document.querySelector('[data-bice=password]'); i.value = ${JSON.stringify(password)}; i.dispatchEvent(new Event('input', { bubbles: true })); document.querySelector('[data-bice=submit]').click(); })()`);
  await waitFor("[data-bice=chart] svg"); await sleep(2500);
  await ev(`document.querySelector('[data-bice=chart]').scrollIntoView({ block: 'center' })`); await sleep(500);
  const y = await plotY();
  await move(await tickX(20), y); out.steps["1_todos_2152-01"] = { tip: await tipText(), lit: await lit() }; await view("1_todos_2152-01");
  const d = await dot("fixture_raiz_3"); await move(d.x, d.y + 3); await sleep(300);
  out.steps["2_perto_raiz_3"] = { tip: await tipText(), lit: await lit() }; await view("2_perto_raiz_3");
  await click(d.x, d.y + 3); await move(await tickX(40), y); await sleep(300);
  out.steps["3_clicou_perto_raiz_3_depois_longe"] = { tip: await tipText(), lit: await lit() };
  await move(await tickX(60), y); out.steps["4_todos_2155-05_parcial"] = { tip: await tipText(), lit: await lit() }; await view("4_todos_2155-05_parcial");
  await move(5, 5); out.steps["5_fora"] = { tip: await tipText(), lit: await lit() };
  const p = await label("fixture_raiz_1"); await move(p.x, p.y); out.steps["6_rotulo_raiz_1"] = { tip: await tipText(), lit: await lit() };
  await click(p.x, p.y, 8); await move(5, 5); out.steps["7_shift_clique_rotulo_raiz_1"] = { lit: await lit() };
  await choose("fixture_canal_c");
  const y2 = await plotY();
  await move(await tickX(4), y2); out.steps["8_canal_c_2150-09_G"] = { tip: await tipText() }; await view("8_canal_c_2150-09_G");
} catch (e) { out.error = String(e?.stack || e); }
finally { out.logs = logs; writeFileSync(join(outDir, "vertical.json"), JSON.stringify(out, null, 1)); ws.close(); chrome.kill(); await sleep(800); rmSync(profile, { recursive: true, force: true }); }
