// Probe A7 (docs/framework_prototype.md §3): a Vite plugin that answers the four
// imports by which Evidence's browser client (@evidence-dev/universal-sql,
// client-duckdb/browser.js) brings DuckDB-WASM's worker and WASM into the build
// with modules of a line each — the WASM's jsDelivr URL, and a Worker started
// from a blob that imports the worker's jsDelivr URL —, both pinned by cdn.json.
// Nothing of the engine's worker or WASM is then written into the build.
import { readFileSync } from "node:fs";

const cdn = JSON.parse(readFileSync(new URL("./cdn.json", import.meta.url), "utf8"));
const PREFIX = "\0bice-pinned-engine:";

function body(file) {
  if (!file.sha256 || !file.url.startsWith("https://cdn.jsdelivr.net/npm/")) throw new Error(`cdn.json: ${file.name} is not pinned`);
  if (file.role === "wasm") return `export default ${JSON.stringify(file.url)};\n`;
  const script = `importScripts(${JSON.stringify(file.url)});`;
  return `export default class PinnedWorker {\n  constructor() {\n    return new Worker(URL.createObjectURL(new Blob([${JSON.stringify(script)}], { type: "text/javascript" })));\n  }\n}\n`;
}

const modules = Object.fromEntries(cdn.files.map((f) => [f.import, body(f)]));

export default function pinnedEngine() {
  return {
    name: "bice-pinned-engine",
    enforce: "pre",
    resolveId(id) {
      return id in modules ? PREFIX + id : null;
    },
    load(id) {
      return id.startsWith(PREFIX) ? modules[id.slice(PREFIX.length)] : null;
    },
  };
}
