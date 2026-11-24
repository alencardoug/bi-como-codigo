# The exporter — stage 2.4

> **What lives here:** how stage 2.4 builds the source-to-package gate on the Owner's machine.
> That covers the read of the 16 views and the facts checked before it, the view contract pinned
> here and the report contract generated from it, the checks on every row, the frozen reference
> and the Parquet read back against it, the control totals, the package sealed for the two
> profiles, the governance metadata carried as JSON, where clear data may be written and what a
> refusal prints, the migration of the trusted declarations, the evidence a run leaves in Git and
> the mutations that prove each check.
>
> **What does not:**
> - why there are three gates and where each sits — [PLAN §3.4](../PLAN.md#34-the-architecture);
> - what crosses between this repository and eng_dados, and the pin —
>   [PLAN §3.5](../PLAN.md#35-the-contract-with-eng_dados);
> - the Owner's decisions that shape this plan — N105 to N109 in
>   [PLAN §1.2](../PLAN.md#12-the-decisions);
> - the envelope's format and its producer — [`encryption_envelope.md`](encryption_envelope.md);
> - the package-to-artifact gate CI runs on what this stage produces: its report contract (N79),
>   control totals (N78), Parquet checks (N77), value inspection (N81) and sum domain (N82) —
>   [`package_gate.md`](package_gate.md);
> - the report pages and the portal — stages 2.5 to 2.7;
> - the first publication — stage 2.10.

| Field | Information |
|---|---|
| Date | 2026-11-24 — revision 2: round 1 of Codex's review (EXP-1-01 to -13, ten blocking) answered, with the Owner's N105 to N109. Revision 1 is `ae8b684` |
| Author | Claude Code |
| Status | **Plan, in Codex's review.** Nothing of it is implemented. Its live run needs a read window the Owner opens ([UQ-05](upstream_questions.md#answers)) |

**[measured]** has output behind it; **[planned]** is intent; **[assumed]** is a premise about a
tool or service that the stage proves or refutes (§14).

---

## 1. What the stage decides, and what it does not

The criterion, from [PLAN §6.2](../PLAN.md#62-the-stages): *one consistent read; contract, grain,
nulls and decimals checked; typed rows equal to the views after the round trip — which catches M19
(N76); the mutation tests of §3.4 caught; no clear report data in Git.*

- It **reads** the 16 views of `consumption` at the pin, `b0ef66e` of `mvp_eng_dados_2` (N91),
  through the exporter's login (N4), in one transaction. It **writes a package**: the 16 reports,
  sealed for Diretoria, and P13 also for Logística. The package goes to a folder outside Git, beside
  the governance metadata.
- It **migrates the trusted declarations** to the 16 reports in its own protected PR (N109, §11).
  `site/package/` then holds **invented** envelopes of the 16 real shapes. The real package enters
  `site/package/` in an ordinary PR, with a preview, once stage 2.5 has a page that opens it.
- It **proves the real package passes CI's gate**: `release.verify` runs, unchanged, on a private
  candidate with the site's pages and the real package (§10).
- It does **not** recompute a metric (rule 3 of `CLAUDE.md` §6). The control totals are checksums
  inside the encrypted payload, recomputed by CI and never shown (§8, N107).
- It does **not** read inside the warehouse beyond `consumption`, the catalogue and the one relation
  of `governance` the login reads (PLAN §3.5). Oracles over the inner layers are the custodian's.

## 2. What exists, and what is new

| Part | Today | 2.4 |
|---|---|---|
| The read | `evidence/20261117/capture.sh` **[measured, M55, M59]**: `psql` inside the warehouse's container, as `consumption_reader`. It lists the views on one connection, then reads them in one `REPEATABLE READ READ ONLY` transaction on another, in CSV. It fixes the container's name, and it is no longer run from here (`CLAUDE.md` §5) | A Python reader with psycopg 3 (N105), typed, configured only by environment variables, in one transaction that also takes the inventory (§3) |
| The view contract | None. The columns and types are in the captures, the grain in the metadata package's `view_rules` (UQ-18) | `release/views.json`, written once from a draft and reviewed in full (§4) |
| The report contract | `release/contract.json` describes three fixtures (N79) | Generated from the view contract, and checked equal to it (§4.4) |
| The Parquet | DuckDB reads it in `verify` (N77) | DuckDB writes it from exact bindings and reads it back (§7) |
| The control totals | `{contract_version, report_version, rows, sums}`, recomputed in `verify` (N78) | Unchanged in format; every column within N82's domain is summed (N107, §8) |
| The sealing | `envelope.encrypt_package` **[measured]**: it sealed the honest fixture package of PR #30 (`evidence/20261106/t22b_real_prs.out.txt`) | Called as it is (§9) |
| The profiles | `release/profiles.json`: two profiles, three fixtures | Diretoria 16 reports, Logística P13 (PLAN §3.2) |
| `site/package/` | Three fixture envelopes | Sixteen invented envelopes of the real shapes (N109) |
| The governance metadata | Read by `evidence/*/package_check.py` | Carried as JSON, bound to its blob and checked against the contract (§5) |

**The views at the pin [measured, M59 and `evidence/20261124/m59_profile.out.txt`].**
- **Columns:** 16 views, 188 columns. 46 are `numeric` with no declared precision or scale in
  any of them. The rest are 44 `character varying`, 35 `integer`, 35 `bigint`, 23 `text`,
  4 `boolean` and one `timestamp with time zone` (`skus_below_reorder_point.last_movement_at`).
- **Rows:** from 25 (`top_skus_by_revenue`) to 5,775 (`inventory_turnover_by_sku_and_warehouse`),
  14,244 in all.
- **Numerics:** the widest has 7 integer digits; the most fractional digits written is 4; no
  `numeric` value needs more than 9 digits, and none is NaN or infinite.
- **Nulls:** only 9 `numeric` columns have them, from 1 to 641 per column. Every other column is
  never null, and no text is empty.
- **Grain:** in every view, the columns of role `grain` with those of role `identity` repeat no key
  and hold no null.

The profile reads the CSV of M59's capture outside Git and prints no value. CSV cannot tell an
empty text from a null, so "no text is empty" means neither occurs.

## 3. The read

**Where it runs.** On the Owner's machine, inside a read window the Owner opens in
`mvp_eng_dados_2` (UQ-05). This repository starts no container and runs no command of that project
(`CLAUDE.md` §5).

**How it connects [planned] (N105).** psycopg 3, pinned in `uv.lock`, connects to the host and port
the warehouse publishes. Everything comes from environment variables, so another environment is
other values (`CLAUDE.md` §5):

| Variable | What |
|---|---|
| `BICE_WAREHOUSE_HOST`, `BICE_WAREHOUSE_PORT`, `BICE_WAREHOUSE_DB` | Where the warehouse is |
| `BICE_WAREHOUSE_USER`, `BICE_WAREHOUSE_PASSWORD` | The exporter's login (N4). The password is never printed nor written |
| `ENG_DADOS_2_DIR` | The checkout of `mvp_eng_dados_2`, read only with `git` (§5) |
| `BICE_EXPORT_STAGING`, `BICE_EXPORT_DIR` | Where clear data may be written, and where the sealed result goes (§10) |

The Owner sets the warehouse variables from that checkout's own configuration. The connection
refuses unless `sslmode`, `PGOPTIONS` and the like come only from these variables. libpq's own
environment (`PGTZ`, `PGOPTIONS`, `PGSERVICE`, `PGSSLMODE`) is cleared for the process.

**One transaction, once [planned].** One connection, opened with `autocommit` off and
`isolation_level = REPEATABLE READ`, `read_only = True`. Its first statement starts the transaction,
and every fact below is read inside it, so the snapshot is one. There is no retry and no second
connection: a failed statement, a failed `COMMIT` or a lost connection refuses the run. The
transaction ends with `COMMIT` after the last read.

**The facts checked before any row [planned]**, each refusing with its fixed code:

1. **The transaction**: `transaction_isolation` is `repeatable read` and `transaction_read_only` is
   `on`.
2. **The session settings**: `TimeZone`, `DateStyle`, `IntervalStyle` and `extra_float_digits`
   equal their server defaults (`pg_settings.reset_val`). `server_encoding` and `client_encoding`
   are `UTF8`. All are recorded. Text order is the database's collation, recorded from
   `pg_database.datcollate`.
3. **The login**: `session_user` and `current_user` are both the contract's login. A `SET ROLE` or
   a different login refuses.
4. **The login's attributes** in `pg_roles`: not superuser, no `CREATEROLE`, no `CREATEDB`, no
   `REPLICATION`, no `BYPASSRLS`.
5. **The role graph**: the login's memberships, closed recursively over `pg_auth_members`, are
   exactly the set the contract declares — `analyst` today (N4). A missing, extra or nested role
   refuses. The first live run measures the closure. A difference refuses, and the contract changes
   only by a PR.
6. **The inventory**: every relation of `consumption` in `pg_class`, of any kind, read from the
   catalogue whatever the grants: exactly the contract's 16 names, each of kind `v`. A missing view,
   an extra view or table — granted or not — or a view of another kind refuses.
7. **The effective access**: for each of the 16, `has_table_privilege` gives `SELECT` and none of
   `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`. The login owns none of them, and `has_schema_privilege`
   gives no `CREATE` on `consumption`. That the database refuses every write elsewhere is eng_dados'
   own `test_acesso`, run by the custodian, and is not repeated here.
8. **The provenance**: `governance.warehouse_provenance` has exactly one row. It is `verified`, and
   its `built_from_commit`, `invocation_id` and `sequence` match one entry of the contract's
   `accepted_builds` (§4.1). Today that entry is M59's: `bcc2d5c…`, `1cb3cd4e-…`, sequence 125. A
   new build — the same commit included — refuses until its views are captured and compared, as M59
   was, and a PR adds its entry (PLAN §3.5, the pin). The row is recorded as read.

**The witness [planned].** Each accepted build carries a witness: the 16 views' row counts and
fingerprints. Today the witness is M59's, in `evidence/20261119/capture.out.txt`. Every run
computes the fingerprints inside its transaction with M55's exact expression:
`md5(coalesce(string_agg(t::text, E'\n' order by t::text), ''))` over `consumption.<view> t`. Every
count and fingerprint must equal the witness. A difference in any one refuses, whatever the
provenance row says. The settings of check 2 are what make the text form comparable. M59's session
settings were not recorded, so a first mismatch from settings alone is possible, and it refuses
(§14).

**The rows [planned].** For each view, in the contract's order:

- `SELECT count(*)`, refused above the view's `max_rows` (§4.1) before any row is fetched;
- `SELECT <the contract's columns, quoted, in order> FROM consumption.<view> ORDER BY <grain>`;
- the result's own metadata — `cursor.description`: names, type OIDs and, for `numeric`, the
  modifier — compared with the contract before any row is mapped. This is the query's result, not
  `information_schema`;
- the rows **frozen** into the reference of §7.

`now()` at the transaction's start is recorded as `read_at`.

## 4. The view contract

### 4.1 `release/views.json`

One declaration, reviewed in full (`CLAUDE.md` §5).

**For the whole contract:**
- `login`, `roles` (the closure of §3 check 5);
- the pin, as the full 40-character commit;
- `metadata_blob`: the Git blob id of `docs/pacote_de_metadados.json` at the pin;
- `accepted_builds`: each with its provenance row and its witness file.

**For each of the 16 views:**

| Key | What | Source |
|---|---|---|
| `view` | The name in `consumption` | M59's capture |
| `report` | The question's code, P01–P16 | The metadata package's `questions.<P>.view` (§5) |
| `version` | An integer, raised at every change | Here |
| `columns` | In order: the name; the PostgreSQL type and its OID; for `numeric`, the precision and scale of §4.2; `nullable`; for text, `max_length` | The capture and M59's profile |
| `grain` | The columns that identify a row: role `grain`, with `identity` where the view has it | `view_rules.<view>.columns` (UQ-18) |
| `max_rows` | The most rows the export accepts | M59's count, with headroom |
| `may_be_empty` | Whether zero rows is a valid read | `false` for every view today |

`nullable` is `true` for the 9 columns M59 found with nulls, and `false` elsewhere. A null where
the contract says `false` refuses (§6), and the contract changes only by a PR.

### 4.2 Decimals with no declared scale (N106)

Parquet's and DuckDB's decimals need a precision and a scale, up to 38 digits. The views declare
neither for any of their 46 `numeric` columns. Each column is therefore declared in the contract as
follows:

- **The scale** is the most fractional digits M59 measured for it, as PostgreSQL writes them.
  PostgreSQL keeps a value's display scale, so this is the scale the view's own rounding produces.
- **The integer part** is the most integer digits measured, plus 3.
- **The precision** is their sum, and never more than 18. Today the widest needs 9 digits, so the
  most any column takes is 12. Keeping every column within 18 also keeps every column inside N82's
  sum domain (§8).

A value that does not fit refuses the run. The contract then changes in a PR, and is reviewed. The
export never rounds.

### 4.3 The exact fit, and the exact binding

**The fit [planned].** Each value is the client's `Decimal`, examined under a local context of 200
digits, never the default of 28:

- `NaN`, `Infinity` and `-Infinity` refuse — PostgreSQL's `numeric` admits them;
- negative zero becomes zero;
- trailing zeros are removed, so `1.50` counts one fractional digit;
- the value fits when its fractional digits are at most the scale and its integer digits at most
  precision minus scale.

The fit is computed from the decimal's own digits and exponent, with no arithmetic that rounds.

**The binding [planned].** A `Decimal` is never bound as a parameter: DuckDB infers `DOUBLE` for
one and loses digits (EXP-1-04, reproduced in round 1 with DuckDB 1.5.6). Each value is bound as its
exact fixed-point string and cast explicitly, `CAST(? AS DECIMAL(p,s))`. Integers are bound as
Python integers and cast to their contract type. Text is bound as text.

**Instants [planned].** psycopg returns `timestamp with time zone` as an aware `datetime`. A naive
one refuses, and so does PostgreSQL's `infinity` or a date the client cannot hold. Each instant
becomes its integer microseconds since the epoch, in UTC. It is bound as that integer and built in
DuckDB as `make_timestamp(us)::TIMESTAMPTZ` with DuckDB's time zone set to UTC. It is read back as
`epoch_us(...)`, never fetched as a Python `datetime`, because the locked DuckDB cannot fetch a
non-null `TIMESTAMPTZ` without `pytz` (EXP-1-05, reproduced in round 1).

### 4.4 The report contract is generated

`release/contract.json` (N79) is **generated** from `views.json`, by `export contract`, and is not
edited by hand. Its columns, `nullable`, grain and versions are the view contract's. Its types are
mapped to DuckDB's:

| PostgreSQL | DuckDB |
|---|---|
| `character varying`, `text` | `VARCHAR` |
| `integer` | `INTEGER` |
| `bigint` | `BIGINT` |
| `numeric` | `DECIMAL(p,s)` |
| `boolean` | `BOOLEAN` |
| `timestamp with time zone` | `TIMESTAMP WITH TIME ZONE` |

`sums` is every column N82 admits (§8).

A test in `make check` regenerates it and requires the committed file byte for byte. The exporter
runs the same comparison before it connects, over the whole contract: inventory, columns, types,
`nullable`, grain, sums and versions. A hand edit to either file therefore fails both.

**The draft.** `export propose` writes a draft of `views.json` from a capture's committed output,
M59's profile and the metadata package. It writes only into the private staging folder (§10), and
refuses any destination that resolves to `release/`. The draft is reviewed, then committed by hand.
The exporter never writes `views.json` itself.

## 5. The governance metadata, bound to the pin

The metadata package of `mvp_eng_dados_2` — `docs/pacote_de_metadados.json`, format 1 (N87) — is
read with `git -C "$ENG_DADOS_2_DIR" show <full pin>:docs/pacote_de_metadados.json`. The run first
checks two things, and refuses on either:

- `git rev-parse <pin>^{commit}` is the contract's full pin;
- the blob id of that path at the pin is the contract's `metadata_blob`.

The package itself names no commit of its own. Its `provenance.warehouse` describes the warehouse
where the package was generated (PLAN §3.5). So it is the blob id that binds it to the pin, and the
package's `provenance` is recorded apart from the live provenance row, never compared with it.

Then, by these JSON paths, each refusing on a difference:

- `format` is 1;
- **the mapping**: `questions.<P>.view` is `consumption.<view>` for exactly the contract's 16
  pairs, in both directions. A swapped code, a missing or extra question, or two codes for one view
  refuse. And P13 is `consumption.on_time_delivery_rate_by_carrier`, the one report Logística opens
  (PLAN §3.2);
- **the columns**: the names of `view_rules.<view>.columns` and of `relations.<view>.columns` are
  the contract's column names. Names only: the package declares `text` where the catalogue says
  `character varying`, so physical types come from the live catalogue and M59, never from the
  package;
- **the grain**: the columns of role `grain` and `identity` in `view_rules.<view>.columns` are the
  contract's grain, as a set. A view whose rules give no such column refuses.

The package is written unchanged as `metadata.json` beside the sealed package, with its blob id and
SHA-256 in `run.json`. It is public by design (PLAN §3.4), so it is not encrypted. Stage 2.7 reads
it.

## 6. The checks on every view

In this order, on the frozen reference, each refusing with a fixed code that names the view and the
check, never a value (§10):

1. **Schema**: the result's names, order, type OIDs and modifiers, as §3 reads them.
2. **Size**: at most `max_rows`; not empty unless `may_be_empty`.
3. **Nulls**: none in a column that is not nullable.
4. **Decimals**: finite, and fitting exactly (§4.3).
5. **Instants**: aware, and within the client's range (§4.3).
6. **Grain**: no null in a grain column; no two rows with the same grain.
7. **Text**: no NUL and at most `max_length` characters. PostgreSQL's `text` cannot hold a NUL,
   and psycopg decodes UTF-8 strictly under `client_encoding = UTF8`. The check stays, because
   DuckDB and Parquet would carry a NUL silently.

## 7. The frozen reference, and the round trip

**The reference [planned].** Each row of the result is frozen, before any write, as a tuple of
canonical values:

- decimals as the exact fixed-point string at the column's scale;
- integers as integers, booleans as booleans, text as text;
- instants as integer microseconds in UTC;
- null as null.

The reference's digest, over its canonical JSON, is recorded. Nothing downstream mutates it: the
writer receives a copy.

**Writing [planned]** (N77). DuckDB for Python, in a database file inside the private staging folder
(§10), takes the rows through the bindings of §4.3 into a table of the report contract's types. It
writes Parquet with `COPY ... TO ... (FORMAT parquet)`. The writer's options — compression and row
group size — are fixed in the code.

**Reading back [planned].** The Parquet file is read into memory as bytes and its SHA-256 recorded.
Those bytes are what is read back and, later, what is sealed: sealing checks the digest again. The
read-back opens them with `read_parquet`. It selects every column in the contract's order — decimals
cast to their exact text, instants as `epoch_us` — and orders the rows by the grain. Then it
compares them with the reference:

- the same count;
- the same grain key, row by row;
- every cell equal by the canonical comparator of the reference.

That is what catches M19: two channel labels swapped keep every count and sum, and diverge row by
row (N76; 761 rows in M19). The other side of the equality is the transaction's own result, frozen.
`contract.check_payload` then runs on the same bytes too, as CI will: it checks the contract, the
bounds and the totals, but it does not compare rows.

## 8. The control totals (N107)

The format is N78's: `{contract_version, report_version, rows, sums}`, with exact decimal strings.

**What is summed.** `sums` covers **every column N82 admits**: every `INTEGER` and `BIGINT`, and
every `DECIMAL` of precision up to 18. With §4.2, that is every numeric column of every view, and
every view has sums (N107). These are checksums inside the encrypted payload, which CI recomputes
from the Parquet. No page shows them, and no page adds up a non-additive column. The rules of
PLAN §3.2 (M4, M20) are about what pages show, not about these checksums.

**How the exporter computes them [planned].** In Python, from the frozen reference, not from the
Parquet, so the two sides of CI's comparison come from different paths:

- exact `Decimal` arithmetic under a 200-digit context;
- nulls skipped;
- the result written at the column's scale, with no sign on zero;
- an empty or all-null column summing to zero at its scale — what the gate's `COALESCE` gives
  (round 1 reproduced `0.00` at scale 2).

A sum of up to `max_rows` values of precision 18 stays far inside DuckDB's 38-digit accumulator,
which is N82's reason.

## 9. The package

`envelope.encrypt_package` seals the 16 payloads (totals and Parquet) for the profiles of
`release/profiles.json`: Diretoria all 16, Logística P13. The result holds the manifest and the 16
envelopes, under content-hashed names, and `run.json`. `run.json` is written from a fixed schema of
allow-listed fields:

- the pin and `metadata_blob`;
- the provenance row and the metadata's own `provenance`, kept apart;
- `read_at` and the session settings of §3;
- per view: its row count, its fingerprint, the reference digest and the Parquet's SHA-256;
- per envelope: its SHA-256.

It holds no value of any row.

## 10. Where clear data goes, and what a refusal prints

**The private staging folder [planned].** `BICE_EXPORT_STAGING` names an existing directory.
Resolved with `realpath`, it must lie inside no Git worktree: `git -C <path> rev-parse
--is-inside-work-tree` must fail there. That excludes this repository, both eng_dados checkouts and
any other worktree. Inside it, each run:

- takes an exclusive lock, so two runs never overlap;
- creates a fresh directory with `mkdtemp`, mode `0700`.

Every clear byte is written there, and nowhere else:

- the DuckDB database file, with DuckDB's `temp_directory` set inside the same directory;
- the Parquet files;
- the draft of `export propose`;
- the gate's own temporary files — the process's `TMPDIR` and `tempfile.tempdir` point there,
  so `contract.check_payload`'s temporary directory lands inside.

The directory is removed when the run ends: on success, on a refusal, on an exception and on an
interrupt. A run killed outright leaves it in the staging root, outside every worktree. The next run
reports it and refuses until it is removed.

**The result.** Only the sealed package, `metadata.json` and `run.json` leave staging. They go to
`BICE_EXPORT_DIR`, which must not exist yet: they are written into a sibling temporary directory and
renamed into place in one step. A destination inside a worktree must be an ignored path that holds
no tracked file. Ciphertext there is not clear data, but nothing is put where `git add` would take
it.

**The private candidate, and the collisions (N108).** In staging, the run assembles the candidate
CI would build:

- the files of `release/include.txt` from the working tree — today `site/index.html` and
  `site/releases.md` —, with the real package in place of `site/package/`;
- `release.verify` on it, unchanged, with no package live, the one difference from CI.

N81's inspection will find honest values that also appear in public text: the year 2026 is in
`site/releases.md` and in P08's `year_number` (EXP-1-07). For each such collision, the run lists the
value and the public file it appears in to the Owner's terminal. It can show the value, because the
public file already shows it. The Owner approves each one into `release/public_values.json` with its
reason, in a protected PR (N108). An exempted value is then not searched in any report, so a leak
equal to it would pass: each entry says so.

**What a refusal prints.** The command-line boundary catches every exception and prints:

- a fixed refusal code;
- the view and the check, where there is one;
- the exception's class name.

It never prints a message, a traceback, a value or the connection string: a driver's message can
hold a value or a password. There is no debug mode that prints more.

**The evidence in Git** is written by `export evidence` from `run.json`'s allow-listed fields, into
`evidence/<date>/`, and holds no value.

## 11. The migration of the trusted declarations (N109)

`release/contract.json`, `release/profiles.json` and `site/package/` describe three fixtures today.
`verify` refuses when the contract and the package disagree, and the tests load both (EXP-1-08). So
they change together, in one protected PR of this stage. A protected PR gets no preview, and the
Owner reviews it:

- `release/views.json` and the generated `release/contract.json` for the 16 reports;
- `release/profiles.json`, with Diretoria all 16 reports and Logística P13;
- `site/package/` replaced by **invented** envelopes of the 16 real shapes, generated by
  `tests/site_fixture.py` from the new contract. Their values are chosen not to collide with the
  site's public text, as today's are;
- the tests that load `release/` and `site/` updated to the new shapes, with 2.2b's mutations —
  MUT-15, mismatched totals, among them — proved again on the new fixture.

The real package enters `site/package/` later, in an ordinary PR that touches nothing protected, so
it gets a preview (stage 2.5). Before that PR, the private candidate of §10 has already passed
`verify` under the same trusted declarations.

## 12. The mutations, and the tests

**The fake source.** `make check` cannot reach the warehouse. So the reader works over a small
connection interface: execute, fetch, the result's description, commit and close. In production,
psycopg implements it. In tests, a fake implements it and records every statement in order. The
fake is fed by a committed fixture of invented values with the 16 views' real columns, generated by
a script, and a test proves the committed fixture is what the script writes.

**Each mutation changes one thing at its boundary.** Each must stop there, with its code. Each has
a positive control: the same case unmutated passes.

| Boundary | Mutation | Stops at |
|---|---|---|
| The connection | The statements out of order; a failure injected at each one; a failed `COMMIT` | §3: refusal, with no further statement and no second connection |
| The facts | Isolation `read committed`; `transaction_read_only` off; a session setting off its default | §3 checks 1–2 |
| | `session_user` or `current_user` other than the login, as after `SET ROLE`; a superuser or `CREATEROLE` login; a missing, extra or nested role | §3 checks 3–5 |
| | A view missing; an extra view or table, granted or not; a view of another kind; a view not readable; an `INSERT` grant | §3 checks 6–7 |
| | No provenance row, two rows, not `verified`; the same commit with another invocation | §3 check 8 |
| | One fingerprint or one count off the witness | The witness (§3) |
| The result | A column renamed, retyped or moved in the result's description; two same-type text columns swapped in the result | Schema (§6.1) |
| The rows | A row over `max_rows`; an empty view, and an empty view declared `may_be_empty`, which passes | Size (§6.2) |
| | A null where not nullable; and an all-null nullable column with a populated grain, which passes | Nulls (§6.3) |
| | A decimal one fractional digit or one integer digit beyond its type; `NaN`; `Infinity`; negative zero, which passes as zero; a 38-digit value with leading fractional zeros | Decimals (§6.4) |
| | A naive instant; PostgreSQL `infinity`; two instants with the same wall time and different offsets, and microsecond precision, which pass | Instants (§6.5) |
| | A duplicated grain; a null in a grain column | Grain (§6.6) |
| | A NUL; a text over `max_length` | Text (§6.7) |
| The write | M19: two labels swapped in the Parquet bytes between write and read-back; a writer that rounds a decimal; a writer that drops a row | The round trip (§7) |
| | The bytes sealed are not the bytes read back | The seal's digest check (§7) |
| The metadata | A swapped report code in both local contracts; a missing question; a grain role missing; another blob at the pin | §5 |
| The contracts | `contract.json` edited by hand; `views.json` edited without regenerating | §4.4, in `make check` and before connecting |
| | `export propose` pointed at `release/` | §4.4 |
| The paths | Staging inside a worktree, through a symlink, or in an eng_dados checkout; a destination with a tracked file; an existing destination; a leftover directory of a killed run; an interrupt mid-run | §10 |
| The output | An exception whose message holds an invented value or password | §10: neither printed |
| The candidate | A clear value injected into an included file; a tampered manifest; a reused key or IV; mismatched totals (MUT-15) | `verify` on the private candidate (§10), with 2.2b's mutations on the migrated fixture |
| | An honest collision with public text, approved; the same value unapproved | `verify`, which passes the first and refuses the second (§10) |

**The live run**, in the read window, is not in `make check`. It writes its evidence with
`export evidence`:

- the facts of §3 and the provenance row;
- each view's count and fingerprint against the witness;
- each digest;
- `verify`'s result on the private candidate;
- the time each phase took.

It writes no value.

## 13. Questions answered by the Owner

All five were answered on 2026-11-24 and are recorded in PLAN §1.2:

- **N105 — the client.** psycopg 3, over the host `psql` client, which this machine does not have.
  `psql` inside the container is no longer allowed from here.
- **N106 — the scale.** Per column, from M59's measurement, with three integer digits of headroom
  and at most 18 digits (§4.2).
- **N107 — the control sums.** Every column within N82's domain, as checksums never shown (§8).
- **N108 — public collisions.** Each approved into `release/public_values.json` with its reason, in
  a protected PR (§10).
- **N109 — the migration.** In this stage, in one protected PR, with invented envelopes of the 16
  shapes (§11).

## 14. Not verified, and assumptions

- **[assumed]** psycopg 3 returns `numeric` as `Decimal` with every digit, and `timestamptz` as an
  aware `datetime`, and its `cursor.description` carries the type OID and the numeric modifier. To
  be proved by the first live read.
- **[assumed]** The published port accepts the reader's login from the host. M55 and M59 connected
  from inside the container.
- **[assumed]** DuckDB 1.5.6 writes and reads `DECIMAL(p,s)` up to 18 digits from exact strings,
  and `TIMESTAMPTZ` built from integer microseconds, in Parquet, with no loss. Round 1 found the
  `Decimal`-parameter and `datetime`-fetch paths lossy or failing. The bindings of §4.3 avoid both,
  and the fixture tests prove them before any live read.
- **[assumed]** M59's session settings were the server's defaults. They were not recorded, so a run
  could refuse on the witness for settings alone. That refusal is safe: it is then investigated,
  never bypassed.
- **Not measured**: the closure of the login's roles (§3 check 5), measured by the first live run;
  the run's time and memory; the package's size.
- **Not measured**: which honest values collide with public text beyond the year 2026, found by the
  first private candidate (§10).
- M59's profile holds for its rows. The live run checks every rule again on the rows it reads.

## 15. The order of the work

1. This plan, reviewed by Codex until no blocking finding is left.
2. `release/views.json` from `export propose`'s draft, reviewed in full; the generated
   `release/contract.json`; `release/profiles.json`; the invented fixture of the 16 shapes. All in
   the protected PR of §11, with the code below.
3. The connection interface, the fake and its fixture; the facts of §3, the checks of §6, the
   reference and round trip of §7, the totals, the sealing, the paths and output of §10, and each
   mutation of §12 with its test, in `make check`.
4. Codex's review of the code; then the Owner's review of the protected PR.
5. The live run in the Owner's read window: the private candidate, the collisions approved in a
   protected PR, and the evidence committed.
