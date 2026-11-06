# The package gate — stage 2.2b

> **What lives here:** how stage 2.2b completes the package-to-artifact gate of the publishing
> workflow — the report contract it reads, the control totals it recomputes, the checks it adds to
> `verify` and their order, the comparison with the package already live, the inspection of the
> finished artifact for clear report values, the fixtures, every mutation and the check that
> refuses it, and the tests that prove each check.
>
> **What does not:** why there are three gates and where each one sits — [PLAN §3.4](../PLAN.md#34-the-architecture);
> the envelope's format and its own checks — [`encryption_envelope.md`](encryption_envelope.md),
> which owns them; the workflows, the federation and the promotion — [`publishing_pipeline.md`](publishing_pipeline.md);
> the source-to-package gate on the Owner's machine, with the row-level equality that catches M19 —
> stage 2.4.

| Field | Information |
|---|---|
| Date | 2026-11-06 — revision 1 |
| Author | Claude Code |
| Status | **Plan, for Codex's review before execution.** The Owner's decisions N76–N79 (2026-11-06) shape it; nothing of it is implemented |

**[measured]** has output behind it; **[planned]** is intent; **[assumed]** is a premise about a
tool or service that the stage proves or refutes (§11).

---

## 1. What exists, and what the stage adds

| Check of `verify` ([pipeline §4.2](publishing_pipeline.md#42-job-verify--no-credentials)) | Today [measured, stage 2.2] | 2.2b [planned] |
|---|---|---|
| Inclusion list, media types, no source map, nothing under `__/` | Yes | Unchanged |
| The manifest, strictly; the files exactly the manifest's | Yes | Unchanged |
| Profiles and entitlements equal to `release/profiles.json`; reports equal to the declared ones | Yes | And equal to the contract's (§2) |
| The whole matrix, `dek_unique`, `iv_unique`, `matrix_closed` (envelope §6.4) | Yes | Unchanged |
| The control totals | No: the payload's totals are not read | Parsed strictly and recomputed from the Parquet (§3) |
| The Parquet | Only its `PAR1` framing, by the envelope's reader | Opened by DuckDB, its schema, nulls and grain checked against the contract (§4) |
| Against the package live | No | The four live predicates of envelope §6.4 (§5) |
| Inspection by content | Parquet magic, `BICP` and DEKs outside an envelope; source-map references | And the decrypted report values outside an envelope (§6) |
| Fixtures | Stand-ins: `{"fixture": "P01"}` and a 12-byte `PAR1…PAR1` | Real Parquet files with a contract, written by DuckDB (§7) |

The gate runs in `verify`, with no credential, on `main`'s code; a refusal there uploads nothing
(pipeline §4.2). Every new file is in the protected set — under `release/` or `src/bi_como_codigo/`
— so a PR cannot change what judges it (ADR-0003).

---

## 2. The report contract — `release/contract.json` (N79)

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

Read strictly, by the same rules as the manifest (envelope §4): duplicate keys, `NaN`, `Infinity`
and any key outside the ones above refused; report ids by the envelope's rule; column names
`[a-z][a-z0-9_]{0,62}`, unique within a report; `type` one of DuckDB's names, from a closed list —
`VARCHAR`, `BOOLEAN`, `SMALLINT`, `INTEGER`, `BIGINT`, `DATE`, `TIMESTAMP`, `TIMESTAMP WITH TIME ZONE`,
`DECIMAL(p,s)` with `1 ≤ p ≤ 38`, `0 ≤ s ≤ p`; no floating type: a sum is exact or it is not a
control total. `grain` is a non-empty list of declared columns, all `nullable: false`; `sums` a list
of declared columns of an integer or decimal type, possibly empty. `version` is a positive integer
the exporter writes into the totals (§3), so a package exported against another version of a view
is refused.

**Inventory**: the contract's report ids, `release/profiles.json`'s union of entitled reports and
the manifest's reports must be the same set — a report missing or extra in any of the three is
refused (`inventory_exact`).

A change to the contract is a PR that touches `release/`: it gets no preview and promotes nothing
(ADR-0003); the next content PR is judged by the new contract.

---

## 3. The control totals (N78)

The payload's `totals` (envelope §2.4) are, from 2.2b on, exactly this object:

```json
{"contract_version": 1, "report_version": 1, "rows": 1140, "sums": {"valor": "33076529.47", "unidades": "13920"}}
```

- parsed by the envelope's strict JSON (duplicate keys, `NaN`, `Infinity`, non-UTF-8 and a
  non-object top refused — envelope §2.4), then **exact keys**: those four, no other
  (`totals_shape`). Stage 2.4 may add keys; it does so by changing this rule, in a protected PR;
- `contract_version` and `report_version` equal to the contract's (`totals_version`);
- `rows` a non-negative integer equal to DuckDB's `count(*)` over the Parquet (`totals_rows`);
- `sums` with exactly the contract's `sums` columns as keys, each a string in canonical decimal
  form — no sign but `-`, no leading zero but a lone `0`, exactly the column's scale after the
  point, `0` scaled for no row (`0.00`) — equal to DuckDB's `CAST(COALESCE(SUM(c), 0) AS
  DECIMAL(38,s))` rendered as `VARCHAR` (`totals_sums`). A null cell is not summed; a nullable
  sum column is allowed and declared.

The fixtures' totals are computed **independently** of the gate — in Python with `decimal`, from
the rows the fixture writes —, so a defect shared by DuckDB's sum and the gate's query would not
pass unseen.

---

## 4. The Parquet against the contract (N77)

For each report, after the matrix has opened it with an entitled profile:

1. the Parquet bytes are written to a fresh temporary directory created by the gate — the path
   is the gate's, never derived from the candidate — and opened by DuckDB for Python, pinned
   `duckdb==1.5.6` [planned], on a connection configured before any read with
   `autoinstall_known_extensions=false`, `autoload_known_extensions=false`, `threads=1` and a
   `memory_limit`, then `lock_configuration=true`;
2. **schema** (`schema_exact`): `DESCRIBE SELECT * FROM read_parquet(path)` gives exactly the
   contract's columns, in order, with exactly its types — a column renamed, added, removed,
   reordered or retyped is refused. Parquet does not carry `NOT NULL` from DuckDB, so nullability is
   checked on the data, next step [measured, 2026-11-06: every column read back as nullable];
3. **nulls** (`not_null`): `count(*) FILTER (WHERE c IS NULL)` is 0 for each `nullable: false`
   column;
4. **grain** (`grain_unique`): `count(*) = count(DISTINCT (grain columns))` — a duplicated row
   breaks it, and so does any two rows that share the grain;
5. **totals** (§3).

A Parquet DuckDB cannot read is refused as `parquet_unreadable`, with DuckDB's message. The file is
data from a PR, opened in a job with no credential and a read-only token (pipeline §4.2): a parser
defect exploited here reaches nothing that can deploy.

---

## 5. Against the package live (envelope §6.4)

`verify` reads the package that live serves, from the site's public URL — `https://<FIREBASE_SITE>.web.app/package/manifest.json`, the site from the repository variable, never written in the code — with no credential, since live is public:

- **404** on the manifest is **no live package** — the first release — and the four predicates
  are not run, which `release.json` records (`live: none`); any other status but 200, a redirect,
  or a manifest the strict validator refuses, fails the gate (`live_unreadable`) — never "no
  package";
- each envelope the live manifest lists is fetched and must match its manifest entry's size and
  SHA-256 (`live_unreadable` otherwise);
- then, with the candidate:
  - **the same `package_id`**: the candidate must be live unchanged — the same report set, each
    envelope byte-identical, each manifest entry and profile entry equal (`live_unchanged_identical`,
    refusing `package_id_reused`);
  - **a different `package_id`**: no DEK of the candidate equals one of live's (`live_dek_fresh`,
    `dek_reused`), no IV (`live_iv_fresh`, `iv_reused`), no profile salt (`live_salt_fresh`,
    `salt_reused`). IVs and salts are public — header and manifest —; live's DEKs are unwrapped with
    the declared public passwords, by any entitled profile. A live envelope that no declared
    password opens fails the gate (`live_unreadable`): a password change is not a case 2.2b
    handles (N22 fixes them) — it is refused, not skipped.

**Why reading live in `verify` is enough.** Between this check and the promotion, another release
can go live. But only the newest merge promotes (`decide` condition 1, `promote` step 2), and a PR
whose merge changed included content relative to its head — which another package's merge does —
needs a new preview (`decide` condition 4), so the release that reaches live was compared with the
live of its own last preview [planned argument, for the review].

The live predicates are proved on fixtures by the six cases of envelope §6.4, with live served by
a stand-in in the tests (§9), and once against the real live in a PR (§9.3).

---

## 6. The inspection for clear report values

The finished artifact is already searched for a Parquet magic, `BICP`, a DEK and source maps
outside an envelope (pipeline §4.2). After the matrix, the gate knows every decrypted value, so it
adds: no non-envelope file of `deploy/` contains, as bytes,
- the totals object of any report, as decrypted (`clear_totals`);
- any `VARCHAR` cell value of 12 characters or more, in UTF-8 (`clear_value`);
- any `sums` value of 6 characters or more, as the canonical decimal string (`clear_value`).

The thresholds keep short labels and small numbers — which a page legitimately says — from
refusing an honest artifact; a value re-encoded (escaped, reformatted, base64) is not found. Both
are declared limits (§11), not guarantees: the guarantee against a leak is that the site is built
only from the inclusion list and the package, and that every page is a protected-or-reviewed file.

---

## 7. The fixtures

`tests/site_fixture.py` writes, with DuckDB, one small table per fixture report — P01, P02 and
P13, as today —, built to exercise every check: a decimal and an integer sum column, a nullable
column, a two-column grain in one report, a `VARCHAR` value over the threshold of §6. Its values
are invented placeholders (`fixture_a`, `fixture_b`, …), not figures of eng_dados: no report data
reaches the repository before stage 2.4 (CLAUDE.md §6, rule 2). It computes the totals in Python
(§3), writes `release/contract.json`'s fixture entries once (a protected file, committed), and
seals the package with the envelope's producer, as in 2.2.

---

## 8. The mutations (N76)

Each mutation is a candidate `deploy/` that is valid in every respect but one, built by the tests
from the fixture package; each must stop in `verify`, with the named check, before anything is
uploaded. Sealed mutations are re-encrypted by the envelope's producer, so they pass the matrix and
reach the check under test.

| Id | Mutation (PLAN §3.4) | Stops at |
|---|---|---|
| MUT-01 | A tampered manifest — an envelope's `sha256` wrong | Envelope `integrity_mismatch` (2.2's T6) |
| MUT-02 | A reused key/IV pair — two envelopes with one DEK and one IV | `dek_reused` |
| MUT-03 | The same, IV only | `iv_reused` |
| MUT-04 | Injected clear data — a `.json` holding a Parquet | Inspection, Parquet magic (2.2's T6) |
| MUT-05 | Injected clear data — a page holding a decrypted label value | `clear_value` |
| MUT-06 | Injected clear data — a page holding a report's totals | `clear_totals` |
| MUT-07 | A missing view — a report of the contract absent from package and profiles | `inventory_exact` |
| MUT-08 | An extra view — a report in the package and profiles, not in the contract | `inventory_exact` |
| MUT-09 | A changed type — `valor` written as `DOUBLE` | `schema_exact` |
| MUT-10 | A column renamed, and one dropped | `schema_exact` |
| MUT-11 | A duplicated row | `grain_unique` |
| MUT-12 | A null in a non-nullable column | `not_null` |
| MUT-13 | Totals that do not match: `rows` off by one; one sum off by one cent | `totals_rows`; `totals_sums` |
| MUT-14 | Totals malformed: a duplicate key; a sum as a JSON number; an extra key | Strict JSON; `totals_shape` |
| MUT-15 | Totals of another contract or report version | `totals_version` |
| MUT-16 | A Parquet DuckDB cannot read, with valid `PAR1` framing | `parquet_unreadable` |
| MUT-17 | The live `package_id` with one envelope re-sealed | `package_id_reused` |
| MUT-18 | A new `package_id` reusing a DEK, an IV, a salt of live | `dek_reused`, `iv_reused`, `salt_reused` |
| — | M19, two labels swapped | **Not at this gate** (N76): counts, sums and grain are unchanged; stage 2.4's row-level equality with the views refuses it |

---

## 9. The tests

1. **Every mutation in `make check`**: a test per row of §8 runs `release.verify` — the function
   the workflow runs — on the mutated `deploy/`, and asserts the refusal names its check; a control
   test runs it on the unmutated fixture and passes. The live stand-in is a function the test
   passes in place of the HTTP reader.
2. **A counter-proof per new check**, like M48 (envelope §6.5): a copy of the module with that one
   check made to pass, and its mutation run against the copy — it must no longer stop there. The
   run's literal output goes into `evidence/`.
3. **On GitHub, three real PRs** — MUT-09, MUT-13 and MUT-17 —, each touching only `site/`, each
   refused in `verify` with `preview` skipped and no channel created, read back afterwards; and one
   honest PR, the regenerated fixture package, previewed, merged and promoted under the Owner's
   approval, with the live predicates run against the package live before it.

---

## 10. What changes elsewhere

- `pyproject.toml` and `uv.lock`: `duckdb==1.5.6` as the second runtime dependency (N77), with the
  stage that uses it.
- `release/contract.json`: new. `src/bi_como_codigo/contract.py`: new — the contract, the totals
  and the Parquet checks; `release.py`'s `verify` calls it and gains the live read.
- `publish.yml`: the `verify` job gets `FIREBASE_SITE` for the live URL.
- `docs/encryption_envelope.md` §2.4: the totals' keys are now this document's (§3), extended by
  2.4; §6.4's live table: run at 2.2b, with its evidence.
- PLAN: N76–N79; stage 2.2b's criterion as N76 writes it; stage 2.4 gains M19.

---

## 11. Not verified, and assumptions

- [assumed] DuckDB 1.5.6 reads every Parquet that DuckDB-WASM, chosen at 2.3, reads, and gives
  the same types — the versions differ; 2.3 measures it on the fixtures.
- [assumed] The public URL serves live's current package after a promotion, under
  `Cache-Control: no-cache`; a stale read would compare with the previous live, which the argument
  of §5 makes harmless but not exact.
- [assumed] DuckDB's configuration locks keep a hostile Parquet from loading an extension or
  reaching the network.
- The value inspection of §6 does not find a re-encoded value, nor a value under its thresholds.
- M19 is not caught here (N76).
