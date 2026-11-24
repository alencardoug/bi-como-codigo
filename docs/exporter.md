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
| Date | 2026-11-24 — revision 4: round 3, the last by N110 (EXP-3-01 to -08, two blocking), answered; the review is closed, with the limits of §14. Revision 3, `c51a993`, answered round 2 (EXP-2-01 to -12, eight blocking). Revision 2, `f190b7a`, answered round 1 (EXP-1-01 to -13, ten blocking) with the Owner's N105 to N109. Revision 1 is `ae8b684` |
| Author | Claude Code |
| Status | **Plan, reviewed: closed after round 3 of Codex's review (N110)** — 33 findings in three rounds, 20 blocking, all answered. Nothing of it is implemented. Its live run needs a read window the Owner opens ([UQ-05](upstream_questions.md#answers)) |

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
| `BICE_WAREHOUSE_SSLMODE` | libpq's `sslmode`, explicit |
| `ENG_DADOS_2_DIR` | The checkout of `mvp_eng_dados_2`, read only with `git` (§5) |
| `BICE_EXPORT_STAGING`, `BICE_EXPORT_DIR` | Where clear data may be written, and where the sealed result goes (§10) |

The Owner sets the warehouse variables from that checkout's own configuration. Before connecting,
the process removes **every** environment variable whose name starts with `PG` — `PGHOSTADDR`,
`PGTZ`, `PGOPTIONS`, `PGSERVICE`, `PGSERVICEFILE`, `PGPASSFILE`, `PGSSLROOTCERT` and the rest of
libpq's list. The connection then takes only explicit parameters: `host`, `port`, `dbname`, `user`,
`password`, `sslmode`, `options` empty and `application_name` fixed.

**TLS [planned].** libpq also reads files from the home directory by default: `~/.postgresql/root.crt`,
`root.crl`, `postgresql.crt` and `postgresql.key` (EXP-3-08). So the TLS inputs are explicit too:

- `sslcertmode=disable`, so no client certificate is ever sent. The exporter authenticates by
  password only;
- `sslrootcert` and `sslcrl` are set from `BICE_WAREHOUSE_SSLROOTCERT` and
  `BICE_WAREHOUSE_SSLCRL` when given. When not given, they point to a path inside the run
  directory that does not exist, so no file of the home directory is read;
- with `sslmode` `verify-ca` or `verify-full`, a root certificate must be given, or the run refuses
  before connecting.

The receipt records the `sslmode`, and whether a root certificate and a CRL were given, never their
contents. Against the warehouse on this machine's own port, `sslmode` is the Owner's choice.

**One transaction, once [planned].** One connection, opened with `autocommit` off and
`isolation_level = REPEATABLE READ`, `read_only = True`. Its first statement starts the transaction,
and every fact below is read inside it, so the snapshot is one. There is no retry and no second
connection: a failed statement, a failed `COMMIT` or a lost connection refuses the run. The
transaction ends with `COMMIT` after the last read.

**The facts checked before any row [planned]**, each refusing with its fixed code, in this order.
Each query must return exactly the rows expected, with non-null booleans: a missing row, a null or
an extra row refuses.

1. **The transaction**: `transaction_isolation` is `repeatable read` and `transaction_read_only` is
   `on`.
2. **The provenance**: `governance.warehouse_provenance` has exactly one row. It is `verified`, and
   its `built_from_commit`, `invocation_id` and `sequence` match **exactly one** entry of the
   contract's `accepted_builds` (§4.1). That entry is the build whose witness and policy the rest
   of the run uses. Today it is M59's: `bcc2d5c…`, `1cb3cd4e-…`, sequence 125. A new build — the
   same commit included — refuses until a PR adds its entry. The PR needs its views captured and
   compared, as M59 was (PLAN §3.5, the pin). The row is recorded as read.
3. **The login**: `session_user` and `current_user` are both the contract's login. A `SET ROLE` or
   a different login refuses.
4. **The roles**: the closure of the login's memberships, recursive over `pg_auth_members`, is
   exactly the contract's set — `analyst` today (N4). For each edge, `admin_option` is false and
   `inherit_option` and `set_option` are what the contract declares. For the login and every role
   reached, `pg_roles` shows no superuser, `CREATEROLE`, `CREATEDB`, `REPLICATION` or `BYPASSRLS`,
   and `rolcanlogin` is what the contract declares. The first live run measures the closure and
   its options. A difference refuses, and the contract changes only by a PR.
5. **The inventory**: every relation of `consumption` in `pg_class`, of any kind, read from the
   catalogue whatever the grants. It must be exactly the contract's 16 names, each of kind `v`. A
   missing view, an extra view or table — granted or not — or a view of another kind refuses. The
   16 OIDs found are what checks 6 and 7 use.
6. **The access**, for each of the 16 OIDs:
   - `has_table_privilege` gives `SELECT` and none of `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`,
     `REFERENCES`, `TRIGGER`;
   - `has_any_column_privilege` gives neither `INSERT` nor `UPDATE`, so a grant on one column is
     caught;
   - the owner (`relowner`) is neither the login nor a role the login is a member of, by
     `pg_has_role(login, relowner, 'MEMBER')`, so no ownership is reachable by inheritance or
     `SET ROLE`.

   On the schema, `has_schema_privilege` gives `USAGE` and not `CREATE`. That the database refuses
   every write elsewhere is eng_dados' own `test_acesso`, run by the custodian, and is not repeated
   here.
7. **The source schema**: for each OID, its columns from `pg_attribute` in `attnum` order, not
   dropped: name, type OID (`atttypid`) and modifier (`atttypmod`). They must equal the contract's
   source columns exactly, and the contract records that source modifier apart from the
   `DECIMAL(p,s)` the export writes (§4.1). A trailing column, a moved column or a changed modifier
   refuses, even on an empty view. **The baseline is read, not inferred** (EXP-3-02): M59's
   committed header has type names, not OIDs nor modifiers, and `varchar` and `timestamptz` carry
   modifiers M59 did not record. `export catalogue` runs checks 1 to 6 in the same kind of
   transaction, reads `pg_attribute` for the 16 views and no row, and writes the OIDs and
   modifiers into the draft of §4.4. The Owner reviews them, as every field of `views.json`.
8. **The text-form policy of the selected build**: the transaction runs `SET LOCAL` for `TimeZone`,
   `DateStyle`, `IntervalStyle` and `extra_float_digits` to the values that build's witness
   declares, and reads them back, so no role or database default can change how a value is written
   as text. `server_encoding` and `client_encoding` must be `UTF8`. The database's collation must
   equal the witness's: from `pg_database`, `datlocprovider`, `datcollate`, `datctype`,
   `daticulocale` and `daticurules`, and the **effective** version,
   `pg_database_collation_actual_version(oid)`, which must also equal the stored `datcollversion`.
   A library updated under a stored version is caught this way (EXP-3-03).

**The witness [planned].** Each accepted build carries a witness:

- its text-form policy: the four settings of check 8, and the collation;
- the 16 views' row counts and fingerprints, one entry per view, each view exactly once.

Every run computes the fingerprints inside its transaction, under that policy, with M55's exact
expression: `md5(coalesce(string_agg(t::text, E'\n' order by t::text), ''))` over
`consumption.<view> t`. Every count and fingerprint must equal the witness's. A missing entry, a
duplicate entry or one difference refuses, whatever the provenance row says.

M59's session settings were not recorded. The witness of `bcc2d5c` therefore declares the policy M59
is assumed to have run under: the warehouse's defaults as `psql` sees them inside the container
(§14). If the first authorized run matches all 16 fingerprints under it, that **reproduces M59's
hashes on this capture** under that policy. It does not prove which settings M59 historically had,
and the evidence says so. If any differs, the run refuses and writes nothing, and the build stays
refused under M59's witness.

**There is no replacement path** (EXP-3-01). M59's rows outside Git have no committed digest that
binds them to its fingerprints, so they cannot authenticate a replacement. Revision 3's
`export witness` is withdrawn. A refusal on the first run comes back to the Owner as a question:
- whether to accept a witness taken by the exporter itself for the same build, recorded as having
  no link to M59;
- or to ask `mvp_eng_dados_2` for a new build and capture it as M59 was.

**The rows [planned].** For each view, in the contract's order:

- `SELECT count(*)`, refused above the view's `max_rows` (§4.1) before any row is fetched;
- `SELECT <the contract's columns, quoted, in source order> FROM consumption.<view>`, with no
  `ORDER BY`: the comparison of §7 is by grain key, not by position;
- the result's own metadata, from psycopg's public result object — `cursor.pgresult.fname(i)`,
  `ftype(i)` and `fmod(i)`, by position — compared with the contract, independently of check 7,
  before any row is read. `cursor.description`'s `Column` does not expose the raw modifier
  (EXP-3-02);
- the rows **frozen** into the reference of §7, by the validated positions of the raw result,
  before any mapping to the writer's columns.

`now()` at the transaction's start is recorded as `read_at`.

## 4. The view contract

### 4.1 `release/views.json`

One declaration, reviewed in full (`CLAUDE.md` §5).

**For the whole contract:**
- `login`, and `roles`: the closure of §3 check 4, with each edge's options and each role's
  `rolcanlogin`;
- the pin, as the full 40-character commit;
- `metadata_blob`: the Git blob id of `docs/pacote_de_metadados.json` at the pin;
- `accepted_builds`: each with its provenance row and its witness (§3) — the text-form policy, the
  collation and the 16 counts and fingerprints.

**For each of the 16 views:**

| Key | What | Source |
|---|---|---|
| `view` | The name in `consumption` | M59's capture |
| `report` | The question's code, P01–P16 | The metadata package's `questions.<P>.view` (§5) |
| `version` | An integer, raised at every change | Here |
| `columns` | In source order: the name; the **source** type OID and modifier, as `pg_attribute` gives them; the **export** type — for `numeric`, the precision and scale of §4.2; `nullable`; for text, `max_length` | The capture and M59's profile |
| `grain` | The columns that identify a row: role `grain`, with `identity` where the view has it | `view_rules.<view>.columns` (UQ-18) |
| `max_rows` | The most rows the export accepts | M59's count, with headroom |
| `may_be_empty` | Whether zero rows is a valid read | `false` for every view today |

`nullable` is `true` for the 9 columns M59 found with nulls, and `false` elsewhere. A grain column
is never nullable. A null where the contract says `false` refuses (§6), and the contract changes
only by a PR.

**The loader is strict [planned].** `views.json` is read with duplicate keys refused, every key
required and typed, and no unknown key. Its bounds are checked: `max_rows` at least the witness's
count; `max_length` at least 1; a precision at most 18 and a scale at most the precision; a grain
naming existing, non-nullable columns; 16 views and 16 distinct codes; each accepted build with a
witness entry for each of the 16 views exactly once. A declaration that fails any of them refuses
before anything else runs.

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
runs the same comparison before it connects, over the whole report contract: inventory, columns,
types, `nullable`, grain, sums and versions. A hand edit to `contract.json`, or to a field of
`views.json` that the report contract derives from, fails both. The fields only the exporter reads
— the source OIDs and modifiers, `max_rows`, `may_be_empty`, `max_length`, the roles and the
accepted builds — do not reach `contract.json`. They are guarded by the strict loader of §4.1, not
by this comparison.

**The draft.** `export propose` writes a draft of `views.json` from a capture's committed output,
M59's profile, the metadata package and the source OIDs and modifiers `export catalogue` read
(§3 check 7), into the staging root's `drafts/` folder (§10). The draft is
reviewed, then committed by hand. The exporter never writes `views.json` itself.

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

1. **Schema**: the source schema (§3 check 7) and the result's description (§3, the rows), each
   against the contract, independently.
2. **Size**: at most `max_rows`, checked on `count(*)` before any row is fetched; not empty unless
   `may_be_empty`.
3. **Nulls**: none in a column that is not nullable — grain columns included, which are never
   nullable.
4. **Decimals**: finite, and fitting exactly (§4.3).
5. **Instants**: aware, and within the client's range (§4.3).
6. **Grain**: no two rows with the same grain key (§7's canonical key).
7. **Text**: no NUL and at most `max_length` characters. PostgreSQL's `text` cannot hold a NUL,
   and psycopg decodes UTF-8 strictly under `client_encoding = UTF8`. The check stays, because
   DuckDB and Parquet would carry a NUL silently.

The witness (§3) is compared after these checks, so that a mutation of one row stops at its own
check first.

## 7. The frozen reference, and the round trip

**The reference [planned].** Each row of the raw result is frozen, by the validated positions and
before any write, as a tuple of canonical values:

- decimals as the exact fixed-point string at the column's scale;
- integers as integers, booleans as booleans, text as text;
- instants as integer microseconds in UTC;
- null as null.

Its **grain key** is the tuple of the canonical values of the grain's columns. The reference is
held as a map from grain key to row: a key seen twice refuses (§6.6). Its digest, over the rows'
canonical JSON sorted by the key's canonical JSON, is recorded. Nothing downstream mutates it: the
writer receives a copy.

**Writing [planned]** (N77). DuckDB for Python, in a database file inside the private run directory
(§10), takes the copy through the bindings of §4.3 into a table of the report contract's types. It
writes Parquet with `COPY ... TO '<path>' (FORMAT parquet)` to a file in the same directory. The
writer's options — compression and row group size — are fixed in the code.

**Reading back [planned].** The locked DuckDB reads Parquet from a path, not from a bytes object or
a buffer (EXP-2-04, reproduced in round 2). So:

1. the written file is read into memory as bytes, the **retained buffer**, and its SHA-256
   recorded;
2. that buffer is written to a new file, opened exclusively in the same directory;
3. `read_parquet` reads that file, with the path bound as a parameter;
4. after the read, the file's bytes are compared with the retained buffer's digest.

The read-back selects every column in the contract's order — decimals cast to their exact text,
instants as `epoch_us` — and builds the same map from canonical grain key to row. It is compared
with the reference:

- the same count;
- the same set of keys, each key once on each side;
- for each key, every cell equal by the canonical comparator.

The comparison needs no ordering, so PostgreSQL's collation and DuckDB's can differ.

That is what catches M19: two channel labels swapped keep every count and sum, and diverge row by
row (N76; 761 rows in M19). The other side of the equality is the transaction's own result, frozen
by raw position. A value swapped between two same-type columns on the writer's side therefore fails
it too. `contract.check_payload` then runs on the retained buffer, as CI will: it checks the
contract, the bounds and the totals, but it does not compare rows. **Sealing takes the retained
buffer** and checks its digest once more.

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

`envelope.encrypt_package` seals the 16 payloads (totals and the retained Parquet) for the profiles
of `release/profiles.json`: Diretoria all 16, Logística P13. The result holds the manifest and the
16 envelopes, under content-hashed names, and the **receipt**, `run.json`.

**The receipt** has a fixed schema, read back strictly: every field required, typed and
allow-listed, and no free text from a driver or an exception. It holds no value of any row:

| Part | Fields |
|---|---|
| Identity | The pin, `metadata_blob` and the SHA-256 of the metadata; the receipt's schema version |
| The read | `read_at`; the provenance row; the metadata's own `provenance`, kept apart; the text-form policy and collation read back (§3 check 8); the `sslmode`, and whether a root certificate and a CRL were given |
| The facts | For each check of §3, its code and `passed`, with the non-sensitive values it compared: isolation, read-only, the two users, the role closure with its options, the 16 view names and kinds, the access booleans, the source schema's OIDs and modifiers |
| Per view | Row count; fingerprint; whether count and fingerprint equal the witness; the reference digest; the Parquet's SHA-256 |
| Per envelope | Its file name and SHA-256 |
| The candidate | The digest of the private candidate's deploy listing; each included file's path and SHA-256; the SHA-256 of each trusted declaration as the rehearsal read it — `views.json`, `contract.json`, `profiles.json`, `public_values.json`, `include.txt`, `media_types.txt`; `verify`'s result for each live mode run (§10), with which live it compared — `none` or the stand-in's digest; the collisions approved, by entry of `public_values.json` |
| Time | The duration of each phase: connect, facts, read, checks, write, read-back, seal, candidate |

`export evidence` reads the receipt strictly and refuses an incomplete or ill-typed one before it
writes anything to Git (§10). A change to a trusted declaration alone changes the receipt's input identity even
when the deploy listing's digest is unchanged, and a test proves it.

## 10. Where clear data goes, and what a refusal prints

**Where nothing may be written [planned].** Before any write, every destination is resolved with
`realpath` — the staging root, the run directory, the drafts folder, the result and its sibling
temporary directory. Each is checked by the filesystem alone, not by asking Git. A path is refused
when:

- it or any ancestor holds a `.git` entry, file or directory, so it is inside a worktree or a
  repository. That covers this repository, both eng_dados checkouts and any other worktree, and it
  does not depend on Git's discovery, which `GIT_DIR`, `GIT_CEILING_DIRECTORIES` or a dubious owner
  can change (EXP-2-06, reproduced in round 2);
- it lies under the resolved `ENG_DADOS_DIR`, `ENG_DADOS_2_DIR` or this repository, which is
  checked explicitly even without a `.git`;
- it holds a character outside `[A-Za-z0-9._/-]`. The gate interpolates its temporary path into SQL,
  and an apostrophe breaks it (EXP-2-07, reproduced in round 2). A safe path needs no change to the
  protected gate.

The sealed result, which is ciphertext, follows the same rule. It reaches `site/package/` only
later, by a copy the Owner commits in its own PR (§11).

**The private run directory [planned].** `BICE_EXPORT_STAGING` names an existing directory that
passes the rule above. Inside it, each run:

- takes an exclusive lock, so two runs never overlap;
- creates a fresh directory with `mkdtemp`, mode `0700`;
- changes the process's working directory to it.

Every clear byte is written there, and nowhere else:

- the DuckDB database file, with its `temp_directory` set inside the same directory;
- the Parquet files of §7;
- the gate's own files. The process's `TMPDIR` and `tempfile.tempdir` point there, so
  `contract.check_payload`'s temporary directory lands inside. The gate's in-memory DuckDB spills
  to `.tmp` under the working directory, which is the run directory (EXP-2-07). A test forces a
  spill under a small memory limit and finds every spilled file inside.

The run directory is removed when the run ends: on success, on a refusal, on an exception and on an
interrupt. A run killed outright leaves it in the staging root, outside every worktree. The next run
reports it and refuses until it is removed.

**The drafts [planned].** `export propose` writes its draft of `views.json` to
`<staging>/drafts/views.<UTC time>.json`, which outlives the run. The draft holds names, types,
scales and bounds, no report value. It is the Owner's to review and commit by hand. The command
refuses a destination that resolves to `release/` and leaves both trusted contracts byte for byte
as they were.

**The result.** Only the sealed package, `metadata.json` and the receipt leave the run directory.
They go to `BICE_EXPORT_DIR`, which must not exist yet: they are written into a sibling temporary
directory and renamed into place in one step.

**The private candidate (EXP-1-07, EXP-2-09).** In the run directory, the run assembles what the
candidate workflow would build:

- a copy of the working tree's `site/`, with the real package in place of `site/package/`;
- `release.build`, the same function CI calls, which takes `release/include.txt` into a deploy
  folder;
- the digest of every included file and of the trusted declarations, recorded in the receipt.

Then `release.verify` runs on it, unchanged, twice:

- with no package live;
- with a **stand-in for live**: the envelopes of `site/package/` at the commit being rehearsed. The
  invented fixture of §11 is the stand-in, so the comparison of package id, DEKs, IVs and salts is
  exercised, not skipped.

The receipt says which ran. CI still makes the authoritative comparison against what is actually
live, when stage 2.5's PR brings the real package.

**The collisions (N108, EXP-2-08).** `verify` stops at the first clear value and prints only its
code and file, as it must. So `export collisions` is a separate, Owner-local diagnostic. It uses
the gate's own matching — `contract.needles` and its spellings — over the **committed** bytes of
the included public files, read with `git show HEAD:<path>`, and over the profile labels of the
committed `release/profiles.json`, which `verify` searches in the manifest (N83). It does not read
the candidate's copy, nor the package's envelopes. It reports **every** hit. For each hit it gives:

- the canonical value, which is what `release/public_values.json` would list;
- the spelling found and the public file it was found in;
- the reports and columns holding the value.

It prints a value only when it is found in those committed public bytes or labels, so it shows nothing the
site does not already show. A value planted in the candidate's copy is not in them: it is not
printed, and `verify` refuses it. Its output goes to the terminal, never to Git. The Owner approves each entry, with
its reason, in a protected PR. Then `verify` passes with exactly those exemptions and still refuses
an unapproved value. An exempted value is not searched in any report, so a leak equal to it would
pass: each entry says so.

**What a refusal prints.** The command-line boundary catches every exception and prints:

- a fixed refusal code;
- the view and the check, where there is one;
- the exception's class name.

It never prints a message, a traceback, a value or the connection string: a driver's message can
hold a value or a password. There is no debug mode that prints more.

**The evidence in Git** is written by `export evidence` from the receipt's allow-listed fields
(§9), into `evidence/<date>/`, and holds no value.

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
`verify` under the same trusted declarations, with no live and against this invented fixture as
the stand-in for live. Round 2 checked offline that a 16-shape package verifies against the current
three-envelope fixture as live, with the migrated profiles (EXP-1-08's reassessment).

## 12. The mutations, and the tests

**The fake source.** `make check` cannot reach the warehouse. So the reader works over a small
connection interface: execute, fetch, the result's description, commit and close. In production,
psycopg implements it. In tests, a fake implements it and records every statement in order. The
fake is fed by a committed fixture of invented values with the 16 views' real columns. The fixture
carries its own catalogue rows, provenance row and witness, computed from its rows. A script
generates it, and a test proves the committed fixture is what the script writes.

**Two levels.**
- **Unit tests** exercise one check on its own input. They cover the fit, the comparator, the
  path rule, the strict loaders and the receipt's schema.
- **End-to-end tests** run the whole export over the fake, through the real writer, read-back,
  sealing and `verify`.

Every mutation is end to end unless the table says *unit*.

**The rule for each mutation.** It changes one thing. When the change also moves a downstream fact,
the fixture regenerates that fact, so the mutation reaches the check it is for. A row-count change,
for example, regenerates the witness, and an injected artifact file recomputes the manifest's
integrity data, as 2.2b's MUT-15 and key/IV tests do. Each mutation asserts its exact refusal code.
Each has a **positive control**: the same case unmutated passes, through the same path.

| Boundary | Mutation | Code at |
|---|---|---|
| The connection | The statements out of order; a failure injected at each statement in turn; a failed `COMMIT` | §3: refusal, with no further statement and no second connection |
| | A `PGHOSTADDR` or `PGOPTIONS` in the environment naming another endpoint or options | §3: removed before connecting; the fake sees only the explicit parameters |
| The facts | Isolation `read committed`; `transaction_read_only` off | §3 check 1 |
| | A text-form setting that, read back after `SET LOCAL`, differs; a collation field off the witness; the effective collation version drifting while the stored one stays; `client_encoding` not `UTF8`; and, passing, two accepted builds with different policies, each run under its own | §3 check 8 |
| | `session_user` or `current_user` other than the login, as after `SET ROLE` | §3 check 3 |
| | A role missing, extra or nested; `admin_option` true; `set_option` or `inherit_option` changed; a reached role with `CREATEROLE` | §3 check 4 |
| | A view missing; an extra view or table, granted or not; a view of another kind | §3 check 5 |
| | `SELECT` refused on one view; a table-level `INSERT`; a column-level `UPDATE`; a view owned by a role the login reaches; `CREATE` on the schema; `USAGE` refused | §3 check 6 |
| | A trailing column on an accepted empty view; a moved column; a `numeric` modifier changed | §3 check 7 |
| | A modifier changed in the result's metadata only, through the pinned psycopg adapter as well as the fake | The rows (§3), before mapping |
| | A `~/.postgresql/postgresql.crt` and `root.crt` present in a temporary home; `verify-full` with no root certificate given | §3, TLS: no client certificate sent, no home file read; refusal before connecting |
| | No provenance row; two rows; not `verified`; the same commit with another invocation; a row matching two accepted entries | §3 check 2 |
| | One fingerprint off; one count off; a witness missing one view; a witness with one view twice (*unit*, loader) | The witness (§3); the loader (§4.1) |
| The result | A column renamed, retyped or moved in the result's description | Schema (§6.1) |
| | Two same-type text columns swapped by position between the raw result and the writer, with the description intact | The round trip (§7) |
| The rows | `count(*)` over `max_rows`, with nothing fetched after it | Size (§6.2) |
| | An empty view; and an empty view declared `may_be_empty`, which passes through the writer | Size (§6.2) |
| | A null where not nullable; a null in a grain column; and an all-null nullable column with a populated grain, which passes | Nulls (§6.3) |
| | A decimal one fractional digit or one integer digit beyond its type; `NaN`; `Infinity`; a nonzero digit at scale 38, refused before any binding; and, passing through the writer: a value exactly at its precision, negative zero, and a long spelling whose extra digits are only trailing zeros, such as `0.00123000000000000000000000000000000000`, written as `0.00123` | Decimals (§6.4) |
| | A naive instant; PostgreSQL `infinity`; and, passing: two instants with the same wall time and different offsets, microsecond precision | Instants (§6.5) |
| | A duplicated grain key | Grain (§6.6) |
| | A NUL; a text one character over `max_length`; and, passing, a text exactly at it, multibyte | Text (§6.7) |
| The write | M19: two labels swapped in the Parquet file between write and the retained buffer; a writer that rounds a decimal; a writer that drops a row | The round trip (§7) |
| | The retained buffer replaced after read-back and before sealing; the read-back file altered after the read | The seal's digest check; the read-back's digest check (§7) |
| | Accented, multi-column grain keys whose rows come in different orders on the two sides, which passes | The round trip (§7) |
| The metadata | A swapped report code in both local contracts; a missing question; a grain role missing; `format` 2; a column name added in `view_rules`; another blob at the pin | §5 |
| The declarations | `contract.json` edited by hand; `views.json` edited in a generated field without regenerating | §4.4, in `make check` and before connecting |
| | `views.json` with an unknown key, a duplicate key, `max_rows` below the witness, a precision over 18, a nullable grain column (*unit*) | The loader (§4.1) |
| | `export propose` pointed at `release/`; and a proposal that succeeds, whose draft is found in `drafts/` after exit, both contracts unchanged | §10 |
| The paths | Staging under a `.git` ancestor, with `GIT_CEILING_DIRECTORIES` set; staging reached through a symlink into a worktree; staging or result in an eng_dados checkout, ignored there; a path with an apostrophe; an existing destination; a leftover run directory; an interrupt mid-run; and, passing, an external path (*unit* for the rule, end to end for the leftover and the interrupt) | §10 |
| | A spill forced by a small memory limit, in the exporter and in the gate | §10: every spilled file inside the run directory, none left after |
| The output | An exception whose message holds an invented value or password | §10: neither printed |
| | A receipt missing a field, or with a field of the wrong type (*unit*) | `export evidence`, before any write |
| The candidate | A clear value injected into an included file; a tampered manifest; a reused key or IV; mismatched totals (MUT-15) | `verify` on the private candidate (§10), with 2.2b's mutations on the migrated fixture |
| | The candidate resealed with the stand-in's package id and other valid bytes; a fresh id with a DEK reused from the stand-in; and, passing, a fresh id with fresh material | `verify`'s live predicates (§10): `package_id_reused`, `dek_reused` |
| | Two collisions, one through a Brazilian spelling, and one equal to a committed profile label; and an unrelated clear value planted in a candidate file, and a label planted in the candidate's manifest | `export collisions` lists the three collisions, and neither planted value is printed. `verify` passes with the three approved and refuses each planted value |

**The live run**, in the read window, is not in `make check`. It writes its evidence with
`export evidence`, from the receipt of §9: the facts, the witness comparison, the digests, the
candidate's results and the times. It writes no value.

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
- **[assumed]** M59 ran under the warehouse's defaults as `psql` sees them inside the container.
  Its settings were not recorded. The witness declares that policy. The first run either
  reproduces all 16 hashes under it, or refuses, and the refusal comes back to the Owner as a
  question (§3). There is no automatic replacement.
- **[assumed]** psycopg's `cursor.pgresult` gives each result column's type OID and modifier
  (`ftype`, `fmod`), PostgreSQL 16's `pg_auth_members` has `inherit_option` and `set_option`, and
  `pg_database` has `daticulocale` and `daticurules`. The fake encodes them, and the first live run
  proves them.
- **[assumed]** libpq 16 accepts `sslcertmode=disable`, and a nonexistent `sslrootcert` or `sslcrl`
  path makes it read no home file with `sslmode` `prefer` or `require`. A test proves it in a
  temporary home (§12).
- **[assumed]** The gate's in-memory DuckDB spills only under the working directory's `.tmp`. Round 2
  observed that default with a forced spill. The spill test of §12 proves it for the gate's own
  connection.
- **Not measured**: the closure of the login's roles and their options (§3 check 4), measured by the
  first live run; the run's time and memory; the package's size; whether anything spills on M59's
  size.
- **Not measured**: which honest values collide with public text beyond the year 2026, found by the
  first private candidate (§10).
- M59's profile holds for its rows. The live run checks every rule again on the rows it reads.

**Declared limits, from the review's close (N110).** Round 3 listed these as remaining. They are
carried to the review of the code and to the first authorized run, not settled by this plan:

- **To the first authorized run**: the catalogue and wire baselines, host connectivity, the role
  options, the witness policy, memory, elapsed time, the package's size and the real public
  collisions.
- **To the review of the code (§12)**: the real spill and interrupt cleanup; the bound-path byte
  substitutions; M19; all-null and empty views; signed zero, NaN and both infinities; timestamp
  folds; NUL and multibyte text limits. Round 2's and round 3's probes covered selected boundaries
  on invented data only.
- **To stage 2.5 and CI**: the rehearsal compares with a fixture as stand-in. The authoritative live
  package and the artifact-to-live binding stay there. So do the gate's declared substring and
  spelling limits, and the effect of each value exempted under N108.
- **To the implementation**: private copy semantics, absolute paths after the change of working
  directory, and paths that change after they were validated. Round 3 showed no supported path
  escaping the guard.

## 15. The order of the work

1. This plan, reviewed by Codex; the review closes after round 3, of regressions only (N110).
2. `export catalogue` in a first, short read window (§3 check 7), reading the source OIDs and
   modifiers and no row; then `release/views.json` from `export propose`'s draft, reviewed in full; the generated
   `release/contract.json`; `release/profiles.json`; the invented fixture of the 16 shapes. All in
   the protected PR of §11, with the code below.
3. The connection interface, the fake and its fixture; the facts of §3, the checks of §6, the
   reference and round trip of §7, the totals, the sealing, the paths and output of §10, and each
   mutation of §12 with its test, in `make check`.
4. Codex's review of the code; then the Owner's review of the protected PR.
5. The live run in the Owner's read window: the private candidate, the collisions approved in a
   protected PR, and the evidence committed.
