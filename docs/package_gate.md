# The package gate — stage 2.2b

> **What lives here:** how stage 2.2b completes the package-to-artifact gate of the publishing
> workflow — the report contract it reads, the control totals it recomputes, the checks it adds to
> `verify` and their order, the comparison with the package live and how it is bound to the
> promotion, the inspection of the finished artifact for clear report values, what a refusal may
> print, the fixtures, every mutation and the check that refuses it, and the tests that prove each
> check.
>
> **What does not:** why there are three gates and where each one sits — [PLAN §3.4](../PLAN.md#34-the-architecture);
> the envelope's format and its own checks — [`encryption_envelope.md`](encryption_envelope.md),
> which owns them, the live predicates included (its §6.4); the workflows job by job, the federation
> and the promotion's steps — [`publishing_pipeline.md`](publishing_pipeline.md), which gains the
> step of §5.2 when it is implemented; the source-to-package gate on the Owner's machine, with the
> row-level equality that catches M19 — stage 2.4.

| Field | Information |
|---|---|
| Date | 2026-11-06 — revision 3: round 2 applied (PGATE-2-01 to 05), with the Owner's decision N83. Revision 2 is `f517d86`: round 1 applied (PGATE-1-01 to 06), with N80–N82. Revision 1 is `62070ec` |
| Author | Claude Code |
| Status | **Plan, under Codex's review before execution.** The Owner's decisions N76–N83 (2026-11-06) shape it; nothing of it is implemented |

**[measured]** has output behind it; **[planned]** is intent; **[assumed]** is a premise about a
tool or service that the stage proves or refutes (§11).

---

## 1. What exists, and what the stage adds

| Check | Today [measured, stage 2.2] | 2.2b [planned] |
|---|---|---|
| Inclusion list, media types, no source map, nothing under `__/` | Yes, in `verify` | Unchanged |
| The manifest, strictly; the files exactly the manifest's | Yes | Unchanged |
| The inventory and the entitlements | One comparison with `release/profiles.json` | Split and ordered: the trusted declarations agree, then the inventory, then the entitlements (§2.2) |
| The whole matrix, `dek_unique`, `iv_unique`, `matrix_closed` (envelope §6.4) | Yes | Unchanged |
| The control totals | Not read | Parsed strictly and recomputed from the Parquet (§3) |
| The Parquet | Only its `PAR1` framing, by the envelope's reader | Opened by DuckDB, bounded, its schema, nulls and grain checked against the contract (§4) |
| Against the package live | No | The four live predicates of envelope §6.4 in `verify` (§5.1), and live bound at the promotion (§5.2) |
| Inspection by content | Parquet magic, `BICP` and DEKs outside an envelope; source-map references | And every decrypted report value outside an envelope, but the public ones (§6) |
| What a refusal prints | The checker's message | A fixed code, the report and the check — never a value (§7) |
| `preview`'s second `verify` | The whole `verify` again, in the job with credentials | The bytes against `verify`'s listing and digest, nothing parsed (§5.3) |
| Fixtures | Stand-ins: `{"fixture": "P01"}` and a 12-byte `PAR1…PAR1` | Real Parquet files under a contract, written by DuckDB (§8) |

The gate runs in `verify`, with no credential, on `main`'s code; a refusal there uploads nothing
(pipeline §4.2). Every new file is in the protected set — under `release/` or `src/bi_como_codigo/`
— so a PR cannot change what judges it (ADR-0003).

---

## 2. The report contract (N79)

### 2.1 `release/contract.json`

The accepted shape of each report, pinned in this repository (PLAN §3.5). In 2.2b it describes the
fixtures; stage 2.4 replaces its entries with the sixteen views, and the exporter and the gate read
the same file.

```json
{
  "contract_version": 1,
  "reports": {
    "P01": {
      "version": 1,
      "columns": [
        {"name": "rotulo",   "type": "VARCHAR",       "nullable": false},
        {"name": "valor",    "type": "DECIMAL(18,2)", "nullable": false},
        {"name": "unidades", "type": "INTEGER",       "nullable": true}
      ],
      "grain": ["rotulo"],
      "sums": ["valor", "unidades"]
    }
  }
}
```

Read strictly, by the envelope's rules for the manifest (its §4): duplicate keys, `NaN`, `Infinity`
and any key outside the ones above refused; report ids by the envelope's rule; column names
`[a-z][a-z0-9_]{0,62}`, unique within a report; `type` from a closed list of DuckDB's names, each
read back by `DESCRIBE` as written [measured, PGATE-1, DuckDB 1.5.6] — `VARCHAR`, `BOOLEAN`,
`SMALLINT`, `INTEGER`, `BIGINT`, `DATE`, `TIMESTAMP`, `TIMESTAMP WITH TIME ZONE`, `DECIMAL(p,s)`
with `1 ≤ p ≤ 38`, `0 ≤ s ≤ p`; no floating type. `grain` is a non-empty list of declared columns,
all `nullable: false`; `version` a positive integer.

**`sums`** lists declared columns whose type is `SMALLINT`, `INTEGER`, `BIGINT`, or `DECIMAL(p,s)`
with **`p ≤ 18`** (N82): DuckDB accumulates them in 38 digits, so no sum of fewer than 10^19 rows can
overflow, and the 32 MiB bound of an envelope (envelope §3) keeps the row count far below that. A
column of `DECIMAL(19..38,s)` may exist; it cannot be summed — a contract that lists it is refused
when it is read. The overflow PGATE-1-05 measured on `DECIMAL(38,2)` is outside this domain, and a
test at its edge proves the bound (§9).

### 2.2 The order of the inventory checks (PGATE-1-04)

1. **The trusted declarations agree** (`declarations_agree`) — before any candidate byte is read:
   the contract's report ids equal `release/profiles.json`'s union of entitled reports. Both are
   protected, so this guards the repository's own state; a PR cannot reach it (admit refuses
   `release/`), and its case is a test on the two files;
2. **the inventory** (`inventory_exact`): the manifest's reports equal the contract's — a report
   missing from the package or extra in it stops here, whatever the manifest's profiles say;
3. **the entitlements** (`entitlements_exact`): each manifest profile, with its reports, equals
   `release/profiles.json`'s — today's comparison, now after the inventory.

---

## 3. The control totals (N78)

The payload's `totals` (envelope §2.4, which points here for their keys) are exactly this object:

```json
{"contract_version": 1, "report_version": 1, "rows": 1140, "sums": {"valor": "33076529.47", "unidades": "13920"}}
```

- parsed by the envelope's strict JSON (duplicate keys, `NaN`, `Infinity`, non-UTF-8 and a
  non-object top refused); then exactly those four keys, `rows` a JSON integer ≥ 0, `sums` an
  object whose values are JSON strings (`totals_shape`). Stage 2.4 may add keys by changing this
  rule, in a protected PR;
- `contract_version` and `report_version` equal to the contract's (`totals_version`);
- `rows` equal to DuckDB's `count(*)` over the Parquet (`totals_rows`);
- `sums` with exactly the contract's `sums` columns as keys, each in canonical decimal form — an
  optional `-`, no leading zero but a lone `0`, exactly the column's scale after the point and no
  point for scale 0, no `-` on zero — equal to DuckDB's `CAST(COALESCE(SUM(c), 0) AS DECIMAL(38,s))`
  rendered as `VARCHAR` (`totals_sums`), which renders negative zero as `0.00` and no exponent
  [measured, PGATE-1]. A null cell is not summed.

The fixtures' totals are computed **independently** of the gate — in Python with `decimal`, at a
precision of 60 digits, from the rows the fixture writes —, so a defect shared by DuckDB's sum and
the gate's query would not pass unseen.

---

## 4. The Parquet against the contract (N77)

For each report, after the matrix has opened it with an entitled profile:

1. the Parquet bytes are written to a fresh temporary directory created by the gate — the path is
   the gate's, never derived from the candidate — and opened by DuckDB for Python, pinned
   `duckdb==1.5.6` [planned], on a new connection configured before any read with
   `autoinstall_known_extensions=false`, `autoload_known_extensions=false`, `threads=1` and a
   `memory_limit`, then `lock_configuration=true`. These settings exist and lock [measured,
   PGATE-1]; they are **not** a sandbox — external access stays enabled and another local file is
   readable [measured, PGATE-1] —, which matters only if a hostile Parquet can make DuckDB read a
   path, and none of the gate's queries takes a path or a setting from the candidate;
2. **schema** (`schema_exact`): `DESCRIBE SELECT * FROM read_parquet(path)` gives exactly the
   contract's columns, in order, with exactly its types. Nullability is checked on the data, next
   step, since DuckDB's Parquet reads back every column as nullable [measured, 2026-11-06];
3. **nulls** (`not_null`): `count(*) FILTER (WHERE c IS NULL)` is 0 for each `nullable: false`
   column;
4. **grain** (`grain_unique`): `count(*) = count(DISTINCT (grain columns))`;
5. **totals** (§3);
6. **the bound on what is materialised** (`content_bound`): before any value leaves DuckDB for §6,
   `COALESCE(SUM(octet_length(encode(c))), 0)` — UTF-8 bytes, 0 for no row or all null; DuckDB
   1.5.6 has no `octet_length(VARCHAR)` [measured, PGATE-2-01] — summed over every `VARCHAR` column,
   and `count(*)` times the column count, are each under a fixed bound — a 34 KB Parquet can expand to 67 MB of strings [measured, PGATE-1].
   The job also gets a `timeout-minutes`.

A Parquet DuckDB cannot read, or a query that fails, is refused as `parquet_unreadable` — with no
DuckDB message (§7). The Parquet is data from a PR, opened in `verify`, a job with no credential and
a read-only token; after §5.3 no other job opens it.

---

## 5. The package live

### 5.1 In `verify` — the predicates, against what live serves (envelope §6.4)

`verify` reads live's package from the site's public URL — `https://<FIREBASE_SITE>.web.app/package/manifest.json`,
the site from the repository variable, never written in the code — with no credential:

- **404** on the manifest is **no live package**; any other status but 200, a redirect, or a
  manifest the strict validator refuses, fails the gate (`live_unreadable`);
- each envelope the live manifest lists is fetched and must match its manifest entry's size and
  SHA-256 (`live_unreadable` otherwise);
- the predicates of envelope §6.4 then run — the same `package_id` must be live unchanged
  (`package_id_reused`); a different one may share no DEK, IV or salt with live (`dek_reused`,
  `iv_reused`, `salt_reused`). Live's DEKs are unwrapped with the declared public passwords; a live
  envelope that none of them opens fails the gate (`live_unreadable`) — N22 fixes the passwords, and
  a change of them is not a case of 2.2b;
- `release.json` records **what was compared**, as `live`: the sorted list of live's envelope
  paths — each name carries the first 16 hex digits of the envelope's SHA-256, which the manifest
  validator and the integrity check bind to its bytes — and the SHA-256 of live's manifest bytes,
  since the paths alone do not identify it (a profile label can change with the same envelopes,
  PGATE-2-05); or `"none"` after a 404. It is public metadata, like the rest of the record. The
  preview job copies it into the authenticated `release-record` (pipeline §4.3), `decide` reads it
  with the record and passes it to `promote` — the `verified` artifact, kept 7 days, is not relied
  on.

### 5.2 In `promote` — live is still what `verify` compared (PGATE-1-01, N80)

The comparison is only as good as its predecessor: with two PRs in flight, B can be previewed
against L, then A promoted, then B approved — and B would replace A without having been compared
with it [PGATE-1-01's schedule]. So the promotion runs, in the serialised job and in one command — so the order
cannot be split across workflow steps (PGATE-2-04):

1. the re-checks of the tip and of the channel (pipeline §4.4, steps 2–3);
2. **live already serves `VERSION_ID`** → end, nothing to do — a re-run of a successful promotion,
   whose record still names the predecessor it replaced;
3. otherwise, **live is still what `verify` compared**: live's current version is read through
   Hosting's API and its files listed (as `check-version` does); its `package/*.bice` paths must
   equal the recorded ones — none, for `"none"` — and live's manifest, fetched from the site's URL
   and decoded as `check-version` decodes, must have the recorded SHA-256. Otherwise it stops: *live
   changed since this preview; a new PR previews against it* — the recovery of pipeline §4.5;
4. the clone, and its read-back (pipeline §4.4, steps 5–6).

The paths come from the API, not the CDN, so a stale public read in `verify` fails closed here; a
stale manifest read here fails closed too, never open. Nothing is parsed beyond the manifest's
bytes, nothing is decrypted in this job.

### 5.3 `preview` no longer re-runs `verify` (PGATE-1-06)

Today `preview` re-runs the whole `verify` on the downloaded artifact. From 2.2b it only checks the
artifact's files against `verify`'s `release.json` — each path and SHA-256, and the canonical digest
—, so the job that holds a credential never opens a Parquet nor decrypts a payload.

---

## 6. The inspection for clear report values (N81)

The finished artifact is already searched for a Parquet magic, `BICP`, a DEK and source maps
outside an envelope (pipeline §4.2). After the matrix, the gate knows every decrypted value; no
non-envelope file of `deploy/` may contain, as bytes — in `manifest.json`, only its free text, the
profile labels, is searched (N83): its other fields are strictly typed and bound to the package by
its checks, and carry no free content —:

- the totals object of any report, as decrypted (`clear_totals`);
- any `VARCHAR` cell value of **3 or more characters**, in UTF-8 (`clear_value`);
- any numeric cell value, sum, or the totals' `rows`, with **3 or more significant digits, or with
  a non-zero fraction** (PGATE-2-02), in three spellings: canonical (§3, `-1234.50`, `1140`); Brazilian,
  `.` grouping thousands and `,` before the fraction (`-1.234,50`, `1.140`); and `,` before the
  fraction with no grouping (`-1234,50`) — (`clear_value`);
- **except** a value listed in `release/public_values.yml` — protected —, each entry with the reason
  it is public by design, as `docs/public_by_design.yml` does for the passwords: a label that the
  governance portal shows, say, or a date that is also a release's date in `releases.md`. The
  fixtures' values are chosen not to collide with the fixture site, so the list starts empty, and
  the tests prove both ways: a deliberate collision refused while unlisted, accepted once listed.

Dates and timestamps are searched in ISO form (`2026-01-01`, `2026-01-01 10:00:00`), as values of
3 or more characters.
Declared limits, not guarantees (§11): a value re-encoded — escaped, base64, rendered in another
format — is not found; a number of one or two significant digits, or a text of one or two
characters, is not searched, since a page legitimately says them.

---

## 7. What a refusal may print (PGATE-1-02)

A decrypted value must not reach a log either. Every refusal of the new checks is a fixed code
— `schema_exact`, `grain_unique`, `totals_sums`, … — with the report id and, where it helps, a
column name, both public in the contract; never a cell, a total, an operand or a DuckDB message.
Every exception raised while a payload is open — DuckDB's included — is caught at the gate's
boundary and replaced by its code with `from None`, so no traceback carries it. The tests capture
stdout, stderr and the step summary of the CLI on the negative cases of §9 and require none of the
case's values in them.

---

## 8. The fixtures

`tests/site_fixture.py` writes, with DuckDB, one small table per fixture report — P01, P02 and
P13, as today —, built to exercise every check: a decimal and an integer sum column, a nullable
column, a two-column grain in one report, a date. Its values are invented placeholders
(`fixture_a`, …), not figures of eng_dados: no report data reaches the repository before stage 2.4
(CLAUDE.md §6, rule 2). It computes the totals in Python (§3), writes `release/contract.json`'s
fixture entries once (a protected file, committed), and seals the package with the envelope's
producer, as in 2.2. Mutations whose payload the producer would refuse — malformed totals — are
sealed with `seal_report`, the layer below (PGATE-1).

---

## 9. The mutations and their tests (N76)

Each mutation is a candidate `deploy/` valid in every respect but one, built by the tests from the
fixture package; sealed mutations are re-encrypted, so they pass the matrix and reach the check
under test.

| Id | Mutation (PLAN §3.4) | Stops at |
|---|---|---|
| MUT-01 | A tampered manifest — an envelope's `sha256` wrong after its 16-digit name prefix, so the name still matches (PGATE-2) | Envelope `integrity_mismatch` |
| MUT-02 | A reused key/IV pair — two envelopes with one DEK and one IV | `dek_reused` |
| MUT-03 | The same, IV only | `iv_reused` |
| MUT-04 | Injected clear data — `site/releases.md` holding a Parquet | Inspection, Parquet magic |
| MUT-05 | Injected clear data — `site/index.html` holding a short row, `fixture_a 1.25 2` | `clear_value` |
| MUT-06 | The same, a number alone, in Brazilian form | `clear_value` |
| MUT-07 | The same, a report's totals | `clear_totals` |
| MUT-07b | The same, only the row count, `<p>1140</p>` (PGATE-2-02) | `clear_value` |
| MUT-07c | A value hidden in a profile label of the manifest | `clear_value` |
| MUT-07d | A cell value colliding with a release date of `releases.md`, unlisted; then listed | `clear_value`; accepted |
| MUT-08 | A missing view — a contract report absent from the package | `inventory_exact` |
| MUT-09 | An extra view — a report in the package, not in the contract | `inventory_exact` |
| MUT-10 | An entitlement changed — `logistica` entitled to P01 in the manifest | `entitlements_exact` |
| MUT-11 | A changed type — `valor` written as `DOUBLE` | `schema_exact` |
| MUT-12 | A column renamed; one dropped; two reordered | `schema_exact` |
| MUT-13 | A duplicated row | `grain_unique` |
| MUT-14 | A null in a non-nullable column | `not_null` |
| MUT-15 | Totals that do not match: `rows` off by one; one sum off by one cent | `totals_rows`; `totals_sums` |
| MUT-16 | Totals malformed: a duplicate key; a sum as a JSON number; an extra key | Strict JSON; `totals_shape`; `totals_shape` |
| MUT-17 | Totals of another contract or report version | `totals_version` |
| MUT-18 | A Parquet DuckDB cannot read, with valid `PAR1` framing; and one with invalid UTF-8 in a `VARCHAR` | `parquet_unreadable`, its values absent from the output (§7) |
| MUT-19 | A Parquet over the content bound | `content_bound` |
| MUT-20 | The live `package_id` with one envelope re-sealed | `package_id_reused` |
| MUT-21 | A new `package_id` reusing a DEK, an IV, a salt of live | `dek_reused`, `iv_reused`, `salt_reused` |
| MUT-22 | PGATE-1-01's schedule: previewed against L, live became A before the approval | `promote`, §5.2 step 3: live changed |
| MUT-23 | Live's envelopes unchanged, its manifest changed (a profile label) | `promote`, §5.2 step 3: live changed |
| — | M19, two labels swapped | **Not at this gate** (N76): counts, sums and grain are unchanged; stage 2.4's row-level equality with the views refuses it |

The tests:

1. **Every mutation in `make check`**: a test per row runs `release.verify` — the function the
   workflow runs — on the mutated `deploy/` (MUT-22 runs the promotion's check against a stand-in of
   Hosting's API) and asserts the exact code and predicate; the controls — the honest fixture, with its page, `releases.md` and
   manifest; a fresh package against live; the live package unchanged; a promotion whose live did
   not change; the first release, against `"none"`; a re-run of a successful promotion, through the
   whole command — pass. Each new check has its edge cases as tests too: sums
   at `DECIMAL(18,s)`'s limit and with cancellation in either row order, `BIGINT` at its limits,
   scale 0, negative zero, no row, all null; `content_bound` on accented text, no row and all null,
   and an oversized table refused as exactly `content_bound`; the three numeric spellings of §6 on
   negative decimals and grouped integers; a contract listing a `DECIMAL(19,s)` sum refused;
   `declarations_agree` on two disagreeing files.
2. **A counter-proof per new check**, like M48 (envelope §6.5): a copy of the module with that one
   check made to pass, and its mutation run against the copy — it must no longer stop there. The
   run's literal output goes into `evidence/`.
3. **On GitHub, three real PRs** — MUT-05, MUT-11 and MUT-15 —, each touching only `site/`, each
   refused in `verify` with `preview` skipped, no channel created, and the run's log read for the
   case's values (§7); and one honest PR, the regenerated fixture package, previewed against live,
   merged and promoted **under the Owner's approval**, the step of §5.2 passing.

---

## 10. What changes elsewhere

- `pyproject.toml` and `uv.lock`: `duckdb==1.5.6`, the second runtime dependency (N77).
- `release/contract.json`, `release/public_values.yml`: new. `src/bi_como_codigo/contract.py`: new
  — the contract, the totals, the Parquet checks and the value inspection; `release.py`'s `verify`
  calls it and gains the live read, and a `check-live` command for §5.2.
- `publish.yml`: `verify` gets `FIREBASE_SITE` and a `timeout-minutes`; `preview` checks the listing
  instead of re-running `verify` (§5.3) and copies `live` into the `release-record`. `release.py`:
  `Record` and `decide` carry `live`; `promote` runs §5.2's order in one command. `promote.yml`: the
  new input. Both protected, in one
  reviewed PR, like every change of `.github/`.
- `docs/encryption_envelope.md` §2.4: the totals' keys are this document's (§3), extended by 2.4;
  §6.4's live table: run at 2.2b, with its evidence. `docs/publishing_pipeline.md` §4.2–§4.4: the
  changes above, in its own words.
- PLAN: N76–N83; stage 2.2b's criterion as N76 writes it; stage 2.4 gains M19.

---

## 11. Not verified, and assumptions

- [assumed] DuckDB 1.5.6 reads every Parquet that DuckDB-WASM, chosen at 2.3, reads, and gives
  the same types — the versions differ; 2.3 measures it on the fixtures.
- [assumed] Hosting's API lists a version's files with the paths `check-version` already reads;
  §5.2 relies on the paths only.
- [assumed] No Parquet, however hostile, makes DuckDB read a path the gate did not give it; the
  locks of §4 are not a sandbox, and no such path was found in PGATE-1.
- The value inspection of §6 does not find a re-encoded value, a number of one or two significant
  digits, nor a text of one or two characters; in the manifest it searches only the labels, so a
  hostile author could encode a number in a strictly typed field such as `iterations` (N83, an
  adversarial limit).
- The live identity of §5.2 is the envelope paths — 64-bit digest prefixes, not full digests — and
  the manifest's SHA-256; no collision was constructed (PGATE-2-05).
- M19 is not caught here (N76).
