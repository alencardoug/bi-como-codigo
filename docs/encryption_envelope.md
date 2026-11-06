# The encryption envelope — format version 1

> **What lives here:** the byte-level format of an encrypted report, frozen for stage 2.2a — the
> envelope header, which is also the authenticated data, the encrypted payload, the fields of the
> manifest the reader takes its expectations from —; the producer's and the reader's algorithms,
> step by step; the bounds outside which the reader refuses; the oracles: the known-answer vectors,
> the complete envelope vector and the negative cases; and where each part is implemented.
>
> **What does not:** why the password becomes the key and what that does and does not guarantee
> ([PLAN §3.2](../PLAN.md#32-the-showcase) and [§3.6](../PLAN.md#36-the-encryption-envelope--a-proposal-to-review-before-stage-23));
> the three gates and the trusted workflow ([PLAN §3.4](../PLAN.md#34-the-architecture)); what goes
> into the control totals and the rest of the manifest, which the exporter defines (stage 2.4);
> profile switching and logout in the browser (stage 2.6); the Owner's decisions (N23 and N64–N67 in
> [PLAN §1.2](../PLAN.md#12-the-decisions)) and the measurements (M47 in
> [PLAN §2](../PLAN.md#2-what-was-measured)); the decision record of the component, which is born
> with it (the per-profile encryption ADR, pending in the [decision record](adr/README.md#3-pending)).

| Field | Information |
|---|---|
| Date | 2026-11-06 — revision 2: round 1 of Codex's design review applied — observable refusal codes and a step 0 for the manifest (ENV-1-04), negative cases that reach their step, a third vector and the counter-proof of each check (ENV-1-01), separate DEK and IV reuse tests (ENV-1-02), identities matched over every byte (ENV-1-03). Revision 1 is `29a73b8` |
| Author | Claude Code, at the Owner's request (stage 2.2a) |
| Status | **Specification for review by Codex, before implementation.** Nothing in it is implemented. Measured so far: PBKDF2 latency in Node only (M47); the browser's is pending (§7) |

**[measured]** has output behind it; **[planned]** is intent. Every number in this document is a
constant of format version 1 unless it says otherwise.

---

## 1. The objects

| Object | What it is | Identity |
|---|---|---|
| **Profile** | A set of reports one password opens. Declared once in the code: `diretoria` opens the 16 reports, `logistica` opens P13 only (PLAN §3.2) | `profile_id`, an ASCII slug; the visitor-facing name (`Diretoria`, `Logística`) is a label in the manifest and never enters a key or the authenticated data |
| **Package** | One run of the exporter: every report of one publication, encrypted together | `package_id`, 16 bytes from a cryptographic generator, minted at the start of the run — not derived from any content or ciphertext, so nothing is defined in terms of itself |
| **Report** | The encrypted payload of one view | `report_id`, the business question code as eng_dados names it (`P01`–`P16`) |
| **Envelope** | One file per report per package: header, ciphertext and tag | Its SHA-256, recorded in the manifest |
| **Manifest** | One public JSON file per package, with no clear figure, from which the reader takes every identity it expects (§4) | Its SHA-256, in its content-hashed name (PLAN §3.4) |

Keys:

| Key | Length | Lifetime | Derivation |
|---|---|---|---|
| KEK, key-encryption key | 256 bits | One per profile per package | PBKDF2-HMAC-SHA-256 over the password bytes, with the profile's salt and iteration count (§2.3) |
| DEK, data key | 256 bits | **One per encryption of one report file**: never reused across files, packages, retries or attempts | 32 bytes from a cryptographic generator |

The salt is **fresh per profile per package**: every package draws a new 16-byte salt for each
profile, shared by every envelope of that profile within the package. The browser therefore runs
PBKDF2 once per login, not once per report, and a new publication changes every KEK. This is the
"declared scope" of salt rotation that PLAN §3.6 asks for.

---

## 2. The envelope file

### 2.1 Layout

All integers are unsigned and big-endian. The file is the header, then the ciphertext, then the
tag, with nothing before, between or after:

```text
envelope := header || ciphertext || tag
```

| Offset | Length | Field | Version 1 |
|---|---|---|---|
| 0 | 4 | `magic` | `42 49 43 45` (`BICE`) |
| 4 | 1 | `format_version` | `01` |
| 5 | 1 | `password_encoding` | `01` — the UTF-8 bytes of the password exactly as typed, with no normalisation, trimming or case folding |
| 6 | 1 | `kdf` | `01` — PBKDF2 ([RFC 8018 §5.2](https://www.rfc-editor.org/rfc/rfc8018#section-5.2)) |
| 7 | 1 | `kdf_prf` | `01` — HMAC-SHA-256 |
| 8 | 1 | `wrap_alg` | `01` — AES Key Wrap ([RFC 3394](https://www.rfc-editor.org/rfc/rfc3394)), with its default initial value `A6A6A6A6A6A6A6A6` |
| 9 | 1 | `cipher` | `01` — AES-GCM ([NIST SP 800-38D](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf)) |
| 10 | 1 | `key_len` | `20` (32): the length in bytes of the KEK and of the DEK |
| 11 | 1 | `salt_len` | `10` (16) |
| 12 | 1 | `iv_len` | `0C` (12) |
| 13 | 1 | `tag_len` | `10` (16) |
| 14 | 1 | `wrapped_key_len` | `28` (40): RFC 3394 output for a 32-byte key |
| 15 | 16 | `package_id` | Random |
| 31 | 1 | `report_id_len` | `r`, 1 to 16 |
| 32 | `r` | `report_id` | ASCII, matching `^[A-Z][A-Z0-9_]{0,15}$` |
| 32 + `r` | 1 | `slot_count` | `n`, 1 to 8 |
| … | | `slot` × `n` | §2.2, in strictly ascending order of `profile_id` bytes |
| … | 12 | `iv` | Random, fresh per encryption |
| … | 4 | `ciphertext_len` | `c`, 1 to 33,554,432 (32 MiB): the bytes of ciphertext, without the tag |

Then `c` bytes of ciphertext and 16 bytes of tag. The file length is exactly the header length plus
`c` plus 16.

### 2.2 A key slot

One per profile entitled to the report — exactly the set the manifest declares (§4), no more and no
less:

| Length | Field | Version 1 |
|---|---|---|
| 1 | `profile_id_len` | `p`, 1 to 32 |
| `p` | `profile_id` | ASCII, matching `^[a-z][a-z0-9_]{0,31}$` |
| 16 | `salt` | The profile's salt in this package |
| 4 | `iterations` | 600,000 to 2,000,000; the producer of version 1 writes 600,000 (N67) |
| 40 | `wrapped_key` | `AES-KW(KEK of this profile, DEK of this envelope)` |

The salt and the iteration count are repeated in every slot of the profile so that an envelope is
self-describing — the complete vector of §6.2 can be opened with nothing but itself, the password
and the expectations — and they are checked against the manifest, so the repetition cannot
diverge silently.

### 2.3 The cryptography

```text
KEK        = PBKDF2-HMAC-SHA-256(the UTF-8 bytes typed, salt, iterations, dkLen 32)
wrapped    = AES-KW-256(KEK, DEK)                                   -- 40 bytes
AAD        = header                                                 -- every byte from offset 0 to the end of ciphertext_len
ciphertext || tag = AES-256-GCM-Encrypt(key = DEK, IV = iv, A = AAD, P = payload), tag of 128 bits
```

**The authenticated data is the header, byte for byte** (N66). There is no second, canonical
serialisation to reproduce: the bytes the reader parsed are the bytes it authenticates, so two
implementations cannot disagree on an encoding (M23). The header carries the envelope version,
every algorithm and length, the package identity, the report identity, the full mapping of
profiles to wrapped keys, the IV and the ciphertext length — all of what PLAN §3.6 asks to bind.
The wrapped keys are inside it as well: nothing circular, since the DEK is drawn and wrapped before
the header is assembled and the payload encrypted.

In WebCrypto terms (what the browser reader calls; `deriveKey` and `unwrapKey` keep both keys
non-extractable):

```text
importKey("raw", UTF-8(password), "PBKDF2", false, ["deriveKey"])
deriveKey({name: "PBKDF2", salt, iterations, hash: "SHA-256"}, base, {name: "AES-KW", length: 256}, false, ["unwrapKey"])
unwrapKey("raw", wrapped, KEK, "AES-KW", {name: "AES-GCM", length: 256}, false, ["decrypt"])
decrypt({name: "AES-GCM", iv, additionalData: header, tagLength: 128}, DEK, ciphertext || tag)
```

### 2.4 The payload

What AES-GCM encrypts. The reader refuses it unless it is consumed exactly:

| Length | Field | Version 1 |
|---|---|---|
| 4 | `payload_magic` | `42 49 43 50` (`BICP`) |
| 1 | `payload_version` | `01` |
| 4 | `totals_len` | `t`, 2 to 65,536 |
| `t` | `totals` | The control totals: one JSON object, UTF-8. Its keys are defined by the exporter (stage 2.4) |
| 4 | `parquet_len` | `q`, 12 or more |
| `q` | `parquet` | One Parquet file: its first and last four bytes are `PAR1` |

The control totals travel encrypted with the report, never in the manifest (PLAN §3.4). They are
**checked by the package gate in CI** (stage 2.2b), whose JSON parser refuses duplicate keys,
non-UTF-8 bytes and any value other than an object at the top. The browser reader slices them out
and does not interpret them — the browser's `JSON.parse` keeps the last of two duplicate keys
silently, so nothing the site shows comes from them.

---

## 3. The bounds

Outside these, the reader refuses before any cryptography: a malformed or hostile file must not
cost a derivation, and no field can make the reader allocate or iterate without limit.

| What | Accepted in version 1 | Why |
|---|---|---|
| `magic`, `format_version` | Exactly `BICE`, `01` | A new format is a new version, read by new code |
| Each algorithm byte and each length byte at offsets 5–14 | Exactly the values of §2.1 | The parameters are fixed in the format, never taken from a library default or from the file (RV2-02) |
| `report_id` | 1 to 16 bytes, `^[A-Z][A-Z0-9_]{0,15}$`, matched over every byte (below) | One encoding per identity: no case or Unicode variants |
| `slot_count` | 1 to 8, strictly ascending `profile_id`, no repetition | One canonical order, so a reordered or duplicated slot is a different, refused header |
| `profile_id` | 1 to 32 bytes, `^[a-z][a-z0-9_]{0,31}$`, matched over every byte (below) | As `report_id` |
| `iterations` | 600,000 to 2,000,000 | The floor is the decided count (N67); the ceiling keeps a tampered manifest from hanging a browser — about a second on the machine of M47, by extrapolation: 1,000,000 took 497 ms, and 2,000,000 was not run |
| `ciphertext_len` | 1 to 32 MiB, and equal to what the file holds | A view of `consumption` is aggregated; 2.4 measures the real sizes [planned] |
| `totals_len`, `parquet_len` | §2.4, and summing exactly to the plaintext | |

**How an identity matches** (ENV-1-03). The patterns above are a notation, not an instruction to
call a regular-expression engine: an identity is valid when **every one of its bytes**, from the
first to the last, is in the stated ranges — the first in the leading range, each of the others in
the following one — and its length is within the bounds. There is no end-of-line allowance, no
trimming, no case folding and no normalisation: `P01` followed by a line feed is four bytes, the
last outside the range, and is refused. Python's `re.match` with `$` accepts that line feed and
JavaScript's `RegExp.test` does not (ENV-1-03's reproduction), so both implementations check the
bytes directly, with no regular expression. The same rule holds wherever an identity appears: in
the profile declaration, in the manifest and in the header.

The password itself has no bound in the format. **The profile declaration** — the one place the
two passwords are written — accepts only printable ASCII, so UTF-8 and ASCII coincide and no
normalisation question arises; the reader still encodes exactly what was typed.

---

## 4. What the reader takes from the manifest

The reader never takes an identity it expects from the envelope it is checking (PLAN §3.6). Its
expectations come from the manifest, validated first. The cryptographic part of the manifest, the
only part this format defines:

```json
{
  "manifest_version": 1,
  "envelope_format_version": 1,
  "package_id": "<32 lowercase hex digits>",
  "profiles": [
    {"id": "diretoria", "label": "Diretoria", "salt": "<32 lowercase hex>", "iterations": 600000,
     "reports": ["P01", "P02", "…", "P16"]},
    {"id": "logistica", "label": "Logística", "salt": "<32 lowercase hex>", "iterations": 600000,
     "reports": ["P13"]}
  ],
  "reports": [
    {"id": "P01", "file": "P01.<first 16 hex of sha256>.bice", "sha256": "<64 lowercase hex>", "size": 12345}
  ]
}
```

- The mapping of profiles to reports lives only in `profiles[].reports`: a report's entitled set is
  derived from it, never stated twice.
- Every report is entitled to at least one profile; every entry of `profiles[].reports` names a
  report of `reports`; ids are unique and match §3 byte for byte; lists are sorted; hex is
  lowercase and of the stated length; `iterations` is within the bounds of §3; `file` is exactly
  `<id>.<first 16 hex digits of sha256>.bice`.
- **CI validates the manifest strictly**, refusing duplicate keys, unknown keys and any violation
  above, before any envelope is read (stage 2.2b). The browser validates its structure — types,
  lengths, uniqueness, membership — and relies on CI for duplicate keys, since the manifest it
  receives is the one the trusted release path published (PLAN §3.4).

---

## 5. The algorithms

### 5.1 The reader

Given the manifest, the expected `report_id`, a `profile_id` and the password typed, in this order,
stopping at the first failure with nothing returned. Each step that can refuse has **one refusal
code**, the same in both implementations (ENV-1-04): a code names the check that failed, never a
guess at what changed, since the reader has nothing to tell a wrong password from an altered slot.

| Step | Check | Refusal code |
|---|---|---|
| 0 | The manifest validates under §4 — in the browser, its structure; in CI, strictly as well. Done once per manifest, before any envelope | `manifest_invalid` |
| 1 | The envelope's length and SHA-256 equal the manifest's `size` and `sha256` for the expected report | `integrity_mismatch` |
| 2 | The header parses under §2.1–§2.2 and §3, field by field, every byte read once; the file ends exactly after the tag | `header_malformed` |
| 3 | `package_id` equals the manifest's; `report_id` equals the one expected | `identity_mismatch` |
| 4 | The set of slot `profile_id`s equals the report's entitled set in the manifest, and each slot's `salt` and `iterations` equal that profile's entry | `slots_mismatch` |
| 5 | The profile asked for has a slot — decided without deriving anything | `not_entitled` |
| 6 | The KEK is derived (§2.3) — in the browser, once per login, kept as a non-extractable `CryptoKey` whose only usage is `unwrapKey` | — |
| 7 | The profile's slot is unwrapped into the DEK | `unwrap_failed` |
| 8 | The ciphertext and tag are decrypted with the header as authenticated data | `decrypt_failed` |
| 9 | The payload parses under §2.4, exactly | `payload_malformed` |

It returns the totals bytes and the Parquet bytes. The site shows a visitor one message per kind —
*not entitled* for `not_entitled`, *does not open* for every other code —, never a partial report.

### 5.2 The producer

1. Validate the profile declaration (§3) and the payloads (§2.4).
2. Draw `package_id`, then one salt per profile, from the operating system's cryptographic
   generator. Derive each KEK.
3. For each report: draw a fresh DEK and a fresh IV; wrap the DEK under the KEK of each entitled
   profile, in ascending `profile_id` order; assemble the header; encrypt; write the file under its
   content-hashed name; record its SHA-256 and size.
4. Before returning, check the package as the gate will (§6.4): every envelope opens for every
   entitled profile and for no other; no two envelopes share a DEK; no two share an IV.
5. **Any failure discards the whole package.** A retry is a new run: new `package_id`, new salts,
   new DEKs, new IVs — nothing drawn by a failed attempt is reused, and no single file is ever
   encrypted again inside a package. An unchanged encrypted package is promoted, never encrypted
   again (PLAN §3.6).

The producer has two layers, so that the vectors are reproducible without a test path in the
production one:

- `seal_report` takes every input explicitly — DEK, IV, salts, `package_id` — and is pure. The
  vectors (§6.2), the sealed negative fixtures (§6.3) and the injected-reuse tests (§6.4) call it
  directly.
- `encrypt_package` draws everything from the operating system's generator and has **no parameter
  for a random source**: nothing a caller passes can make it deterministic.

---

## 6. The oracles

### 6.1 Known-answer vectors of the primitives

Run in both implementations, against values published by their standards, before any envelope:

| Primitive | Vectors |
|---|---|
| PBKDF2-HMAC-SHA-256 | [RFC 7914 §11](https://www.rfc-editor.org/rfc/rfc7914#section-11), its two PBKDF2 vectors |
| AES-KW with a 256-bit KEK and 256 bits of key data | [RFC 3394 §4.6](https://www.rfc-editor.org/rfc/rfc3394#section-4.6) |
| AES-256-GCM with a 96-bit IV and authenticated data | Test case 16 of McGrew and Viega, *The Galois/Counter Mode of Operation (GCM)*, the specification submitted to NIST, appendix B |

### 6.2 The complete envelope vectors

Fixed files in the repository: three envelopes of **one package** — one `package_id`, one salt
per profile — and its manifest, with every input in hex — passwords, salts, iterations,
`package_id`, DEKs, IVs, payloads — and the expected envelope bytes and SHA-256:

| Vector | What it fixes |
|---|---|
| `p13_two_profiles` | P13, with the slots of `diretoria` and `logistica` — the order of slots and the repeated salt |
| `p01_one_profile` | P01, with the slot of `diretoria` only — opened by `diretoria`, refused to `logistica` as `not_entitled` |
| `p02_one_profile` | P02, with the slot of `diretoria` only — the same entitled set and salts as P01, so that one can be served as the other and reach the identity checks (§6.3, group I and D) |

The Python producer rebuilds each from its inputs byte for byte (`seal_report`); the JavaScript
reader, written separately, opens each with the password and the manifest and returns the payload
of the vector. A change to either implementation that moves a single byte fails both. They use the
real 600,000 iterations, because the reader refuses fewer.

### 6.3 The negative cases

Each case starts from the vectors of §6.2, changes what its row says and expects **one refusal
code** (§5.1). Both implementations run all of them, with the same case ids (ENV-1-04: a case id
names the mutation, a refusal code names the check).

**How a case reaches its step** (ENV-1-01). Every check before the target step must pass, or the
case proves nothing about the target:

- outside group A, the manifest presented with a mutated envelope has its `size`, `sha256` and
  `file` **recomputed for the mutated bytes**, so step 1 passes; every other field of the
  manifest is the vectors' own, unless the row says it changes;
- every iteration count a case uses is inside the bounds of §3, except in the cases that test the
  bounds;
- a case against step 3 or later keeps the slot set, salts and iterations equal to the manifest's,
  except where the row changes them on both sides;
- a case against step 8 changes bytes after any re-sealing: the last mutation is the one under
  test.

Byte mutations — a bit flipped, a field rewritten, a cut, a byte appended — are applied by each
suite to the vectors itself. The cases that need sealing — `foreign_envelope`'s other package,
`foreign_package_rewritten` and `payload_shape` — are **frozen as fixture files** produced by
`seal_report`, next to the vectors, so that the JavaScript suite, which has no producer, reads
the same bytes as the Python one. The package checks of §6.4 are the producer's and the gate's,
in Python only.

| Group | Case id | Change | Code (step) |
|---|---|---|---|
| **M** manifest | `manifest_shape` | Each rule of §4 broken in turn: a missing or unknown key, a wrong type, uppercase or short hex, an unsorted list, a repeated id, a report entitled to no profile, a profile listing an unknown report, a `file` not of its form, `manifest_version` or `envelope_format_version` other than 1 | `manifest_invalid` (0) |
| | `manifest_identity_bytes` | A profile or report id with a final line feed, a final space, an uppercase letter in a profile id, a lowercase one in a report id, an empty id, one byte over the length bound | `manifest_invalid` (0) |
| | `manifest_iterations_bounds` | A profile's `iterations` 599,999 or 2,000,001 | `manifest_invalid` (0) |
| | `manifest_duplicate_key` | A key repeated in an object — **CI's validator only**: the browser's `JSON.parse` cannot see it (§4) | `manifest_invalid` (0) |
| **A** integrity | `bit_flipped_unrefreshed` | One bit of the envelope, the manifest unchanged | `integrity_mismatch` (1) |
| | `size_only` | The manifest's `size` changed by one, the envelope unchanged | `integrity_mismatch` (1) |
| | `foreign_envelope` | P02's envelope served as P01, or an envelope of another package, the manifest unchanged | `integrity_mismatch` (1) |
| **H** header | `header_truncated` | Cut at every field boundary of §2.1–§2.2 and inside the ciphertext | `header_malformed` (2) |
| | `header_trailing_byte` | One byte appended | `header_malformed` (2) |
| | `header_fixed_byte` | Each byte of offsets 0–14 changed in turn | `header_malformed` (2) |
| | `header_identity_bytes` | `report_id` or a `profile_id` with a final line feed, out of range, empty or one over its bound, its length byte adjusted to match | `header_malformed` (2) |
| | `header_slots_shape` | `slot_count` 0 or 9; two slots with the same id; slots out of order | `header_malformed` (2) |
| | `header_ciphertext_len` | `ciphertext_len` 0, above 32 MiB, one more or one less than the file holds | `header_malformed` (2) |
| | `header_iterations_bounds` | A slot's `iterations` 599,999 or 2,000,001, the manifest unchanged | `header_malformed` (2) |
| **I** identity | `package_expected_differs` | The manifest's `package_id` changed, the envelope unchanged | `identity_mismatch` (3) |
| | `report_served_as_other` | P02's envelope served as P01 | `identity_mismatch` (3) |
| **S** slots | `slot_salt_differs` | One bit of a slot's `salt`, the manifest unchanged | `slots_mismatch` (4) |
| | `slot_iterations_differs` | A slot's `iterations` 600,001, the manifest unchanged | `slots_mismatch` (4) |
| | `slot_removed` | P13 without the slot of `logistica`, `slot_count` adjusted | `slots_mismatch` (4) |
| | `slot_added` | P01 with a slot for `logistica`, which the manifest does not entitle to it | `slots_mismatch` (4) |
| | `foreign_package_rewritten` | An envelope of another package, its `package_id` rewritten to this one's: its salts are not this package's | `slots_mismatch` (4) |
| **E** entitlement | `not_entitled` | `logistica` asks for P01 | `not_entitled` (5) |
| **U** unwrap | `wrong_password` | Each profile with the other's password, and with a password one character longer | `unwrap_failed` (7) |
| | `wrapped_key_bit` | One bit of the asking profile's `wrapped_key` | `unwrap_failed` (7) |
| | `salt_both_sides` | One bit of the asking profile's salt, in the slot and in the manifest alike | `unwrap_failed` (7) |
| | `iterations_both_sides` | The asking profile's `iterations` 600,001, in the slot and in the manifest alike | `unwrap_failed` (7) |
| **D** decryption | `iv_bit`, `tag_bit`, `ciphertext_bit` | One bit | `decrypt_failed` (8) |
| | `report_id_rewritten` | P02's envelope served as P01, with the header's `report_id` rewritten to `P01` | `decrypt_failed` (8) |
| | `package_id_rewritten` | The header's `package_id` rewritten, and the manifest's changed to match | `decrypt_failed` (8) |
| | `other_slot_bit` | One bit of `diretoria`'s `wrapped_key` in P13, opened by `logistica`: the slot it unwraps is intact, so only the authenticated data catches the change | `decrypt_failed` (8) |
| **P** payload | `payload_shape` | Sealed validly by `seal_report` around a bad payload: magic, version, `totals_len` 0, 1 or above its bound, lengths that do not consume the plaintext exactly, a Parquet without `PAR1` at either end | `payload_malformed` (9) |

### 6.4 The package checks

Run by the producer before it returns (§5.2) and again by the package gate in CI (stage 2.2b),
both with the public passwords:

- **The whole matrix.** For every profile and every report: an entitled pair opens and its payload
  is the one recorded; an unentitled pair is refused as *not entitled*, **and** the profile's KEK
  fails to unwrap every slot of that envelope — the proof that no wrapped key of it opens for that
  profile, whatever its label says.
- **No reuse — two separate checks.** Unwrapping every slot gives the raw DEKs: no two envelopes
  of the package share a DEK (`dek_reused`), and no two share an IV (`iv_reused`). The first
  protects the access as well as GCM: a DEK shared by P13 and P01 would let the `logistica` slot
  of P13 open P01. Fresh random values make an accidental repeat negligible, not impossible; the
  checks make it caught. Where the live package is available, its DEKs and IVs are compared too,
  with the same two codes — the gate reads it at stage 2.2b [planned].
- **The injected-reuse tests** (ENV-1-02), each a package sealed by `seal_report` that is valid in
  every other respect:

  | Case id | Package | Expected |
  |---|---|---|
  | `reuse_control` | Distinct DEKs, distinct IVs | Accepted |
  | `reuse_dek_only` | Two envelopes with the same DEK and different IVs | `dek_reused` |
  | `reuse_iv_only` | Two envelopes with different DEKs and the same IV | `iv_reused` |
  | `reuse_both` | Two envelopes with the same DEK and the same IV | `dek_reused` and `iv_reused` |

  Each check is proved on the case only it can catch: without the DEK check, `reuse_dek_only`
  passes; without the IV check, `reuse_iv_only` does.

### 6.5 The counter-proof of each check

A case that passes against a reader missing its check proves nothing (ENV-1-01). So, once, when
the implementations exist, each check of steps 0–5 and 9 and each of `dek_reused` and `iv_reused`
is removed in turn — replaced by a pass-through in a **copy** of the module under `/tmp`, never by
a switch in the module itself — and the cases of its group are run against that copy: every one
of them must then fail, giving a later code or opening. Steps 7 and 8 are the primitives' own
refusals and have no check to remove; their cases are proved by reaching step 7 or 8 with every
earlier check passing. The literal output of that run goes into the evidence of stage 2.2a.

### 6.6 What is outside these oracles

The whole matrix in the browser against a preview, and the finished deploy artifact inspected for
clear data and keys, are stage 2.6's and 2.2b's (PLAN §3.4, §3.6) — this format makes them
possible; they prove the site.

---

## 7. Where it is implemented

| Part | Where [planned] | Runs in |
|---|---|---|
| Constants, `seal_report`, `encrypt_package`, the reader and the package checks, in Python | `src/bi_como_codigo/envelope.py`, with `cryptography` as its first runtime dependency | `make check`, through pytest; the exporter (2.4) and the package gate (2.2b) |
| The reader in JavaScript — written separately from the Python, from this document | `web/envelope.mjs`, a plain ES module with no dependency, using `globalThis.crypto.subtle` only | `make check`, through `node --test` on Node 20 or later, the same WebCrypto API the browser exposes; the site (2.3 onwards) imports the same file |
| The vectors and the sealed negative fixtures | `tests/vectors/envelope_v1/`, one JSON file per vector or fixture, and the vectors' manifest | Both suites |
| The latency of the derivation | `evidence/20261105/` | By hand |

**[measured] M47:** PBKDF2-HMAC-SHA-256 with 600,000 iterations through Node's WebCrypto, deriving
an AES-KW key: median 306 ms of five runs, on an Intel Core i5-7200U with Node v24.18.0. **The
browser's latency is pending**: it is measured in Chrome on the same machine when the reader exists,
and the count stays at 600,000 unless the desktop figure goes above about one second — then the
choice goes back to the Owner (N67).

---

## 8. Not verified, and assumptions

**Not verified:**

- the browser's latency of the derivation (§7), and a phone's at all;
- that Chrome's WebCrypto, which runs on BoringSSL, accepts the same inputs and refuses the same
  cases as Node's, which runs on OpenSSL — the primitive vectors (§6.1) in the browser are stage
  2.6's matrix;
- the sizes of the real payloads against the 32 MiB bound (stage 2.4).

**Assumptions:**

- Python's `cryptography` and Node's WebCrypto implement RFC 3394 with its default initial value and
  report a failed integrity check as an error, never as a wrong key — the negative cases of §6.3
  prove it for both before anything depends on it;
- the two implementations share an author: their independence is in the language, the library and
  the code, not in who reads the specification. Codex's review of both against this document is
  the independent reading.
