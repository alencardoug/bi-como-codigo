// What the browser can still read at the end, on the new login page (§2.5.3,
// "readable by the browser at the end"): Web Storage, IndexedDB, CacheStorage,
// the origin private file system, service worker registrations and cookies
// visible to the page. Bytes come back as base64.
(async () => {
  const b64 = (bytes) => { let s = ""; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000)); return btoa(s); };
  const out = { localStorage: {}, sessionStorage: {}, indexedDB: {}, caches: {}, opfs: {}, serviceWorkers: [], cookie: document.cookie, unobserved: [] };
  // Maps and Sets kept, a Blob read, anything else JSON cannot hold said so (PROTO-2-09).
  const blobs = [];
  const ser = (v, where) => {
    try {
      return JSON.stringify(v, (k, x) => {
        if (typeof x === "bigint") return x.toString();
        if (ArrayBuffer.isView(x)) return { __b64: b64(new Uint8Array(x.buffer, x.byteOffset, x.byteLength)) };
        if (x instanceof ArrayBuffer) return { __b64: b64(new Uint8Array(x)) };
        if (x instanceof Map) return { __map: [...x.entries()] };
        if (x instanceof Set) return { __set: [...x.values()] };
        // Each Blob under its own name: two in one record are two bodies (PROTO-3-11).
        if (x instanceof Blob) { const n = blobs.length; blobs.push([`${where}@blob${n}`, x]); return { __blob: x.size, __n: n }; }
        return x;
      });
    } catch (e) { out.unobserved.push(`${where}: not serializable (${e && e.name})`); return ""; }
  };
  for (const area of ["localStorage", "sessionStorage"]) for (let i = 0; i < window[area].length; i++) { const k = window[area].key(i); out[area][k] = window[area].getItem(k); }
  try {
    for (const { name } of await indexedDB.databases()) {
      const db = await new Promise((res, rej) => { const r = indexedDB.open(name); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
      out.indexedDB[name] = {};
      for (const store of db.objectStoreNames) {
        const values = await new Promise((res, rej) => { const r = db.transaction(store).objectStore(store).getAll(); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
        out.indexedDB[name][store] = values.map((v, n) => ser(v, `indexedDB:${name}/${store}#${n}`));
      }
      db.close();
    }
  } catch (e) { out.unobserved.push("indexedDB: " + e); }
  try {
    for (const name of await caches.keys()) {
      const cache = await caches.open(name);
      out.caches[name] = {};
      for (const req of await cache.keys()) out.caches[name][req.url] = b64(new Uint8Array(await (await cache.match(req)).arrayBuffer()));
    }
  } catch (e) { out.unobserved.push("caches: " + e); }
  try {
    const walk = async (dir, prefix) => { for await (const [name, h] of dir.entries()) { if (h.kind === "file") out.opfs[prefix + name] = b64(new Uint8Array(await (await h.getFile()).arrayBuffer())); else await walk(h, prefix + name + "/"); } };
    await walk(await navigator.storage.getDirectory(), "");
  } catch (e) { out.unobserved.push("opfs: " + e); }
  try { out.serviceWorkers = (await navigator.serviceWorker.getRegistrations()).map((r) => r.scope); } catch (e) { out.unobserved.push("serviceWorker: " + e); }
  out.blobs = {};
  for (const [where, blob] of blobs) {
    try { out.blobs[where] = b64(new Uint8Array(await blob.arrayBuffer())); } catch (e) { out.unobserved.push(`${where}: a Blob not read (${e && e.name})`); }
  }
  return out;
})()
