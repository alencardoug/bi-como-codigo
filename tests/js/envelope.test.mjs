// The JavaScript reader of the envelope against the oracles of
// docs/encryption_envelope.md §6: the primitives' standard vectors, the
// vectors of §6.2 and every case of §6.3 — the same committed files the Python
// suite reads (tests/vectors/envelope_v1/). Run by `node --test tests/js/`.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

import * as env from "../../web/envelope.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const VECTORS = path.join(ROOT, "tests", "vectors", "envelope_v1");
const read = (name) => readFileSync(path.join(VECTORS, name), "utf-8");
const CASES = JSON.parse(read("cases.json")).cases;
const VECTOR = JSON.parse(read("vectors.json"));
const subtle = globalThis.crypto.subtle;

const hex = (s) => Uint8Array.from(s.match(/../g) ?? [], (b) => parseInt(b, 16));
const toHex = (b) => Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");

// §6.1
test("PBKDF2-HMAC-SHA-256 matches RFC 7914 §11", async () => {
  const vectors = [
    ["passwd", "salt", 1, "55ac046e56e3089fec1691c22544b605f94185216dde0465e68b9d57c20dacbc49ca9cccf179b645991664b39d77ef317c71b845b1e30bd509112041d3a19783"],
    ["Password", "NaCl", 80000, "4ddcd8f60b98be21830cee5ef22701f9641a4418d04c0414aeff08876b34ab56a1d425a1225833549adb841b51c9b3176a272bdebba1d078478f62b397f33c8d"],
  ];
  for (const [p, s, c, expected] of vectors) {
    const base = await subtle.importKey("raw", new TextEncoder().encode(p), "PBKDF2", false, ["deriveBits"]);
    const bits = await subtle.deriveBits({ name: "PBKDF2", salt: new TextEncoder().encode(s), iterations: c, hash: "SHA-256" }, base, 512);
    assert.equal(toHex(new Uint8Array(bits)), expected);
  }
});

test("AES-KW matches RFC 3394 §4.6", async () => {
  const kek = await subtle.importKey("raw", Uint8Array.from({ length: 32 }, (_, i) => i), "AES-KW", false, ["wrapKey", "unwrapKey"]);
  const data = await subtle.importKey("raw", hex("00112233445566778899aabbccddeeff000102030405060708090a0b0c0d0e0f"), "AES-GCM", true, ["encrypt"]);
  const wrapped = new Uint8Array(await subtle.wrapKey("raw", data, kek, "AES-KW"));
  assert.equal(toHex(wrapped), "28c9f404c4b810f4cbccb35cfb87f8263f5786e2d80ed326cbc7f0e71a99f43bfb988b9b7a02dd21");
});

test("AES-256-GCM matches test case 16", async () => {
  const key = await subtle.importKey("raw", hex("feffe9928665731c6d6a8f9467308308".repeat(2)), "AES-GCM", false, ["encrypt"]);
  const out = await subtle.encrypt(
    { name: "AES-GCM", iv: hex("cafebabefacedbaddecaf888"), additionalData: hex("feedfacedeadbeeffeedfacedeadbeefabaddad2"), tagLength: 128 },
    key,
    hex("d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a721c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b39"),
  );
  assert.equal(
    toHex(new Uint8Array(out)),
    "522dc1f099567d07f47f37a32a84427d643a8cdcbfe5c0c97598a2bd2555d1aa8cb08e48590dbb3da7b08b1056828838c5f61e6393ba7a0abcc9f662" + "76fc6ece0f4e1768cddf8853bb2d551b",
  );
});

// Logins are cached as the browser caches them: once per profile per manifest.
const keys = new Map();
async function keyFor(manifest, profile, typed) {
  const p = manifest.profiles.get(profile);
  const k = [toHex(manifest.packageId), profile, toHex(p.salt), p.iterations, typed].join("|");
  if (!keys.has(k)) keys.set(k, await env.login(manifest, profile, typed));
  return keys.get(k);
}

async function run(manifestText, envelope, report, profile, typed) {
  try {
    const manifest = env.validateManifest(JSON.parse(manifestText));
    return await env.openReport(manifest, envelope, report, await keyFor(manifest, profile, typed));
  } catch (error) {
    if (error instanceof env.Refused) return error;
    throw error;
  }
}

// §6.2 and §6.3. The case that only CI's strict parser can see is skipped:
// JSON.parse keeps the last of two repeated keys (§4).
for (const c of CASES) {
  test(`case ${c.id}`, { skip: c.ci_only && "CI only: a repeated key is invisible to JSON.parse" }, async () => {
    const out = await run(c.manifest, hex(c.envelope), c.report, c.profile, c.typed);
    if (c.code === null) {
      const expected = VECTOR.reports[c.report];
      assert.ok(!(out instanceof env.Refused), `${c.id} refused: ${out.message}`);
      assert.equal(toHex(out.totals), expected.totals);
      assert.equal(toHex(out.parquet), expected.parquet);
      return;
    }
    assert.ok(out instanceof env.Refused, `${c.id} opened`);
    assert.deepEqual([out.code, out.predicateId], [c.code, c.predicate]);
  });
}

test("case header_ciphertext_range above the bound, built here", async () => {
  const p01 = hex(VECTOR.reports.P01.envelope);
  const headerLen = env.parseHeader(p01).raw.length;
  const n = 32 * 1024 * 1024 + 1;
  const data = new Uint8Array(headerLen + n + 16);
  data.set(p01.subarray(0, headerLen));
  new DataView(data.buffer).setUint32(headerLen - 4, n);
  const manifest = JSON.parse(read("manifest.json"));
  const sha = toHex(new Uint8Array(await subtle.digest("SHA-256", data)));
  manifest.reports = manifest.reports.map((r) => (r.id === "P01" ? { id: "P01", file: `P01.${sha.slice(0, 16)}.bice`, sha256: sha, size: data.length } : r));
  const out = await run(JSON.stringify(manifest), data, "P01", "diretoria", VECTOR.typed_by_profile.diretoria);
  assert.ok(out instanceof env.Refused);
  assert.deepEqual([out.code, out.predicateId], ["header_malformed", "ciphertext_len_range"]);
});

// §6.5: the module's predicates are the specification's table, but the
// package and live ones, which are Python's.
function specPredicates() {
  const text = readFileSync(path.join(ROOT, "docs", "encryption_envelope.md"), "utf-8");
  const table = text.split("### 6.5")[1].split("\n### ")[0];
  const ids = new Set();
  for (const line of table.split("\n")) {
    const cells = line.split("|");
    if (cells.length < 4) continue;
    const step = cells[1].trim();
    if (!step || step === "Step" || step === "---" || step.startsWith("live") || step.startsWith("package")) continue;
    for (const m of cells[2].matchAll(/`([a-z0-9_]+)`/g)) ids.add(m[1]);
  }
  ids.delete("manifest_no_duplicate_keys"); // CI only (§4)
  return ids;
}

test("the module has exactly the predicates of the specification", () => {
  const source = readFileSync(path.join(ROOT, "web", "envelope.mjs"), "utf-8");
  const found = new Set([...source.matchAll(/require\([^\n]*,\s*[A-Z_]+,\s*"([a-z0-9_]+)"\)/g)].map((m) => m[1]));
  assert.deepEqual([...found].sort(), [...specPredicates()].sort());
});

test("the key derived at login cannot be exported", async () => {
  const manifest = env.validateManifest(JSON.parse(read("manifest.json")));
  const key = await env.login(manifest, "logistica", VECTOR.typed_by_profile.logistica);
  assert.equal(key.kek.extractable, false);
  assert.deepEqual(key.kek.usages, ["unwrapKey"]);
});
