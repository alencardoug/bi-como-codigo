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
  const ser = (v) => {
    try {
      if (typeof v === "string") return { text: v };
      if (v instanceof ArrayBuffer) return { b64: b64(new Uint8Array(v)) };
      if (ArrayBuffer.isView(v)) return { b64: b64(new Uint8Array(v.buffer, v.byteOffset, v.byteLength)) };
      return { text: JSON.stringify(v, (k, x) => (typeof x === "bigint" ? x.toString()
        : ArrayBuffer.isView(x) ? { __b64: b64(new Uint8Array(x.buffer, x.byteOffset, x.byteLength)) }
        : x instanceof ArrayBuffer ? { __b64: b64(new Uint8Array(x)) } : x)) };
    } catch { try { return { text: String(v) }; } catch { return { unreadable: true }; } }
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

  // What it stores: the entry points and the values written.
  if (g.Storage) wrap(Storage.prototype, "setItem", function ([k, v]) { send("store", { store: this === g.sessionStorage ? "sessionStorage" : "localStorage", op: "setItem", key: String(k), value: ser(String(v)) }); });
  if (g.IDBFactory) wrap(IDBFactory.prototype, "open", function ([name]) { send("store", { store: "indexedDB", op: "open", key: String(name) }); });
  if (g.IDBObjectStore) {
    for (const op of ["put", "add"]) wrap(IDBObjectStore.prototype, op, function ([value, key]) { send("store", { store: "indexedDB", op, key: String(this.name), value: ser(value) }); });
  }
  if (g.IDBCursor) wrap(IDBCursor.prototype, "update", function ([value]) { send("store", { store: "indexedDB", op: "cursor.update", value: ser(value) }); });
  if (g.CacheStorage) wrap(CacheStorage.prototype, "open", function ([name]) { send("store", { store: "CacheStorage", op: "open", key: String(name) }); });
  if (g.Cache) {
    wrap(Cache.prototype, "put", function ([req, res]) {
      const url = typeof req === "string" ? req : req && req.url;
      try { res.clone().arrayBuffer().then((buf) => send("store", { store: "CacheStorage", op: "put", key: String(url), value: ser(buf) })); } catch { send("store", { store: "CacheStorage", op: "put", key: String(url) }); }
    });
    for (const op of ["add", "addAll"]) wrap(Cache.prototype, op, function ([req]) { send("store", { store: "CacheStorage", op, key: ser(req) }); });
  }
  if (g.StorageManager) wrap(StorageManager.prototype, "getDirectory", function () { send("store", { store: "opfs", op: "getDirectory" }); });
  if (g.FileSystemWritableFileStream) wrap(FileSystemWritableFileStream.prototype, "write", function ([data]) { send("store", { store: "opfs", op: "write", value: ser(data) }); });
  if (g.FileSystemSyncAccessHandle) wrap(FileSystemSyncAccessHandle.prototype, "write", function ([data]) { send("store", { store: "opfs", op: "write", value: ser(data) }); });
  if (g.Document) {
    const d = Object.getOwnPropertyDescriptor(Document.prototype, "cookie");
    if (d && d.set) Object.defineProperty(Document.prototype, "cookie", { ...d, set(v) { send("store", { store: "cookie", op: "set", value: ser(String(v)) }); return d.set.call(this, v); } });
  }
  if (g.ServiceWorkerContainer) wrap(ServiceWorkerContainer.prototype, "register", function ([url]) { send("store", { store: "serviceWorker", op: "register", key: String(url) }); });
  if (g.History) {
    for (const op of ["pushState", "replaceState"]) wrap(History.prototype, op, function ([state, , url]) { send("store", { store: "history", op, key: String(url ?? ""), value: ser(state) }); });
  }
  if (g.Navigation) {
    wrap(Navigation.prototype, "navigate", function ([url, opts]) { send("store", { store: "navigation", op: "navigate", key: String(url), value: ser(opts && opts.state) }); });
    wrap(Navigation.prototype, "updateCurrentEntry", function ([opts]) { send("store", { store: "navigation", op: "updateCurrentEntry", value: ser(opts && opts.state) }); });
  }

  // Workers, for what survives logout.
  if (g.Worker) {
    const W = g.Worker;
    wrap(W.prototype, "terminate", function () { send("worker", { op: "terminate" }); });
    g.Worker = new Proxy(W, { construct(t, args) { send("worker", { op: "create", key: String(args[0]) }); return Reflect.construct(t, args); } });
  }
  send("installed", {});
})();
