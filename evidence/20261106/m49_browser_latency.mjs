// M49: PBKDF2-HMAC-SHA-256 latency in Chrome on the desktop (N67).
//
// Starts Chrome headless with a throwaway profile, opens a blank page from a
// local file (a secure context, so WebCrypto is there), and through the
// DevTools protocol runs the same derivation the reader's login runs —
// deriveKey to an AES-KW key, non-extractable — five times at each count.
// Writes only the throwaway profile, under the system's temporary directory,
// and removes it. Run: node evidence/20261106/m49_browser_latency.mjs
//
// The Chrome binary comes from CHROME, or `google-chrome` on the PATH.

import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir, cpus } from "node:os";
import path from "node:path";

const chrome = process.env.CHROME || "google-chrome";
const dir = mkdtempSync(path.join(tmpdir(), "m49-"));
const page = path.join(dir, "blank.html");
writeFileSync(page, "<!doctype html><title>m49</title>");
const proc = spawn(chrome, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  `--user-data-dir=${path.join(dir, "profile")}`, "--remote-debugging-port=0", `file://${page}`,
], { stdio: ["ignore", "ignore", "pipe"] });

const wsUrl = await new Promise((resolve, reject) => {
  let err = "";
  proc.stderr.on("data", (d) => {
    err += d;
    const m = err.match(/DevTools listening on (ws:\/\/\S+)/);
    if (m) resolve(m[1]);
  });
  proc.on("exit", (code) => reject(new Error(`chrome exited ${code}: ${err}`)));
});

const port = new URL(wsUrl).port;
const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const target = targets.find((t) => t.type === "page");
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let id = 0;
const pending = new Map();
ws.addEventListener("message", (ev) => {
  const msg = JSON.parse(ev.data);
  if (pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  }
});
const send = (method, params) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });

const expression = `(async () => {
  const subtle = crypto.subtle;
  const base = await subtle.importKey("raw", new TextEncoder().encode("not-a-real-password"), "PBKDF2", false, ["deriveKey"]);
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const out = [];
  for (const it of [100000, 600000, 1000000, 2000000]) {
    const ms = [];
    for (let i = 0; i < 5; i++) {
      const t0 = performance.now();
      await subtle.deriveKey({ name: "PBKDF2", salt, iterations: it, hash: "SHA-256" }, base, { name: "AES-KW", length: 256 }, false, ["unwrapKey"]);
      ms.push(performance.now() - t0);
    }
    ms.sort((a, b) => a - b);
    out.push(\`iterations=\${it} min=\${ms[0].toFixed(1)}ms median=\${ms[2].toFixed(1)}ms max=\${ms[4].toFixed(1)}ms\`);
  }
  out.push("secure_context=" + isSecureContext + " user_agent=" + navigator.userAgent);
  return out.join("\\n");
})()`;

const res = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
console.log(new Date().toISOString().replace(/\.\d+Z$/, "Z"));
console.log(res.result?.result?.value ?? JSON.stringify(res));
console.log(`cpu=${cpus()[0].model}`);
ws.close();
proc.kill();
await new Promise((r) => proc.on("exit", r));
rmSync(dir, { recursive: true, force: true });
