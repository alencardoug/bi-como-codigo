// The reader of the encryption envelope, format version 1, for the browser.
//
// The specification is docs/encryption_envelope.md; section numbers (§n) are
// its own. This file is written from that document, separately from the
// Python of src/bi_como_codigo/envelope.py, and uses nothing but WebCrypto
// (globalThis.crypto.subtle): the same file runs in Node, for the tests, and
// in the site.
//
// Every condition that refuses is one require(condition, code, predicateId)
// call on a line of its own, with no side effect in the condition: the
// counter-proof of §6.5 copies this file and takes one predicate as true.

const subtle = globalThis.crypto.subtle;

// §2.1
const MAGIC = [0x42, 0x49, 0x43, 0x45];
const FORMAT_VERSION = 1;
const ALGORITHM_BYTES = [1, 1, 1, 1, 1];
const LENGTH_BYTES = [32, 16, 12, 16, 40];
const SALT_LEN = 16;
const IV_LEN = 12;
const TAG_LEN = 16;
const WRAPPED_LEN = 40;
const PACKAGE_ID_LEN = 16;
const REPORT_ID_MAX = 16;
const PROFILE_ID_MAX = 32;
const SLOT_COUNT_MAX = 8;
export const ITERATIONS_MIN = 600000;
export const ITERATIONS_MAX = 2000000;
const CIPHERTEXT_MAX = 32 * 1024 * 1024;
// §2.4
const PAYLOAD_MAGIC = [0x42, 0x49, 0x43, 0x50];
const PAYLOAD_VERSION = 1;
const TOTALS_MIN = 2;
const TOTALS_MAX = 65536;
const PARQUET_MIN = 12;
const PARQUET_MAGIC = [0x50, 0x41, 0x52, 0x31];

// §5.1
export const MANIFEST_INVALID = "manifest_invalid";
export const INTEGRITY_MISMATCH = "integrity_mismatch";
export const HEADER_MALFORMED = "header_malformed";
export const IDENTITY_MISMATCH = "identity_mismatch";
export const SLOTS_MISMATCH = "slots_mismatch";
export const NOT_ENTITLED = "not_entitled";
export const UNWRAP_FAILED = "unwrap_failed";
export const DECRYPT_FAILED = "decrypt_failed";
export const PAYLOAD_MALFORMED = "payload_malformed";

export class Refused extends Error {
  constructor(code, predicateId) {
    super(predicateId ? `${code} (${predicateId})` : code);
    this.name = "Refused";
    this.code = code;
    this.predicateId = predicateId;
  }
}

function require(condition, code, predicateId) {
  if (!condition) throw new Refused(code, predicateId);
}

// §3: identities byte by byte, with no regular expression.
const isUpper = (b) => b >= 0x41 && b <= 0x5a;
const isLower = (b) => b >= 0x61 && b <= 0x7a;
const isDigit = (b) => b >= 0x30 && b <= 0x39;

function identityBytesOk(bytes, lead) {
  if (bytes.length === 0 || !lead(bytes[0])) return false;
  for (let i = 1; i < bytes.length; i++) {
    const b = bytes[i];
    if (!(lead(b) || isDigit(b) || b === 0x5f)) return false;
  }
  return true;
}

// The bytes of an identity given as text, or null when a character is not
// ASCII — such an identity can match no range anyway.
function asciiBytes(text) {
  const out = new Uint8Array(text.length);
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i);
    if (c > 0x7f) return null;
    out[i] = c;
  }
  return out;
}

function compareBytes(a, b) {
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) if (a[i] !== b[i]) return a[i] - b[i];
  return a.length - b.length;
}

function equalBytes(a, b) {
  return a.length === b.length && compareBytes(a, b) === 0;
}

function hexOk(value, length) {
  if (typeof value !== "string" || value.length !== length) return false;
  for (let i = 0; i < value.length; i++) {
    const c = value.charCodeAt(i);
    if (!((c >= 0x30 && c <= 0x39) || (c >= 0x61 && c <= 0x66))) return false;
  }
  return true;
}

function fromHex(value) {
  const out = new Uint8Array(value.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(value.substr(2 * i, 2), 16);
  return out;
}

function toHex(bytes) {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

// An integer of the manifest (§4): an integral value within ±(2^53 - 1).
// JSON.parse has already turned 1.0 and 1e0 into 1, so spelling cannot and
// need not be told apart; the Python reader judges by value as well.
const isInt = (v) => typeof v === "number" && Number.isSafeInteger(v);
const isObject = (v) => typeof v === "object" && v !== null && !Array.isArray(v);
const sameKeys = (obj, keys) => {
  const own = Object.keys(obj);
  return own.length === keys.length && keys.every((k) => Object.prototype.hasOwnProperty.call(obj, k));
};
const sortedBy = (list) => list.every((v, i) => i === 0 || compareBytes(asciiBytes(list[i - 1]), asciiBytes(v)) <= 0);
const unique = (list) => new Set(list).size === list.length;

function idsOk(ids, lead, maximum) {
  const raws = ids.map(asciiBytes);
  const lengths = ids.every((id, i) => id.length >= 1 && (raws[i] === null || raws[i].length <= maximum));
  const content = raws.every((r) => r !== null && identityBytesOk(r, lead));
  return [lengths, content];
}

// Step 0 from the text of the manifest: what does not parse as JSON — NaN,
// Infinity, a truncated file — is refused like a wrong type.
export function parseManifest(text) {
  let data;
  let parsed = true;
  try {
    data = JSON.parse(text);
  } catch {
    parsed = false;
  }
  require(parsed, MANIFEST_INVALID, "manifest_types");
  return validateManifest(data);
}

// Step 0, the browser's: the structure of §4. A key repeated in the JSON text
// is invisible here — JSON.parse keeps the last — and is CI's to refuse.
export function validateManifest(data) {
  require(isObject(data), MANIFEST_INVALID, "manifest_types");
  require(sameKeys(data, ["manifest_version", "envelope_format_version", "package_id", "profiles", "reports"]), MANIFEST_INVALID, "manifest_keys");
  const { profiles, reports } = data;
  require(Array.isArray(profiles) && Array.isArray(reports), MANIFEST_INVALID, "manifest_types");
  require([...profiles, ...reports].every(isObject), MANIFEST_INVALID, "manifest_types");
  require(profiles.every((p) => sameKeys(p, ["id", "label", "salt", "iterations", "reports"])), MANIFEST_INVALID, "manifest_keys");
  require(reports.every((r) => sameKeys(r, ["id", "file", "sha256", "size"])), MANIFEST_INVALID, "manifest_keys");
  const typesOk =
    isInt(data.manifest_version) &&
    isInt(data.envelope_format_version) &&
    typeof data.package_id === "string" &&
    profiles.every(
      (p) =>
        typeof p.id === "string" &&
        typeof p.label === "string" &&
        typeof p.salt === "string" &&
        isInt(p.iterations) &&
        Array.isArray(p.reports) &&
        p.reports.every((r) => typeof r === "string"),
    ) &&
    reports.every((r) => typeof r.id === "string" && typeof r.file === "string" && typeof r.sha256 === "string" && isInt(r.size) && r.size >= 1);
  require(typesOk, MANIFEST_INVALID, "manifest_types");
  const versionsOk = data.manifest_version === 1 && data.envelope_format_version === FORMAT_VERSION;
  require(versionsOk, MANIFEST_INVALID, "manifest_versions");
  const hexesOk = hexOk(data.package_id, 2 * PACKAGE_ID_LEN) && profiles.every((p) => hexOk(p.salt, 2 * SALT_LEN)) && reports.every((r) => hexOk(r.sha256, 64));
  require(hexesOk, MANIFEST_INVALID, "manifest_hex");
  const profileIds = profiles.map((p) => p.id);
  const reportIds = reports.map((r) => r.id);
  const listed = profiles.flatMap((p) => p.reports);
  const [pLen, pBytes] = idsOk(profileIds, isLower, PROFILE_ID_MAX);
  const [rLen, rBytes] = idsOk([...reportIds, ...listed], isUpper, REPORT_ID_MAX);
  require(pLen && rLen, MANIFEST_INVALID, "manifest_identity_length");
  require(pBytes && rBytes, MANIFEST_INVALID, "manifest_identity_bytes");
  const iterationsOk = profiles.every((p) => p.iterations >= ITERATIONS_MIN && p.iterations <= ITERATIONS_MAX);
  require(iterationsOk, MANIFEST_INVALID, "manifest_iterations_bounds");
  const uniqueOk = unique(profileIds) && unique(reportIds) && profiles.every((p) => unique(p.reports));
  require(uniqueOk, MANIFEST_INVALID, "manifest_unique");
  const sortedOk = sortedBy(profileIds) && sortedBy(reportIds) && profiles.every((p) => sortedBy(p.reports));
  require(sortedOk, MANIFEST_INVALID, "manifest_sorted");
  const known = new Set(reportIds);
  const entitledSome = new Set(listed);
  require(listed.every((r) => known.has(r)), MANIFEST_INVALID, "manifest_membership");
  require(reportIds.every((r) => entitledSome.has(r)), MANIFEST_INVALID, "manifest_entitled");
  const filesOk = reports.every((r) => r.file === `${r.id}.${r.sha256.slice(0, 16)}.bice`);
  require(filesOk, MANIFEST_INVALID, "manifest_file_form");
  return Object.freeze({
    packageId: fromHex(data.package_id),
    profiles: new Map(profiles.map((p) => [p.id, Object.freeze({ id: p.id, label: p.label, salt: fromHex(p.salt), iterations: p.iterations, reports: [...p.reports] })])),
    reports: new Map(reports.map((r) => [r.id, Object.freeze({ ...r })])),
  });
}

function entitled(manifest, reportId) {
  return new Set([...manifest.profiles.values()].filter((p) => p.reports.includes(reportId)).map((p) => p.id));
}

class Cursor {
  constructor(buf) {
    this.buf = buf;
    this.pos = 0;
  }
  take(n) {
    const available = this.buf.length - this.pos >= n;
    require(available, HEADER_MALFORMED, "bytes_available");
    const out = this.buf.subarray(this.pos, this.pos + n);
    this.pos += n;
    return out;
  }
  u8() {
    return this.take(1)[0];
  }
  u32() {
    const b = this.take(4);
    return ((b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3]) >>> 0;
  }
}

// Step 2.
export function parseHeader(envelope) {
  const cur = new Cursor(envelope);
  const magic = cur.take(4);
  require(equalBytes(magic, MAGIC), HEADER_MALFORMED, "magic");
  const version = cur.u8();
  require(version === FORMAT_VERSION, HEADER_MALFORMED, "format_version");
  const algorithms = cur.take(ALGORITHM_BYTES.length);
  require(equalBytes(algorithms, ALGORITHM_BYTES), HEADER_MALFORMED, "algorithm_bytes");
  const lengths = cur.take(LENGTH_BYTES.length);
  require(equalBytes(lengths, LENGTH_BYTES), HEADER_MALFORMED, "length_bytes");
  const packageId = cur.take(PACKAGE_ID_LEN);
  const reportIdLen = cur.u8();
  require(reportIdLen >= 1 && reportIdLen <= REPORT_ID_MAX, HEADER_MALFORMED, "report_id_length");
  const reportId = cur.take(reportIdLen);
  require(identityBytesOk(reportId, isUpper), HEADER_MALFORMED, "report_id_bytes");
  const slotCount = cur.u8();
  require(slotCount >= 1 && slotCount <= SLOT_COUNT_MAX, HEADER_MALFORMED, "slot_count_range");
  const slots = [];
  for (let i = 0; i < slotCount; i++) {
    const profileIdLen = cur.u8();
    require(profileIdLen >= 1 && profileIdLen <= PROFILE_ID_MAX, HEADER_MALFORMED, "profile_id_length");
    const profileId = cur.take(profileIdLen);
    require(identityBytesOk(profileId, isLower), HEADER_MALFORMED, "profile_id_bytes");
    const ascending = slots.length === 0 || compareBytes(slots[slots.length - 1].profileId, profileId) < 0;
    require(ascending, HEADER_MALFORMED, "slots_ascending");
    const salt = cur.take(SALT_LEN);
    const iterations = cur.u32();
    require(iterations >= ITERATIONS_MIN && iterations <= ITERATIONS_MAX, HEADER_MALFORMED, "iterations_bounds");
    const wrappedKey = cur.take(WRAPPED_LEN);
    slots.push({ profileId, salt, iterations, wrappedKey });
  }
  const iv = cur.take(IV_LEN);
  const ciphertextLen = cur.u32();
  require(ciphertextLen >= 1 && ciphertextLen <= CIPHERTEXT_MAX, HEADER_MALFORMED, "ciphertext_len_range");
  const end = cur.pos;
  const rest = envelope.length - end;
  require(rest >= ciphertextLen + TAG_LEN, HEADER_MALFORMED, "ciphertext_available");
  require(rest === ciphertextLen + TAG_LEN, HEADER_MALFORMED, "exact_end");
  return {
    raw: envelope.subarray(0, end),
    packageId,
    reportId,
    slots,
    iv,
    sealed: envelope.subarray(end, end + ciphertextLen + TAG_LEN),
  };
}

function u32At(buf, at) {
  return ((buf[at] << 24) | (buf[at + 1] << 16) | (buf[at + 2] << 8) | buf[at + 3]) >>> 0;
}

// Step 9.
export function parsePayload(plain) {
  const available = plain.length >= 9;
  require(available, PAYLOAD_MALFORMED, "payload_exact");
  require(equalBytes(plain.subarray(0, 4), PAYLOAD_MAGIC), PAYLOAD_MALFORMED, "payload_magic");
  require(plain[4] === PAYLOAD_VERSION, PAYLOAD_MALFORMED, "payload_version");
  const totalsLen = u32At(plain, 5);
  require(totalsLen >= TOTALS_MIN && totalsLen <= TOTALS_MAX, PAYLOAD_MALFORMED, "totals_len_range");
  const totalsEnd = 9 + totalsLen;
  const parquetLenEnd = totalsEnd + 4;
  const room = plain.length >= parquetLenEnd;
  require(room, PAYLOAD_MALFORMED, "payload_exact");
  const totals = plain.subarray(9, totalsEnd);
  const parquetLen = u32At(plain, totalsEnd);
  require(parquetLen >= PARQUET_MIN, PAYLOAD_MALFORMED, "parquet_len_minimum");
  const exact = plain.length === parquetLenEnd + parquetLen;
  require(exact, PAYLOAD_MALFORMED, "payload_exact");
  const parquet = plain.subarray(parquetLenEnd);
  const framed = equalBytes(parquet.subarray(0, 4), PARQUET_MAGIC) && equalBytes(parquet.subarray(parquet.length - 4), PARQUET_MAGIC);
  require(framed, PAYLOAD_MALFORMED, "parquet_magic");
  return { totals, parquet };
}

// Step 6: the login. The KEK never leaves WebCrypto: non-extractable, with
// unwrapKey as its only usage. A profile the manifest does not declare is the
// caller's error, not a refusal.
export async function login(manifest, profileId, password) {
  const profile = manifest.profiles.get(profileId);
  if (!profile) throw new TypeError(`profile ${profileId} is not in the manifest`);
  const base = await subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveKey"]);
  const kek = await subtle.deriveKey(
    { name: "PBKDF2", salt: profile.salt, iterations: profile.iterations, hash: "SHA-256" },
    base,
    { name: "AES-KW", length: 256 },
    false,
    ["unwrapKey"],
  );
  return Object.freeze({ packageId: manifest.packageId, profileId, kek });
}

// Steps 1 to 9; the manifest is validated already. Resolves to the totals and
// the Parquet bytes, or rejects with Refused.
export async function openReport(manifest, envelope, reportId, key) {
  const entry = manifest.reports.get(reportId);
  if (!entry) throw new TypeError(`report ${reportId} is not in the manifest`);
  if (!equalBytes(key.packageId, manifest.packageId)) throw new TypeError("the key was derived for another package: log in again");
  // 1
  require(envelope.length === entry.size, INTEGRITY_MISMATCH, "size_equal");
  const digest = toHex(new Uint8Array(await subtle.digest("SHA-256", envelope)));
  require(digest === entry.sha256, INTEGRITY_MISMATCH, "sha256_equal");
  // 2
  const header = parseHeader(envelope);
  // 3
  require(equalBytes(header.packageId, manifest.packageId), IDENTITY_MISMATCH, "package_id_equal");
  require(equalBytes(header.reportId, asciiBytes(reportId)), IDENTITY_MISMATCH, "report_id_equal");
  // 4
  const slotIds = new Set(header.slots.map((s) => String.fromCharCode(...s.profileId)));
  const expected = entitled(manifest, reportId);
  const setsEqual = slotIds.size === expected.size && [...expected].every((id) => slotIds.has(id));
  require(setsEqual, SLOTS_MISMATCH, "slot_set_equal");
  for (const slot of header.slots) {
    const profile = manifest.profiles.get(String.fromCharCode(...slot.profileId));
    require(equalBytes(slot.salt, profile.salt), SLOTS_MISMATCH, "slot_salt_equal");
    require(slot.iterations === profile.iterations, SLOTS_MISMATCH, "slot_iterations_equal");
  }
  // 5
  const mine = header.slots.filter((s) => String.fromCharCode(...s.profileId) === key.profileId);
  require(mine.length === 1, NOT_ENTITLED, "slot_present");
  // 7
  let dek;
  try {
    dek = await subtle.unwrapKey("raw", mine[0].wrappedKey, key.kek, "AES-KW", { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
  } catch {
    throw new Refused(UNWRAP_FAILED, null);
  }
  // 8
  let plain;
  try {
    plain = new Uint8Array(await subtle.decrypt({ name: "AES-GCM", iv: header.iv, additionalData: header.raw, tagLength: 128 }, dek, header.sealed));
  } catch {
    throw new Refused(DECRYPT_FAILED, null);
  }
  // 9
  return parsePayload(plain);
}
