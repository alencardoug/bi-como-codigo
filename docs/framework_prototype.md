# The framework prototype — stage 2.3

> **What lives here:** how stage 2.3 compares the two framework candidates of N3 on the same P01
> page — the fixture both read, the page both build, the oracle that fails a candidate whose finished
> output carries clear report data, what is measured of each and under what conditions, the probes
> each candidate needs, how its dependencies are kept away from this machine's credentials, the
> order of the work — and, once it runs, the results the Owner chooses from.
>
> **What does not:** why there is a comparison and who chooses — [PLAN §1.2](../PLAN.md#12-the-decisions),
> N3, and [§7](../PLAN.md#7-what-is-still-decided-at-the-right-moment); the envelope the page opens —
> [`encryption_envelope.md`](encryption_envelope.md); the package-to-artifact gate whose `verify` is
> one half of the oracle here, its formats and its limits — [`package_gate.md`](package_gate.md); the
> complete P01 report, with its accessibility, narrow screens, themes and the partial-month and
> empty-slice rules in full — stage 2.5; real report data — stage 2.4.

| Field | Information |
|---|---|
| Date | 2026-11-20 — revision 2, answering round 1 of Codex's review (FPROTO-1-01 to -06). Revision 1, 2026-11-13, for that round |
| Author | Claude Code |
| Status | **Planned.** Nothing of it is built. P01's columns are read at eng_dados `f86b9fb`, tag `v2.0.0`; they are, in the same order, the ones M55 read at `eb11709` and M59 at `2bceb47`, and `b0ef66e`, the pin of 2.4–2.10 (N91), carries M59's views. The stage reads no warehouse data, so the pin does not reach it otherwise |

**[measured]** has output behind it; **[planned]** is intent; **[assumed]** is a premise about a
tool that the stage proves or refutes (§9).

---

## 1. What the stage decides, and what it does not

The criterion, from [PLAN §6.2](../PLAN.md#62-the-stages): *the same page in each candidate, with
what each cost and what was missing; the finished build output of each inspected — a candidate that
runs report queries over clear data at build time fails; you choose.*

- It **builds** one page twice and **measures** both (§6); it does not pick. The choice is the
  Owner's (N3, PLAN §7), recorded by the Owner as an ADR — the framework is a new component of the
  repository, listed as pending in the [decision record §3](adr/README.md#3-pending).
- It does **not** publish: nothing of it enters `site/`, `release/include.txt` or a preview. The
  prototypes live under `prototypes/framework/`, outside the inclusion list, and are built and
  served only on this machine.
- It does **not** read the warehouse. The data is an invented fixture with P01's columns (§2.1).
- It does **not** change the publishing gate. `release.verify` is called as it is; what this stage
  adds to it (§2.5.2) is the prototype's, and whether any of it joins the gate is decided with the
  framework, at 2.5.

## 2. The common ground

### 2.1 The fixture

P01 is the view `monthly_revenue_by_channel_and_category`
([eng_dados at `f86b9fb`](https://github.com/alencardoug/mvp_eng_dados_1/blob/f86b9fb/dbt/models/consumption/monthly_revenue_by_channel_and_category.sql)):
`year_month`, `year_number`, `month_number`, `sales_channel_name`, `channel_type`,
`root_category_name`, `category_name`, `order_count`, `unit_count`, `gross_revenue_amount`,
`discount_amount`, `net_revenue_amount`, at the grain `[year_month, sales_channel_name,
category_name]`. The fixture keeps those names, in that order, and invents every value
**[planned]**. Its shape is fixed; its values are drawn.

**The shape.**

- 13 consecutive months; 3 channels, `fixture_canal_a` and `fixture_canal_b` of one channel type and
  `fixture_canal_c` of another; 3 root categories, `fixture_raiz_1` to `_3`, with 2 categories each,
  `fixture_cat_1a` to `fixture_cat_3b`. A full month has 18 rows.
- **The gap, G**: `fixture_canal_c` has no row of `fixture_raiz_3` — neither of its categories — in
  the fifth month. Filtered on that channel, the page's summary has an empty cell there (§2.3).
- **The zero, Z**: `fixture_canal_b` has both rows of `fixture_raiz_2` in the seventh month, with
  units and gross revenue, and a discount equal to the gross revenue: `net_revenue_amount` is
  `0.00` on both. Filtered on that channel, the summary cell exists and is zero — the case the
  page must not confuse with G.
- **The partial month**: the last month has no row of `fixture_canal_c` — 12 rows instead of 18 —
  and smaller amounts. The page shows a fixed notice for it; the rule of M5 itself is 2.5's.
- 226 rows: 13 × 18, less the 2 of G and the 6 of the partial month.

**The values.** Drawn deterministically by `prototypes/framework/fixture.py` from a recorded seed,
with the control totals computed in Python with `decimal`, as `tests/site_fixture.py` does:

- amounts with two decimals, each distinct across the three amount columns and with at least three
  significant digits, at least ten of them with a fraction ending in `0` — so that the JavaScript
  spelling `1234.5` of `1234.50` is exercised (FPROTO-1-01);
- `order_count` and `unit_count` integers, each distinct across the fixture, with at least three
  significant digits; `order_count` differs from row to row, and **no sum of `order_count` over the
  rows of any summary cell, under any filter, equals a value the page displays** — the generator
  asserts it, so that a summary count invented by summing is told apart from a native one (§2.6);
- the calendar too: the 13 months are a window chosen so that its year and `year_month` spellings
  pass the draw below.

**The draw against the corpus.** `verify`'s inspection searches each eligible value as a byte
substring in every file of the output ([`package_gate.md` §6](package_gate.md)). A candidate's own
code — a bundle, the DuckDB WASM that Evidence ships — can hold a short integer by chance, and
that would be a false refusal by content. So each candidate is first built with a **decoy fixture**
of the same shape (§2.5.2), and every value the generator draws is rejected and redrawn while any
of its spellings, as `contract.needles` would make them, occurs in a non-package file of either
candidate's decoy output. The number of rejections, and any range the generator had to widen, are
recorded with the seed. The draw is sound only because the non-package output does not depend on
the fixture — which §2.5.2 proves for each build, and without which the candidate has failed
anyway.

**The coverage assertion.** Before any build, the harness computes `contract.needles` on the
fixture's values and asserts that every eligible number contributes each of its spellings and every
text of three characters or more contributes itself, with no public value excluding any — the
count is printed and compared with the one computed from the fixture alone (FPROTO-1-01).

The SQL types are written in a contract of the prototype's own, in the format of
`release/contract.json`, with the grain above and the sums on `unit_count` and the three amounts —
not on `order_count`, which is not additive across categories (M4). The repository's `release/`
is not touched.

### 2.2 The package

`prototypes/framework/fixture.py` seals the fixture with the envelope's producer
(`envelope.encrypt_package`) under a profiles declaration of the prototype with one profile,
Diretoria, with the showcase's public password (N22), entitled to P01. Round 1 of the review ran
the producer and `validate_manifest` on one profile, and on a profile with no report, and both pass
(FPROTO-1, its §4): Logística stays out — the access matrix is 2.6's —, and step 1 of §7 repeats
that run here. The package is written into each candidate's static folder by the harness, never
committed: like `site/package/`, its bytes change at every run.

Both pages open it with the same reader, `web/envelope.mjs`, imported as is: login derives the key,
unwraps the data key and returns the control totals and the Parquet; the Parquet is then registered
in a DuckDB-WASM instance and queried there. The envelope's reader is not re-implemented in either
candidate.

### 2.3 The page

The same page, in Portuguese, in both **[planned]**:

1. a login box with the Diretoria password; a wrong password shows that nothing opened;
2. after login, a filter by `sales_channel_name` — its values read from the data, with "todos" —
   and a month selector for the detail table;
3. a chart of `net_revenue_amount` by `year_month`, one series per `root_category_name`;
4. **the summary**: a table by `year_month` and `root_category_name` with `net_revenue_amount` and
   `unit_count`, summed from the rows of the filter. It has **no `order_count`**: its cells gather
   several native rows, and the view carries no order identities from which their distinct count
   could be rebuilt (M4; FPROTO-1-03);
5. **the detail**: a table at the view's own grain — channel and category, for the selected month
   and the filter — with `order_count`, `unit_count` and `net_revenue_amount` as they are in the
   rows, nothing summed. This is the only place `order_count` appears;
6. in the summary, a cell with no row under the filter says **"Sem vendas neste recorte."** — not
   `R$ 0,00`, not blank —, and a cell whose rows sum to zero shows `R$ 0,00`; the fixed notice
   **"Mês em curso: os números ainda vão mudar."** on the last month, which names no month;
7. a logout that drops the DuckDB tables and the decrypted buffers and returns to the login box.

Queries run only in the browser, after login. Number formatting is `pt-BR`. No text of the page,
fixed or generated before login, carries a fixture value.

### 2.4 The engine

DuckDB-WASM **1.32.0**, the last stable release on npm, of 2025-12-16 — `latest` points to a
development build, `1.33.1-dev57.0` — **[measured, M54]**. The own build loads it from jsDelivr,
pinned to that version, as PLAN §3.4 has it. Evidence brings its own: its browser engine,
`@evidence-dev/universal-sql` 3.0.1, asks for `^1.30.0` **[measured, M54]** and bundles it through
Vite, so it is served from the same origin as the page; the version its lockfile resolves is
recorded, and a difference from 1.32.0 is reported, not forced.

### 2.5 The oracle

A candidate's **finished build output** — the folder its build produces for a static host — is the
thing judged, together with what the page leaves in the browser (§2.5.3). The oracle has two halves,
and the candidate passes the criterion only if both do.

#### 2.5.1 The gate's own `verify`, and its harness

`bi_como_codigo.release.verify` is the function the publishing workflow runs before any upload
([`package_gate.md` §2](package_gate.md)); whatever is chosen will have to pass it at 2.5, so it
runs here unchanged. Its limits are its own document's: it reads bytes and searches spellings, so
a value that is compressed, encoded, escaped, written as a binary number or re-spelled passes it,
and its first refusal by form stops it before the inspection by content (FPROTO-1, its §4). Here
it is a necessary condition, never a sufficient one.

**The harness [planned]** (FPROTO-1-02). For each run, `prototypes/framework/harness.py` assembles a
root of its own, outside the candidate's folder:

```
<run>/root/release/contract.json       copied from prototypes/framework/release/
<run>/root/release/profiles.json       copied from prototypes/framework/release/
<run>/root/release/public_values.json  copied from prototypes/framework/release/ — {"about": …, "values": []}
<run>/root/release/include.txt         copied from prototypes/framework/<candidate>/release/
<run>/root/release/media_types.txt     copied from prototypes/framework/<candidate>/release/
<run>/output/                          the candidate's finished output, the package in it
```

and calls `release.verify(<run>/root, <run>/output, live=lambda: release.NO_LIVE)`: `verify` appends
`release/` to the root itself. The three shared declarations live once; the two lists are the
candidate's, in the gate's syntax — globs under `site/`, matched against the output's paths with the
prefix removed —; the formats are `package_gate.md`'s. A `release.Refused` is the candidate's result,
recorded with its message; **any other exception is `HARNESS_ERROR`**, recorded apart, and the run
is repeated after the harness is fixed — it is never written as a cost or a failure of the
candidate. Step 1 of §7 proves the harness before either candidate exists: a hand-made output with
the envelope, its manifest and an `index.html` passes; the same output with one fixture label in
`index.html` is refused with `clear_value`; a root missing `public_values.json` gives
`HARNESS_ERROR`, not a refusal.

#### 2.5.2 What this stage adds: the differential build and the carrier inspection

Both are code of the prototype, in `prototypes/framework/`; they run on every output, whatever
`verify` said, and before any setting of the candidate is changed (FPROTO-1-01).

**The differential build [planned].** The encrypted build cannot run a report query over clear data
by construction: it runs in a sandbox (§5) whose only fixture-derived files are the sealed package,
with neither the clear fixture nor the password in its files or environment — the harness checks
both before the build starts. The differential proves it of the output, carrier by carrier, without
having to know the carrier:

1. build the candidate with fixture X; build it again with X, from a clean folder — the files that
   differ are the build's **noise**;
2. build it with fixture Y, of the same shape and a different seed;
3. every file outside the package directory that differs between X and Y, and does not also differ
   between X and X, **depends on the data**: the candidate fails the criterion, with the file named;
4. a file in the noise is passed to the carrier inspection; one the inspection cannot fully decode
   is **inconclusive**.

A value carried compressed, base64, in Arrow, in a service worker or in a format nobody listed still
makes its file differ between X and Y. This is the bounded coverage argument of FPROTO-1-01: what
the build emits is shown independent of the data, instead of searched for every way data could be
spelled. Removing or re-encoding an emitted file does not escape it — the file still differs, or
its absence does.

**The carrier inspection [planned].** `prototypes/framework/inspect_output.py` reads a set of files
— an output, a noise file, the bodies and storage of §2.5.3 — and names the carrier of any fixture
value it finds. It is the half that tells the Owner *how* a candidate leaks, and the one that judges
what the differential cannot (noise, the browser). Its needles are the fixture's values **and the
results of the page's queries** — every summary and detail cell under every filter, from the oracle
of §2.6 —, since a build-time query emits results, not rows. For each file, recursively to a depth
of three:

| Layer | What is done |
|---|---|
| Decoders | gzip, zlib and raw deflate; brotli; zstd; base64, standard and URL-safe, on runs of 16 characters or more; hex on runs of 32 or more; percent-encoding; JSON and JavaScript string escapes; HTML entities — each decoded result is inspected again |
| Structured carriers | JSON, and Svelte's devalue as JSON-like text, parsed: every number compared **as a number** with the needles, so `1234.5` matches `1234.50`; Arrow IPC, stream and file, and Parquet, parsed with `pyarrow`: every cell compared as a value |
| Text | every text needle as a byte string; every amount with a fraction in each spelling of `contract.spellings` and in its shortest JavaScript spelling — integers are compared only inside structured carriers, where a match is a value and not a fragment of code |
| Binary numbers | every amount with a fraction as the 8 bytes of an IEEE 754 double, both byte orders, and as the 16 bytes of an Arrow `decimal128` at scale 2 |
| What remains | a binary file that is byte-identical to a file of the candidate's locked dependency tree, or identical between X and Y, is recorded and not inspected further; any other binary that no layer decodes is **inconclusive** |

Each finding carries its code — `INSPECT_TEXT`, `INSPECT_NUMBER`, `INSPECT_ARROW`, `INSPECT_PARQUET`,
`INSPECT_BINARY` — and the decoding path, never the value. The decoder list is a closed list:
a carrier outside it is not "clean", it is inconclusive or, at build time, caught by the
differential.

**The verdict of a run** is computed by one function, tested in step 1 of §7:

- **fails the criterion**: the differential finds a data-dependent file; or the inspection finds a
  value in any file of the output, in the noise or in the browser (§2.5.3); or `verify` refuses by
  content — a clear value, a Parquet or payload magic outside an envelope, a data key in the clear;
- **inconclusive**: no failure, and a file that neither half could judge. It is not a pass; it is
  reported with the file, and the candidate's result says "not established";
- **a cost**: none of the above, and `verify` refused by form — a file outside the inclusion list,
  an extension outside the media types, a source map or a `sourceMappingURL` comment, a second
  `manifest.json`. It is cleared by a setting of the candidate's build, never by changing `verify`;
  the setting is recorded, and the inclusion list and media types are the narrowest that cover the
  output, their length a measured cost (§6). A form refusal no setting clears means the candidate
  cannot go through the publishing workflow, and it fails on that, said apart from the criterion;
- **passes**: `verify` passes, the differential finds nothing, the inspection finds nothing, and
  nothing is inconclusive.

**Outputs are kept.** Every output is archived, as a tarball with its SHA-256, the moment its build
ends and before `verify` or any inspection — under `prototypes/framework/<candidate>/runs/`, ignored
by Git. A setting produces a new run; **the verdict of an earlier run of the encrypted route stands**:
if any of them failed the criterion, the candidate has failed it, whatever a later setting
removed. The content of an output is judged whether or not its form was refused, so a leak inside
a source map or a second manifest is a failure, not a form problem cleared by deleting the file.

#### 2.5.3 In the browser

The browser check of §2.6 also feeds the carrier inspection with what the page holds before
login, where nothing decrypted may exist: the body of every network response (through the DevTools
protocol), and the contents of CacheStorage, IndexedDB, `localStorage`, `sessionStorage` and the
scripts of any service worker. After logout, the storage is dumped and inspected again. A value
found in any of them fails the criterion, as a build-time one does: a framework that caches query
results in the browser carries clear data outside the envelope.

#### 2.5.4 The controls

No half of the oracle is trusted until it has failed something real, and each control is
independent — one leak, in one carrier, with nothing else in the output that could trip the check:

| Control | Built from | Expected |
|---|---|---|
| Clean | the candidate's encrypted output, X and Y | passes, both halves |
| Clear mode | the candidate's natural clear build, X and Y — Evidence with the fixture as a clear Parquet source; the own build with a page that fetches the clear Parquet | the differential names every data-dependent file, and the inspection names each carrier A1 found, each also copied **alone** into a clean output |
| One carrier each | the clean output plus one fixture-derived file, built for X and for Y: a label as text; an amount in `pt-BR`; an amount in its JavaScript spelling; Arrow IPC — for Evidence, a `prerendered_queries` file of its clear build; Parquet; gzip, brotli and base64 of a JSON of rows; JSON-escaped text; a base64 payload in a service worker | the differential names the file; the inspection names its carrier |
| Content behind form | a label in a `.map`; a label in a second `manifest.json` | `verify` refuses by form; the run's verdict is still **fails the criterion** |
| Carrier nobody listed | rows encrypted under a key the oracle does not hold | the differential names the file; the inspection says inconclusive; the verdict fails |
| Browser | a page that writes one result into CacheStorage and one into `localStorage` before login | the inspection of §2.5.3 names both |

The controls run first on hand-made outputs (step 1 of §7), then on each candidate's own clean
output, so that the carriers are the ones the candidate actually writes.

### 2.6 The browser check

A Node script drives headless Chrome through the DevTools protocol, as `m49` did, against each
finished output served on `127.0.0.1` (§2.7) **[planned]**. Its oracle is the same queries run by
Python's DuckDB over the clear fixture:

- logs in, waits for the tables, reads their cells from the DOM and compares them with the oracle —
  equal, cell by cell, as text in `pt-BR`;
- applies the filter on "todos", `fixture_canal_a`, `fixture_canal_b` and `fixture_canal_c`, and
  the month selector on the fifth and seventh months, and compares again;
- **G**: under `fixture_canal_c`, the summary cell of the fifth month and `fixture_raiz_3` reads
  exactly "Sem vendas neste recorte."; **Z**: under `fixture_canal_b`, the cell of the seventh month
  and `fixture_raiz_2` reads `R$ 0,00`; the notice of the last month is present (FPROTO-1-04);
- **`order_count`**: the detail cells equal the native values of the fixture; the summary has no
  count column, and no summary element holds any of the sums §2.1 made distinct (FPROTO-1-03);
- logs out, and checks that the tables are gone and that a query on the dropped table fails;
- records every network request: only the local origin and, for the own build, `cdn.jsdelivr.net`
  at the pinned paths.

**The check is proved to fail** (FPROTO-1-03, -04): its comparator runs again on altered copies of
the DOM it read — G's cell turned to `R$ 0,00`, G's notice blanked, Z's cell turned to the notice,
a summed count written into a summary cell — and must refuse each; and the own build is built once
from a fixture mutant whose G is filled with a zero row, and the check must refuse that page.

### 2.7 How the costs are measured

So that bytes and times describe the candidates and not the state of a cache (FPROTO-1-05)
**[planned]**:

- **Serving.** One local static server for both, written for the prototype: it sends
  `firebase.json`'s headers — `Cache-Control: no-cache` on every file —, and compresses text files
  with brotli or gzip as the request accepts, as Hosting does **[assumed]**. jsDelivr serves itself;
  its encoding is recorded as received.
- **Cold runs.** Five, each in a new Chrome process with a fresh, empty `--user-data-dir`: from
  navigation to the table, so that the engine's first fetch is inside.
- **Warm runs.** One priming load, then five reloads in the same profile, the HTTP cache on. Cold
  and warm are reported apart, never in one statistic.
- **Timer.** The same script, injected before any page script runs, in both: `t0` is the `submit`
  of the login form, `t1` the first moment every expected cell of the summary is present with its
  expected text. Login to table is `t1 − t0`, the PBKDF2 derivation of M49 inside; median and range
  per mode.
- **Bytes.** For every request, from the DevTools protocol: origin, `encodedDataLength`,
  `Content-Encoding`, status, and whether it came from the memory cache, the disk cache or a service
  worker. Totals until the login box and until the table, split by origin — the local origin is what
  Hosting would serve and count, `cdn.jsdelivr.net` is not — and, for each local file, its size raw
  and brotli-compressed.

Every number is kept with these conditions beside it, in the evidence of the stage.

## 3. Candidate A — Evidence

**Version.** `@evidence-dev/evidence` 40.1.8 with `@evidence-dev/core-components` 5.4.2, both of
2026-02-06 — nine months without a release on 2026-11-13 **[measured, M54]** —, on SvelteKit 2.8.4
and ECharts 5.6.0, installed with `npm ci --ignore-scripts` from a committed lockfile (§5).

**How it carries data [assumed, probe A1].** Evidence runs its *sources* at `npm run sources`, writes
their results as Parquet into its static folder, runs the page queries at build time to prerender
them — `@evidence-dev/universal-sql` 3.0.1 serialises each result as Arrow IPC under
`.svelte-kit/output/prerendered/dependencies/api/prerendered_queries/`, and the page's
`+layout.js` reads those files back in the browser —, and runs the queries again in the browser on
DuckDB-WASM. That is read from the pinned source by round 1 of the review
([`cache-duckdb.js`](https://cdn.jsdelivr.net/npm/@evidence-dev/universal-sql@3.0.1/src/cache-duckdb.js),
[`+layout.js`](https://cdn.jsdelivr.net/npm/@evidence-dev/evidence@40.1.8/template/src/pages/+layout.js)),
not run. Probe A1 builds the clear mode and lists every carrier the fixture's rows and results land
in — Parquet, the prerendered Arrow, values inlined into HTML, JSON or devalue, anything else —;
each becomes a control of §2.5.4 before the encrypted route is attempted.

**The encrypted route [planned].** No source holds data: the only source is empty, or absent if
Evidence allows. A Svelte component of the page fetches the manifest and the envelope, opens it with
`web/envelope.mjs` and loads the Parquet into Evidence's own DuckDB-WASM instance; the chart and the
tables are Evidence's components, fed by page queries over that table. Each step is a probe, in
this order:

| Probe | Question | If no |
|---|---|---|
| A6 | Does the build install and run with `npm ci --ignore-scripts` — run **first**, before any script of a dependency can run (FPROTO-1-06)? | The scripts it needs, by package, recorded from `npm query` and run alone with `npm rebuild <package>`, inside the sandbox |
| A1 | Where do the fixture's rows and results land in the clear mode? | — (it is a measurement) |
| A2 | Can page code reach Evidence's DuckDB-WASM instance through a public module, with no patch? | Through a patched module (`patch-package`) — a cost, recorded |
| A3 | Does the build succeed, and prerender no query result — no `prerendered_queries` file with rows —, when a page query names a table that exists only after login? | Queries moved from markdown into the component; Evidence's SQL blocks lost — "missing" |
| A4 | Do the page queries re-run when the table appears and when the filter or the month changes? | A manual refresh through the component — recorded |
| A5 | Do Evidence's chart and tables take the result of a query run by our own code? | Charts written by hand — Evidence reduced to a layout, recorded as "missing" |

A fork of Evidence is out of scope: if the page needs one, the candidate's result is "not possible
without a fork", with the probe that showed it.

## 4. Candidate B — a build of our own

**What it is [planned].** No framework and no bundler: a static HTML page and plain ES modules —
the envelope's reader, a small report runner, the page —, DuckDB-WASM 1.32.0 and the chart library
loaded from jsDelivr at pinned versions with subresource integrity where the loader allows it, and a
build step in Python that copies the files and names them by content hash (PLAN §3.4, "versions are
bound"). It installs nothing from npm.

**The report as one reviewable file.** P01 is declared in `p01.report.json`: its queries, its
filter and month selector, its two tables and its chart — the chart a **Vega-Lite** specification
(`vega` 6.4.0, `vega-lite` 6.5.0, `vega-embed` 7.3.0 **[measured, M54]**; Vega-Lite 6.5.0 asks for
`vega ^6.4.0`, read from the registry by round 1 of the review), rendered as SVG. Vega-Lite is
chosen because its specification is data, not code: the report file stays a text a reviewer reads
in a diff, as Evidence's markdown is, and it renders to SVG, which 2.5 needs for themes and a text
alternative. ECharts, Evidence's own library, would compare charts like for like but is configured
in JavaScript objects with callbacks; Observable Plot is code. The choice is the prototype's and is
the Owner's to overturn before the build starts (§8).

**What it must write that Evidence gives.** The layout, the filter and month controls, the tables
and their `pt-BR` formatting, the empty-state text, the loading state — each counted (§6).

## 5. Safety of the build

Pinning is not isolation: an exact lockfile still runs whatever its packages' scripts do, and
`env -i` empties the environment but leaves the filesystem — the home folder with its credentials,
the checkout, the publishing tools — within reach (FPROTO-1-06). So **[planned]**:

- Every npm package pinned, with its lockfile committed under the candidate's folder and installed by
  `npm ci --ignore-scripts`, always first (A6); a script found necessary is run alone, by package,
  and recorded. `node_modules/`, `.evidence/`, `runs/` and the build outputs are ignored by Git.
- **Installs and builds run in a sandbox**: `bubblewrap` (0.6.1 on this machine), in a work folder
  that is a copy of the candidate's sources plus `web/envelope.mjs` and the sealed package, bound
  read-write and the only thing writable; the system's `/usr` and the TLS and DNS files bound
  read-only; an empty `HOME` on a `tmpfs`; the real home folder, the checkout, `~/.config`, `~/.ssh`,
  the Codex and Docker sockets and folders **not bound at all**. The network is open for `npm ci`
  only, to reach the registry; the build runs with `--unshare-net`. The output is copied out of the
  work folder by the harness, outside the sandbox.
- **The sandbox is proved before its first use**: a probe run through the same wrapper stats — never
  reads — the real home folder, `~/.config/gcloud`, `~/.config/configstore`, `~/.ssh`, the checkout's
  `.git` and the Docker socket, and must get "no such file" for each; it stats a sentinel file the
  harness planted in this session's scratch folder, and must not find it; it tries to write outside
  the work folder, and must fail; with `--unshare-net`, it tries to reach the registry, and must
  fail. No real credential is read by the probe.
- What is left is written as it is: a dependency's code still runs with the network open during
  `npm ci` — with nothing of this machine's to send —, and a kernel or `bubblewrap` flaw is not
  defended against.
- No prototype runs in CI and none enters `make check`: each has its own target,
  `make prototype-own` and `make prototype-evidence`, which build in the sandbox, run both halves of
  the oracle and the browser check. The inspection's Python libraries — `pyarrow`, `brotli`,
  `zstandard` — go in a dependency group of their own, which `make check` does not install. `make
  check` keeps its time and its dependencies.
- The prototypes import `bi_como_codigo` and `web/envelope.mjs` as they are; they change neither.

## 6. What is measured of each

| Measure | How |
|---|---|
| The criterion | The verdict of §2.5.2 on every run of the encrypted route, with `verify`'s result, the differential's files and the inspection's findings; the controls of §2.5.4, each with its expected result |
| The page works | The browser check of §2.6: cells equal to the oracle after login, under each filter and month, G and Z told apart, `order_count` only native; logout leaves no table; the check's own refusals of the altered DOM and of the mutant |
| Lines we wrote | Per file, split into report declaration, glue and configuration |
| Dependencies | Packages in the lockfile; size of `node_modules`; time of `npm ci` from an empty cache; scripts that had to run (A6) |
| Build | Time; files and bytes of the finished output; the noise of §2.5.2 |
| The gate's lists | Lines of the inclusion list and extensions of the media types the output needs |
| First load | §2.7: bytes until the login box and until the table, cold, by origin, wire and raw |
| Login to table | §2.7: median and range of five cold runs and of five warm runs, apart |
| What was missing | Each probe answered "no", with its output, and each workaround |
| Upkeep | Latest release and its date; the licence |

What 2.5 owns — keyboard, focus, 360 px, themes, the M5 rule — is not measured here; a candidate that
plainly cannot reach one of them is reported as such, with the observation behind it.

## 7. The order of the work

1. **The ground, before either candidate [planned]**: the sandbox and its probe (§5); the fixture's
   shape and generator, with the coverage assertion and §2.1's distinctness assertions; the package,
   repeating the one-profile run; the harness, proved as §2.5.1 says; the verdict function, the
   differential and the inspection, with every control of §2.5.4 on hand-made outputs.
2. Candidate B, which sets the page and the browser check: a decoy build, the draw of the fixture
   against both decoys — for which Evidence's decoy is built here too, with no probe yet —, then the
   X, X and Y builds, the controls on its own clean output, the browser check and its proof.
3. Candidate A, probes A6, A1 and A2 to A5 in order; a "no" is recorded and the next probe runs
   where it still can; then its X, X and Y builds and its controls.
4. The measures of §6 under §2.7, in one sitting per candidate, on this machine.
5. The results written in §10, and the implementation handed to Codex with the `review` skill.
6. The Owner chooses; the ADR is the Owner's.

## 8. Choices taken in this plan

| Choice | Taken | Alternatives | Why |
|---|---|---|---|
| The fixture's shape | P01's real columns, invented values, with G, Z and the partial month named | 2.2b's three-column fixture | The page needs months, channels and categories to show what a framework costs; invented values keep "no report data before 2.4" |
| The fixture's values | Drawn against the candidates' decoy outputs | Fixed values | `verify` searches substrings; a fixed integer may be in a bundle by chance, and a false refusal by content would fail a candidate on nothing |
| The oracle | The gate's own `verify`, with a differential build and a carrier inspection of the prototype's own | `verify` alone; an inspection alone | `verify` is what will judge the chosen framework in the publishing workflow, but bytes-and-spellings cannot see a compressed, encoded or binary value (FPROTO-1-01); the differential covers what is emitted without listing carriers; the inspection names the carrier and judges the browser |
| Where `order_count` shows | Only in a detail table at the view's grain | In the summary, per row | No summary cell keeps the grain at which the count is defined (M4; FPROTO-1-03) |
| Isolation | `bubblewrap`, with no home folder, no checkout and no network at build | `env -i`; a container | `env -i` is not a sandbox (FPROTO-1-06); `bubblewrap` is on the machine and binds only what is named; Docker's daemon runs as root and is itself a credential |
| B's chart library | Vega-Lite, as SVG | ECharts; Observable Plot | §4 |
| B's loading | jsDelivr, pinned | Vendored copies | PLAN §3.4 already loads the engine from jsDelivr; vendoring is measured as a cost only if SRI cannot be applied |
| Where they live | `prototypes/framework/`, tracked, not published | A branch; a scratch folder | Codex reviews what was measured; the chosen one moves to `site/` in 2.5, the other stays as the record of the comparison |

## 9. Not verified, and assumptions

- **[assumed]** Evidence's data path as described in §3, read from its source by the reviewer, not
  run — probe A1 measures it.
- **[assumed]** that Evidence's prerendered pages hold no query results when no source holds data —
  A3, judged by the differential.
- **[assumed]** that both builds are deterministic enough for the differential: noise that covers a
  file the inspection cannot decode makes the result inconclusive, not a pass. If Evidence's noise
  covers its bundles, the result says so.
- **[assumed]** that DuckDB-WASM 1.32.0 from jsDelivr runs in headless Chrome from a page served on
  `127.0.0.1`, with its worker created from a blob of the CDN script.
- **[assumed]** that each candidate's output can hold the package as `verify` finds it: `_package`
  takes the one `manifest.json` of the whole folder, so a framework that writes a `manifest.json` of
  its own is refused by form. That is a cost of the candidate, with the setting that removes it —
  after the output that carried it was judged by content (§2.5.2); the gate is not changed for a
  prototype.
- **[assumed]** that the draw of §2.1 converges with integers of three significant digits against
  a 34 MB WASM; if not, the ranges widen, and the widening is recorded. What it means for real data
  at 2.5 — a real count of three digits that a bundle happens to hold — is a question for the gate
  then, not answered here.
- **[assumed]** that Hosting compresses text as the local server of §2.7 does; wire bytes from the
  local origin are an estimate of Hosting's, and raw bytes are reported beside them.
- **[assumed]** that `bubblewrap` 0.6.1 runs unprivileged on this kernel; the probe of §5 proves it
  or the plan comes back to the Owner.
- Not measured, and not in this stage: the latency on a phone, a slow network, browsers other than
  Chrome.

## 10. Results

**Pending** — written when §7's steps 1 to 4 have run.
