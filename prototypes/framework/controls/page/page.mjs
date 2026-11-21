// The control page: the unchanged reader opens the package after submit; a
// leak, chosen by ?leak=, does one thing the diagnostic must see.
import * as env from "./envelope.mjs";

const leak = new URLSearchParams(location.search).get("leak") || "none";
const $ = (s) => document.querySelector(s);
const subtle = crypto.subtle;
let worker = null;
let opened = null;

async function openPackage(password) {
  const manifest = env.parseManifest(await (await fetch("package/manifest.json")).text());
  const entry = manifest.reports.get("P01");
  const envelope = new Uint8Array(await (await fetch(`package/${entry.file}`)).arrayBuffer());
  const key = await env.login(manifest, "diretoria", password);
  return env.openReport(manifest, envelope, "P01", key);
}

const b64 = (bytes) => { let s = ""; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000)); return btoa(s); };

if (leak === "startup") await openPackage("senha_complexa_123");  // the public password, before any submission: the whole decryption

async function decryptAnything() {
  const key = await subtle.generateKey({ name: "AES-GCM", length: 128 }, false, ["encrypt", "decrypt"]);
  const iv = new Uint8Array(12);
  await subtle.decrypt({ name: "AES-GCM", iv }, key, await subtle.encrypt({ name: "AES-GCM", iv }, key, new Uint8Array(4)));
}

$("[data-bice=login]").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  $("[data-bice=login-error]").hidden = true;
  const manifest = env.parseManifest(await (await fetch("package/manifest.json")).text());
  const entry = manifest.reports.get("P01");
  const envelope = new Uint8Array(await (await fetch(`package/${entry.file}`)).arrayBuffer());
  try {
    const key = await env.login(manifest, "diretoria", $("[data-bice=password]").value);
    opened = await env.openReport(manifest, envelope, "P01", key);
  } catch {
    if (leak === "wrong") await decryptAnything();
    $("[data-bice=login-error]").hidden = false;
    return;
  }
  const totals = JSON.parse(new TextDecoder().decode(opened.totals));
  worker = new Worker(URL.createObjectURL(new Blob(["onmessage = (e) => postMessage(e.data);"], { type: "text/javascript" })));
  if (leak === "local") {  // a retained marker the profile scan must read on disk, and a retained cookie
    localStorage.setItem("p01", totals.sums.net_revenue_amount);
    document.cookie = `p01=${totals.rows}; max-age=3600; path=/`;
  }
  if (leak === "history") history.replaceState({ selection: "todos", rows: totals.rows }, "");
  if (leak === "label") localStorage.setItem("p01", b64(opened.parquet));  // the report's labels, inside its Parquet
  if (leak === "transient") { localStorage.p01 = totals.sums.net_revenue_amount; delete localStorage.p01; }  // no setItem to hook
  if (leak === "cache") await (await caches.open("bice-control")).put("/q", new Response(totals.sums.net_revenue_amount));
  if (leak === "getter") {  // a state whose getter counts its reads: the hooks must not add one
    let reads = 0;
    history.replaceState({ get v() { reads += 1; return reads; } }, "");
    document.title = `reads=${reads}`;
  }
  if (leak === "idb") {
    const db = await new Promise((res) => { const r = indexedDB.open("bice-control"); r.onupgradeneeded = () => r.result.createObjectStore("q"); r.onsuccess = () => res(r.result); });
    await new Promise((res) => { const t = db.transaction("q", "readwrite"); t.objectStore("q").put({ rows: totals.rows, net: totals.sums.net_revenue_amount }, "r"); t.oncomplete = res; });
    db.close();
  }
  $("[data-bice=login]").hidden = true;
  const summary = document.createElement("table");  // present only once the report is open
  summary.dataset.bice = "summary";
  summary.innerHTML = "<tr><td>aberto</td></tr>";
  $("[data-bice=report]").prepend(summary);
  $("[data-bice=report]").hidden = false;
});

$("[data-bice=logout]").addEventListener("click", async () => {
  if (leak === "logoutcrypto") await subtle.digest("SHA-256", new Uint8Array(1)).then(() => decryptAnything());  // in the old document, after the click
  if (leak === "idb") {
    const db = await new Promise((res) => { const r = indexedDB.open("bice-control"); r.onsuccess = () => res(r.result); });
    await new Promise((res) => { const t = db.transaction("q", "readwrite"); t.objectStore("q").clear(); t.oncomplete = res; });
    db.close();
  }
  if (leak === "worker") {  // the session's worker kept, the page kept: what the diagnostic must report
    $("[data-bice=report]").remove();
    $("[data-bice=login]").hidden = false;
    return;
  }
  worker.terminate();
  location.replace(location.pathname + location.search);
});

$("[data-bice=password]").disabled = false;  // the page contract: enabled once the page can take a submission
