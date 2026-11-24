# The exporter — stage 2.4

> **What lives here:** how stage 2.4 builds the source-to-package gate on the Owner's machine.
> That covers the read of the 16 views, the view contract pinned here, the checks on every row,
> the Parquet written and read back, the control totals, the package sealed for the two profiles,
> the governance metadata carried as JSON, the evidence the run leaves in Git, the mutations that
> prove each check, and the questions still open for the Owner.
>
> **What does not:**
> - why there are three gates and where each sits — [PLAN §3.4](../PLAN.md#34-the-architecture);
> - what crosses between this repository and eng_dados, the pin and the warehouse provenance row —
>   [PLAN §3.5](../PLAN.md#35-the-contract-with-eng_dados);
> - the envelope's format and its producer — [`encryption_envelope.md`](encryption_envelope.md);
> - the package-to-artifact gate that CI runs on what this stage writes, its report contract
>   (N79), its control totals (N78) and its Parquet checks (N77) — [`package_gate.md`](package_gate.md);
> - the report pages and the portal — stages 2.5 to 2.7;
> - the first publication — stage 2.10.

| Field | Information |
|---|---|
| Date | 2026-11-24 — revision 1 |
| Author | Claude Code |
| Status | **Plan, for Codex's review.** Nothing of it is implemented. Its run needs a read window the Owner opens ([UQ-05](upstream_questions.md#answers)) |

**[measured]** has output behind it; **[planned]** is intent; **[assumed]** is a premise about a
tool or service that the stage proves or refutes (§12).

---

## 1. What the stage decides, and what it does not

The criterion, from [PLAN §6.2](../PLAN.md#62-the-stages): *one consistent read; contract, grain,
nulls and decimals checked; typed rows equal to the views after the round trip — which catches M19
(N76); the mutation tests of §3.4 caught; no clear report data in Git.*

- It **reads** the 16 views of `consumption` at the pin, `b0ef66e` of `mvp_eng_dados_2` (N91),
  through the exporter's login (N4), in one transaction, and **writes a package** — the 16 reports
  sealed for Diretoria and P13 also for Logística — to a folder outside Git. It also writes the
  governance metadata beside it.
- It does **not publish**. Nothing it writes enters `site/` in this stage. The package goes to
  `site/package/` in a PR of its own, when a report page exists to open it: P01's at 2.5, the first
  publication at 2.10. The stage proves the package passes CI's `verify` by running `verify` on it
  locally (§8).
- It does **not** recompute a metric (rule 3 of `CLAUDE.md` §6). The control totals are checksums
  of the columns the package declares additive, not published figures (§7).
- It does **not** read inside the warehouse beyond `consumption` and the one relation of
  `governance` the login reads (PLAN §3.5). Oracles over the inner layers are the custodian's.

## 2. What exists, and what is new

| Part | Today | 2.4 |
|---|---|---|
| The read | `evidence/20261117/capture.sh` **[measured, M55, M59]**: `psql` in the warehouse's container, as `consumption_reader`, one `REPEATABLE READ READ ONLY` transaction, CSV out. It proves the login, the isolation and the provenance row, and leaves a fingerprint per view. It fixes the container's name and reads its rows as text | A Python reader with typed values, configured only by environment variables (§3) |
| The view contract | None. The columns and types are in the captures, the grain in the metadata package's `view_rules` (UQ-18) | `release/views.json`, pinned and reviewed in full (§4) |
| The report contract | `release/contract.json` describes three fixtures (N79) | The 16 reports, written from the view contract (§4.3) |
| The Parquet | DuckDB reads it in `verify` (N77) | DuckDB writes it and reads it back (§6) |
| The control totals | `{contract_version, report_version, rows, sums}`, recomputed in `verify` (N78) | Unchanged in format; the sum columns come from the view contract (§7) |
| The sealing | `envelope.encrypt_package` **[measured, 2.2a]** | Called as it is (§8) |
| The profiles | `release/profiles.json`: two profiles, three fixtures | Diretoria 16 reports, Logística P13 (PLAN §3.2) |
| The governance metadata | Read by `evidence/*/package_check.py` | Carried as JSON, checked against the view contract (§9) |

M59 measured what the read finds at the pin's models and data **[measured]**. It found 16 views and
226 columns: 46 `numeric` with no declared precision or scale, 44 `character varying`, 35 `integer`,
35 `bigint`, 23 `text`, 4 `boolean` and one `timestamp with time zone`
(`skus_below_reorder_point.last_movement_at`). The views run from 25 rows (`top_skus_by_revenue`)
to 5,775 (`inventory_turnover_by_sku_and_warehouse`), 14,244 in all.

## 3. The read

**Where it runs.** On the Owner's machine, inside a read window the Owner opens in
`mvp_eng_dados_2` (UQ-05). This repository starts no container and runs no command of that project
(`CLAUDE.md` §5).

**How it connects [planned].** A PostgreSQL client from Python connects to the host and port the
warehouse publishes. Everything comes from environment variables, so another environment is other
values (`CLAUDE.md` §5):

| Variable | What |
|---|---|
| `BICE_WAREHOUSE_HOST`, `BICE_WAREHOUSE_PORT`, `BICE_WAREHOUSE_DB` | Where the warehouse is |
| `BICE_WAREHOUSE_USER`, `BICE_WAREHOUSE_PASSWORD` | The exporter's login (N4); the password is never printed nor written |
| `ENG_DADOS_2_DIR` | The checkout of `mvp_eng_dados_2`, read only with `git show <pin>:<path>` (§9) |

The Owner sets them from that checkout's `.env`, whose keys hold the reader's login
(`WAREHOUSE_READER_USER`, `WAREHOUSE_READER_PASSWORD`) and the port (`WAREHOUSE_DB_PORT`)
**[measured, by key name only]**. Which client to use is question Q1 (§11).

**The transaction [planned].** One connection runs one transaction:
`BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY`, with a `statement_timeout`. Before any row is
read, the transaction checks four things, and refuses with a fixed code on any of them:

- `current_user` is the login the contract names;
- `transaction_isolation` is `repeatable read` and `transaction_read_only` is `on`;
- the login is a member of `analyst` and of nothing that can write. The read checks `pg_roles` and
  `pg_auth_members` for the login itself; the database's own refusal of writes is eng_dados'
  `test_acesso`, not repeated here;
- the views of `consumption` are exactly the 16 the contract lists, by name: a missing view and an
  extra one both refuse.

**The provenance [planned].** In the same transaction, before the views, the reader reads
`governance.warehouse_provenance`. It refuses unless the row is `verified` and its
`built_from_commit` is one the contract accepts. M59 found `bcc2d5c` **[measured]**, the commit
whose models and data `b0ef66e` carries (M61). A build from another commit refuses until the views
are captured and compared as M59 was and the contract is changed in a PR (PLAN §3.5, the pin). The
row is recorded in the package and in the evidence.

**The rows [planned].** Each view is read whole, in its contract's grain order, typed by the client:
`numeric` as an exact decimal, `timestamp with time zone` as an aware instant in UTC, `text` and
`varchar` as text, `integer` and `bigint` as integers, `boolean` as a boolean. Its schema is read
from `information_schema.columns` in the same transaction and compared with the contract before its
rows (§5). The transaction ends with `COMMIT` after the last view, and records `now()` at its start
as `read_at`.

**The fingerprint [planned].** For each view, the reader also computes M55's fingerprint inside the
transaction: the `md5` of its rows as text, in text order. When the provenance row is the one M59
read, every fingerprint must equal M59's. That is an oracle from outside the exporter: the exporter
read the state the earlier captures read, through another path.

## 4. The view contract

### 4.1 `release/views.json`

One declaration, reviewed in full (`CLAUDE.md` §5). For each of the 16 views, it records:

| Key | What | Source |
|---|---|---|
| `view` | The name in `consumption` | M59's capture |
| `report` | The question's code, P01–P16 | The metadata package's `questions`, at the pin |
| `version` | An integer, raised at every change | Here |
| `columns` | In order: name, PostgreSQL type and, for `numeric`, the precision and scale the export uses (§4.2); `nullable` | The capture; `nullable` from the measured nulls, reviewed |
| `grain` | The columns that identify a row: role `grain`, and `identity` where the view has it | The package's `view_rules` (UQ-18) |
| `additive` | The columns the totals sum | The package's `measures`, `additivity: additive` (§7) |
| `may_be_empty` | Whether zero rows is a valid read | Here; `false` for every view today |

The contract also carries the login's name, the pin and the accepted `built_from_commit` values.

A command, `export propose`, writes a **draft** of the file from a capture and the metadata package
at the pin. The draft is reviewed and committed. The exporter never writes the contract itself, and
an upstream change fails the export until a PR changes the contract (PLAN §3.5).

### 4.2 Decimals with no declared scale

All 46 `numeric` columns are declared without precision or scale in the views **[measured, M59]**.
Parquet's decimals and DuckDB's need both, up to 38 digits. The contract therefore declares them per
column. The export refuses a value it cannot write exactly at that precision and scale: one with
more fractional digits, or more integer digits. It never rounds. How the scale is chosen is
question Q2 (§11).

### 4.3 The report contract follows

`release/contract.json` (N79) is written from the view contract: the same columns and grain, the
types mapped to DuckDB's — `character varying` and `text` to `VARCHAR`, `integer` to `INTEGER`,
`bigint` to `BIGINT`, `numeric` to `DECIMAL(p,s)`, `boolean` to `BOOLEAN`, `timestamp with time
zone` to `TIMESTAMP WITH TIME ZONE` —, and `sums` from `additive`. The exporter and the gate read
the same file. A test proves the two contracts agree, so neither is edited alone.

## 5. The checks on every view

In this order, each refusing with a fixed code that names the view and the check, never a value
(as `package_gate.md` §7 does for CI):

1. **Schema**: names, order and types exactly as the contract says.
2. **Not empty**, unless `may_be_empty`.
3. **Nulls**: no null in a column that is not nullable.
4. **Decimals**: each value fits the column's declared precision and scale exactly (§4.2).
5. **Instants**: every `timestamp with time zone` value is an aware instant. It is written in UTC
   and read back as the same instant.
6. **Grain**: no two rows share the grain's columns; a null in a grain column refuses.
7. **Text**: valid UTF-8, with no NUL byte.

The empty and all-null cases are tested on the fake source (§10), since no view has them today.

## 6. The Parquet, and the round trip

**Writing [planned]** (N77). For each view, DuckDB for Python takes the typed rows into a table with
the report contract's types and writes Parquet with `COPY ... TO ... (FORMAT parquet)`. The writer's
options — compression, row group size — are fixed in the code.

**Reading back [planned].** The written Parquet is read back by DuckDB with `read_parquet` and by
the gate's own check (`contract.check_payload`). The rows read back are compared with the rows the
transaction read, typed, row by row, in grain order:

- equal count;
- for each row, every column equal as a typed value: decimals as exact decimals, instants as the
  same UTC instant, text byte for byte.

That comparison is what catches M19: two channel labels swapped keep every count and sum, and
diverge row by row (N76). It compares with the transaction's rows, not with a second read, so the
same snapshot is on both sides.

## 7. The control totals

The format is N78's: `{contract_version, report_version, rows, sums}`, with exact decimal strings.
`sums` covers the columns the package declares additive in `measures`. Their sum is a checksum the
gate recomputes. It is never shown: the report pages show the view's own values (M4, M20). A
non-additive column — an average, a rate, `order_count` across categories in P01 — is never
summed, not even as a checksum. A sum can check a package without being a figure, but declaring
it for a non-additive column would invite its use.

## 8. The package

`envelope.encrypt_package` seals the 16 payloads (totals and Parquet) for the profiles of
`release/profiles.json`: Diretoria all 16, Logística P13 (PLAN §3.2). The output folder holds the
manifest and the 16 envelopes, under content-hashed names. It also holds a `run.json` with:

- the pin;
- the provenance row;
- `read_at`;
- each view's row count and fingerprint;
- each payload's digest.

It holds no value of any row.

Then the exporter runs, locally, the checks CI runs: `release.verify` on a deploy folder built from
the output with today's inclusion list. That covers the whole decryption matrix with the public
passwords, the totals recomputed, the Parquet against the contract and the inspection for clear
values (`package_gate.md`), minus the comparison with the package live, which needs the site. A
package that `verify` refuses is not a package.

**The output folder** comes from a variable (`BICE_EXPORT_DIR`) and must be outside the repository's
tracked tree, or inside an ignored path. The exporter refuses a folder Git tracks.

## 9. The governance metadata

The metadata package of `mvp_eng_dados_2` at the pin — `docs/pacote_de_metadados.json`, format 1
(N87) — is read with `git show b0ef66e:docs/pacote_de_metadados.json`. The exporter:

- checks its `format` is 1 and its `provenance` names the pin;
- checks that every view of the contract is a relation of it, with the same columns. It also checks
  that the contract's `grain` and `additive` are what its `view_rules` and `measures` say;
- writes it unchanged, as `metadata.json`, beside the package, with its digest in `run.json`.

It is public by design (PLAN §3.4), so it is not encrypted. Stage 2.7 reads it.

## 10. The mutations, and the tests

`make check` cannot reach the warehouse, so the reader works over a **source** interface. In
production, the source is the PostgreSQL transaction. In tests, it is a fake that serves the same
shapes — the four transaction facts, the provenance row, `information_schema.columns` and typed rows
— from a small committed fixture of invented values with the 16 views' real columns. The fixture is
generated by a script, and a test proves the committed file is what the script writes.

Each mutation is one change to the fake, and each must stop at its check, with its code:

| Mutation | Stops at |
|---|---|
| M19: two labels swapped in one report's Parquet after writing | The round trip (§6) |
| A view missing; a view extra | The inventory (§3) |
| A column renamed, retyped, moved | Schema (§5.1) |
| A duplicated row; a null in a grain column | Grain (§5.6) |
| A null in a column that is not nullable | Nulls (§5.3) |
| A decimal with one fractional digit more than declared; one integer digit more | Decimals (§5.4) |
| A `timestamp with time zone` served naive | Instants (§5.5) |
| An empty view | Not empty (§5.2) |
| Isolation `read committed`; `transaction_read_only` off; another login | The transaction (§3) |
| Provenance not `verified`; built from a commit the contract does not accept | The provenance (§3) |
| A Parquet writer that rounds a decimal | The round trip (§6) |
| The view contract and the report contract disagree | The agreement test (§4.3) |
| The metadata package's grain differs from the contract's | §9 |
| The output folder tracked by Git | §8 |
| Clear data, a reused key or IV, a tampered manifest | `verify`, already proved in 2.2b, run here on the output (§8) |

**The live run**, in the read window, is not in `make check`. It writes its evidence to
`evidence/<date>/`: the transaction facts, the provenance row, each view's count and fingerprint
against M59's, each payload's digest, `verify`'s result and the time each phase took. It writes no
value.

## 11. Questions for the Owner

| # | Question | Recommended | Alternatives |
|---|---|---|---|
| Q1 | Which PostgreSQL client the exporter uses | **psycopg 3**, a new runtime dependency, pinned in `uv.lock`: typed values — `Decimal`, aware `datetime` —, one connection under our control, and `pg_hba` reached over the published port. It protects the typed round trip and fixes no container name | `psql` in the container, as `capture.sh` does: no new dependency, but every value crosses as text, typing moves into our parser, and the container's name is fixed. DuckDB's `postgres` extension: already a dependency, but it downloads an extension at run time and opens its own connections, so one snapshot for all 16 views is not ours to guarantee |
| Q2 | How the scale of the 46 unconstrained `numeric` columns is chosen | **Per column, from M59's measured maximum scale and integer digits, with headroom, declared in the contract and reviewed**: a value that outgrows it refuses loudly and the contract is changed in a PR | One wide type for all, such as `DECIMAL(38,10)`: no measurement, but it fixes a scale no view declares, and a value with more digits still refuses. Asking `mvp_eng_dados_2` to declare precision and scale in its views: the right owner, but it is a change there and a new pin |
| Q3 | Whether 2.4 writes the package into `site/package/` | **No**: the package stays outside Git until a page can open it (2.5), and 2.4 proves it with `verify` locally | Yes, in a PR at 2.4: the preview would then carry real ciphertext with fixture pages that cannot read it |

## 12. Not verified, and assumptions

- **[assumed]** psycopg 3 returns `numeric` as `Decimal` with every digit, and `timestamptz` as an
  aware `datetime`, through the published port. To be proved by the first live read.
- **[assumed]** The published port accepts the reader's login from the host. M55 connected from
  inside the container, over `127.0.0.1` there.
- **[assumed]** DuckDB 1.5.6 writes and reads `DECIMAL(p,s)` up to 38 digits and
  `TIMESTAMP WITH TIME ZONE` in Parquet with no loss. Tested on the fixture before any live read.
- **Not measured**: the run's time, and its memory with 14,244 rows (expected small); the size of
  the package.
- **Not measured**: the maximum scale and integer digits of each `numeric` column. They are read
  from the capture of M59 outside Git (`data/captures/`) when the contract's draft is written, and
  recorded in the evidence.
- Whether the views' grain under `view_rules` is unique in the data today. M56's compare checked
  repeated keys at `eb11709`, not at the pin's data, and the live run checks it again.

## 13. The order of the work

1. This plan, reviewed by Codex until no blocking finding is left; the Owner answers Q1–Q3.
2. The view contract's draft from M59's capture and the metadata package, reviewed in full; the
   report contract and the profiles written from it.
3. The source interface, the fake and its fixture; the checks of §5, the round trip of §6, the
   totals, the sealing and `verify` on the output, each mutation of §10 with its test, in
   `make check`.
4. Codex's review of the code.
5. The live run in the Owner's read window, its evidence committed.
