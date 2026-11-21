// The browser diagnostic's hooks (docs/framework_prototype.md §2.5.3), injected
// before any page script runs in every realm the DevTools protocol reaches —
// the page, its frames, its workers. It changes nothing the page does: each
// wrapper records the call and forwards it. Records leave through
// `console.debug("__bice__", json)`, which the driver reads from every session.
//
// Recorded: WebCrypto's deriveKey, deriveBits, unwrapKey and decrypt — realm,
// start time, outcome —; the store entry points and the values written to them;
// history and navigation state; worker creation and termination.
(() => {
  const g = globalThis;
  if (g.__biceInstalled) return;
  Object.defineProperty(g, "__biceInstalled", { value: true });
  const now = () => performance.timeOrigin + performance.now();
  const realm = () => { try { return String(g.location && g.location.href); } catch { return "?"; } };
  const debug = console.debug.bind(console);
  const doc = `${now()}-${Math.random()}`;  // one realm's life: call ids restart in each
  const send = (kind, data) => { try { debug("__bice__", JSON.stringify({ kind, t: now(), realm: realm(), doc, ...data })); } catch { /* never break the page */ } };
  const b64 = (bytes) => { let s = ""; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000)); return btoa(s); };
  // Serializes a value the browser has already cloned — history.state, a record
  // read back from IndexedDB — or a primitive: never an object of the page, whose
  // getters it would run (PROTO-1-11). What JSON cannot hold is kept typed, and a
  // body it cannot read now is said so, not dropped (PROTO-1-12).
  const ser = (v) => {
    try {
      if (typeof v === "string") return { text: v };
      if (v instanceof ArrayBuffer) return { b64: b64(new Uint8Array(v)) };
      if (ArrayBuffer.isView(v)) return { b64: b64(new Uint8Array(v.buffer, v.byteOffset, v.byteLength)) };
      const missing = [];
      const text = JSON.stringify(v, (k, x) => {
        if (typeof x === "bigint") return x.toString();
        if (ArrayBuffer.isView(x)) return { __b64: b64(new Uint8Array(x.buffer, x.byteOffset, x.byteLength)) };
        if (x instanceof ArrayBuffer) return { __b64: b64(new Uint8Array(x)) };
        if (x instanceof Map) return { __map: [...x.entries()] };
        if (x instanceof Set) return { __set: [...x.values()] };
        if (typeof Blob !== "undefined" && x instanceof Blob) { missing.push(`a Blob of ${x.size} bytes`); return { __blob: x.size }; }
        return x;
      });
      return missing.length ? { text, unreadable: missing.join("; ") } : { text };
    } catch (e) { return { unreadable: `not serializable: ${e && e.name}` }; }
  };
  const after = (proto, name, then) => {
    if (!proto || typeof proto[name] !== "function") return;
    const orig = proto[name];
    proto[name] = function (...args) { const r = orig.apply(this, args); try { then.call(this, args, r); } catch { /* recording only */ } return r; };
  };
  const wrap = (proto, name, before) => {
    if (!proto || typeof proto[name] !== "function") return;
    const orig = proto[name];
    proto[name] = function (...args) { try { before.call(this, args); } catch { /* recording only */ } return orig.apply(this, args); };
  };

  // When it decrypts (FPROTO-8-05): every call kept with its realm, start time and outcome.
  let calls = 0;
  if (g.SubtleCrypto) {
    for (const method of ["deriveKey", "deriveBits", "unwrapKey", "decrypt"]) {
      const orig = SubtleCrypto.prototype[method];
      SubtleCrypto.prototype[method] = function (...args) {
        const id = ++calls;
        send("crypto", { method, id, phase: "start" });
        const p = orig.apply(this, args);
        p.then(() => send("crypto", { method, id, phase: "ok" }), () => send("crypto", { method, id, phase: "fail" }));
        return p;
      };
    }
  }

  // What it stores: the entry points, and each value read back as the browser
  // stored it — an attempt, not a committed write (PROTO-1-12).
  if (g.Storage) after(Storage.prototype, "setItem", function ([k]) { send("store", { store: this === g.sessionStorage ? "sessionStorage" : "localStorage", op: "setItem", key: String(k), value: ser(this.getItem(k)) }); });
  if (g.IDBFactory) wrap(IDBFactory.prototype, "open", function ([name]) { send("store", { store: "indexedDB", op: "open", key: String(name) }); });
  if (g.IDBObjectStore) {
    // A read-back after a later write to the same store may read that later
    // value: such an attempt is said unreadable, not reported as read (PROTO-2-09).
    const writes = new WeakMap();
    for (const op of ["put", "add"]) {
      after(IDBObjectStore.prototype, op, function (args, req) {
        const store = this;
        const seq = (writes.get(store) || 0) + 1;
        writes.set(store, seq);
        req.addEventListener("success", () => {
          if (writes.get(store) !== seq) { send("store", { store: "indexedDB", op, key: String(store.name), value: { unreadable: "a later write in the same store came before the read-back" } }); return; }
          try { const back = store.get(req.result); back.onsuccess = () => send("store", { store: "indexedDB", op, key: String(store.name), value: ser(back.result) }); }
          catch (e) { send("store", { store: "indexedDB", op, key: String(store.name), value: { unreadable: `not read back: ${e && e.name}` } }); }
        });
      });
    }
  }
  if (g.IDBCursor) {
    after(IDBCursor.prototype, "update", function (args, req) {
      const cursor = this;
      req.addEventListener("success", () => {
        try {
          const store = cursor.source.objectStore || cursor.source;
          const back = store.get(cursor.primaryKey);
          back.onsuccess = () => send("store", { store: "indexedDB", op: "cursor.update", value: ser(back.result) });
        } catch (e) { send("store", { store: "indexedDB", op: "cursor.update", value: { unreadable: `not read back: ${e && e.name}` } }); }
      });
    });
  }
  if (g.CacheStorage) wrap(CacheStorage.prototype, "open", function ([name]) { send("store", { store: "CacheStorage", op: "open", key: String(name) }); });
  if (g.Cache) {
    wrap(Cache.prototype, "put", function ([req, res]) {
      const url = typeof req === "string" ? req : req && req.url;
      try { res.clone().arrayBuffer().then((buf) => send("store", { store: "CacheStorage", op: "put", key: String(url), value: ser(buf) })); } catch { send("store", { store: "CacheStorage", op: "put", key: String(url), value: { unreadable: "a body not cloned" } }); }
    });
    for (const op of ["add", "addAll"]) wrap(Cache.prototype, op, function ([req]) { send("store", { store: "CacheStorage", op, key: typeof req === "string" ? req : String(req && req.url || "requests") }); });
  }
  if (g.StorageManager) wrap(StorageManager.prototype, "getDirectory", function () { send("store", { store: "opfs", op: "getDirectory" }); });
  const opfsWrite = function ([data]) {
    if (typeof data === "string" || data instanceof ArrayBuffer || ArrayBuffer.isView(data)) send("store", { store: "opfs", op: "write", value: ser(data) });
    else if (typeof Blob !== "undefined" && data instanceof Blob) data.arrayBuffer().then((buf) => send("store", { store: "opfs", op: "write", value: ser(buf) }));
    else send("store", { store: "opfs", op: "write", value: { unreadable: "a write whose data is an object of the page" } });
  };
  if (g.FileSystemWritableFileStream) wrap(FileSystemWritableFileStream.prototype, "write", opfsWrite);
  if (g.FileSystemSyncAccessHandle) wrap(FileSystemSyncAccessHandle.prototype, "write", opfsWrite);
  if (g.Document) {
    const d = Object.getOwnPropertyDescriptor(Document.prototype, "cookie");
    if (d && d.set) Object.defineProperty(Document.prototype, "cookie", { ...d, set(v) {
      send("store", { store: "cookie", op: "set", value: typeof v === "string" ? ser(v) : { unreadable: "a cookie that is not a string" } });
      return d.set.call(this, v);
    } });
  }
  if (g.ServiceWorkerContainer) wrap(ServiceWorkerContainer.prototype, "register", function ([url]) { send("store", { store: "serviceWorker", op: "register", key: String(url) }); });
  if (g.History) {
    for (const op of ["pushState", "replaceState"]) after(History.prototype, op, function ([, , url]) { send("store", { store: "history", op, key: String(url ?? ""), value: ser(this.state) }); });
  }
  if (g.Navigation) {
    after(Navigation.prototype, "navigate", function () { send("store", { store: "navigation", op: "navigate", value: ser(this.currentEntry && this.currentEntry.getState()) }); });
    after(Navigation.prototype, "updateCurrentEntry", function () { send("store", { store: "navigation", op: "updateCurrentEntry", value: ser(this.currentEntry && this.currentEntry.getState()) }); });
  }

  // The journey's boundaries, at the events themselves (PROTO-1-11): a submission
  // and the logout click, captured before the page's own handlers.
  if (g.document && g.addEventListener) {
    g.addEventListener("submit", () => send("mark", { mark: "submit" }), true);
    g.addEventListener("click", (ev) => { try { if (ev.target && ev.target.closest && ev.target.closest("[data-bice=logout]")) send("mark", { mark: "logout" }); } catch { /* recording only */ } }, true);
  }

  // Workers, for what survives logout.
  if (g.Worker) {
    const W = g.Worker;
    wrap(W.prototype, "terminate", function () { send("worker", { op: "terminate" }); });
    g.Worker = new Proxy(W, { construct(t, args) { send("worker", { op: "create", key: String(args[0]) }); return Reflect.construct(t, args); } });
  }
  send("installed", {});
})();
