// M48's JavaScript worker: the dedicated cases of one predicate against a
// mutant copy of web/envelope.mjs. Called by m48_counter_proof.py as
// `node m48_worker.mjs <mutant module> <predicate>`; prints a JSON list of
// {case, killed, end}.

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const [mutant, pid] = process.argv.slice(2);
const env = await import(pathToFileURL(mutant).href);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const VECTORS = path.join(ROOT, "tests", "vectors", "envelope_v1");
const read = (name) => readFileSync(path.join(VECTORS, name), "utf-8");
const hex = (s) => Uint8Array.from(s.match(/../g) ?? [], (b) => parseInt(b, 16));
const toHex = (b) => Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
const subtle = globalThis.crypto.subtle;

async function endOf(manifestText, envelope, report, profile, typed) {
  try {
    const manifest = env.parseManifest(manifestText);
    const key = await env.login(manifest, profile, typed);
    await env.openReport(manifest, envelope, report, key);
    return "opened";
  } catch (error) {
    if (error instanceof env.Refused) return `${error.code}/${error.predicateId}`;
    return `error ${error?.name ?? typeof error}`;
  }
}

const results = [];
for (const c of JSON.parse(read("cases.json")).cases) {
  if (c.predicate !== pid || c.ci_only) continue;
  const end = await endOf(c.manifest, hex(c.envelope), c.report, c.profile, c.typed);
  results.push({ case: c.id, killed: end !== `${c.code}/${pid}`, end });
}

if (pid === "ciphertext_len_range") {
  const vector = JSON.parse(read("vectors.json"));
  const p01 = hex(vector.reports.P01.envelope);
  const headerLen = 122;
  const n = 32 * 1024 * 1024 + 1;
  const data = new Uint8Array(headerLen + n + 16);
  data.set(p01.subarray(0, headerLen));
  new DataView(data.buffer).setUint32(headerLen - 4, n);
  const manifest = JSON.parse(read("manifest.json"));
  const sha = toHex(new Uint8Array(await subtle.digest("SHA-256", data)));
  manifest.reports = manifest.reports.map((r) => (r.id === "P01" ? { id: "P01", file: `P01.${sha.slice(0, 16)}.bice`, sha256: sha, size: data.length } : r));
  const end = await endOf(JSON.stringify(manifest), data, "P01", "diretoria", vector.typed_by_profile.diretoria);
  results.push({ case: "header_ciphertext_range__above", killed: end !== "header_malformed/ciphertext_len_range", end });
}

process.stdout.write(JSON.stringify(results));
