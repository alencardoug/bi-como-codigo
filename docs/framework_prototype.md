# The framework prototype — stage 2.3

> **What lives here:** how stage 2.3 compares the two framework candidates of N3 on the same P01
> page — the fixture both read, the page both build, the oracle that fails a candidate whose finished
> output carries clear report data, what is measured of each, the probes each candidate needs, the
> order of the work — and, once it runs, the results the Owner chooses from.
>
> **What does not:** why there is a comparison and who chooses — [PLAN §1.2](../PLAN.md#12-the-decisions),
> N3, and [§7](../PLAN.md#7-what-is-still-decided-at-the-right-moment); the envelope the page opens —
> [`encryption_envelope.md`](encryption_envelope.md); the package-to-artifact gate whose `verify` is
> the oracle here — [`package_gate.md`](package_gate.md); the complete P01 report, with its
> accessibility, narrow screens, themes and the partial-month and empty-slice rules in full — stage
> 2.5; real report data — stage 2.4.

| Field | Information |
|---|---|
| Date | 2026-11-13 — revision 1, for Codex's review |
| Author | Claude Code |
| Status | **Planned.** Nothing of it is built. P01's columns are read at eng_dados `f86b9fb`, tag `v2.0.0`; the stage reads no warehouse data, so the pin of 2.4–2.10 on `mvp_eng_dados_2` (N85) does not reach it |

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

## 2. The common ground

### 2.1 The fixture

P01 is the view `monthly_revenue_by_channel_and_category`
([eng_dados at `f86b9fb`](https://github.com/alencardoug/mvp_eng_dados_1/blob/f86b9fb/dbt/models/consumption/monthly_revenue_by_channel_and_category.sql)):
`year_month`, `year_number`, `month_number`, `sales_channel_name`, `channel_type`,
`root_category_name`, `category_name`, `order_count`, `unit_count`, `gross_revenue_amount`,
`discount_amount`, `net_revenue_amount`. The fixture keeps those names, in that order, and invents
every value **[planned]**:

- 13 months, `2025-11` to `2026-11`; 3 channels (`fixture_canal_a` to `_c`, two channel types); 3
  root categories with 2 categories each — at most 234 rows;
- one channel × category with no row in one month, so that a filter can produce an **empty slice**;
- the last month with fewer rows and smaller amounts, standing for a **partial month**; the prototype
  shows a fixed notice for it, and the rule of M5 itself is 2.5's;
- amounts with two decimals and at least three significant digits, each distinct, so that the value
  inspection of [`package_gate.md` §6](package_gate.md) has a needle for every one (N81) — a fixture
  of round numbers would let a leaking candidate pass;
- generated deterministically by `prototypes/framework/fixture.py`, from a fixed seed, with its
  control totals computed in Python with `decimal`, as `tests/site_fixture.py` does.

The SQL types are written in a contract of the prototype's own, `prototypes/framework/release/contract.json`,
in the format of `release/contract.json`, with the grain
`[year_month, sales_channel_name, category_name]` and the sums on `unit_count` and the three
amounts — not on `order_count`, which is not additive across categories (M4). The repository's
`release/` is not touched.

### 2.2 The package

`prototypes/framework/fixture.py` seals the fixture with the envelope's producer
(`envelope.encrypt_package`) under a profiles declaration of the prototype, `prototypes/framework/release/profiles.json`:
Diretoria, with the showcase's public password (N22), entitled to P01. Logística is left out — the
access matrix is 2.6's —, unless the producer refuses a declaration with one profile, in which case
Logística is declared entitled to P01 too, and the plan says so. The package is written into each
candidate's static folder by the build, never committed: like `site/package/`, its bytes change at
every run.

Both pages open it with the same reader, `web/envelope.mjs`, imported as is: login derives the key,
unwraps the data key and returns the control totals and the Parquet; the Parquet is then registered
in a DuckDB-WASM instance and queried there. The envelope's reader is not re-implemented in either
candidate.

### 2.3 The page

The same page, in Portuguese, in both **[planned]**:

1. a login box with the Diretoria password; a wrong password shows that nothing opened;
2. after login, a filter by `sales_channel_name` — its values read from the data, with "todos" —;
3. a chart of `net_revenue_amount` by `year_month`, one series per `root_category_name`;
4. a table by `year_month` and `root_category_name` with `net_revenue_amount` and `unit_count`,
   summed from the rows of the filter, and `order_count` shown per row and **never summed** across
   categories (M4) — a total row carries no `order_count`;
5. the empty slice said in words when the filter leaves no row for a cell; the fixed notice on the
   last month;
6. a logout that drops the DuckDB tables and the decrypted buffers and returns to the login box.

Queries run only in the browser, after login. Number formatting is `pt-BR`.

### 2.4 The engine

DuckDB-WASM **1.32.0**, the last stable release on npm, of 2025-12-16 — `latest` points to a
development build, `1.33.1-dev57.0` — **[measured, M54]**. The own build loads it from jsDelivr,
pinned to that version, as PLAN §3.4 has it. Evidence brings its own: its browser engine,
`@evidence-dev/universal-sql` 3.0.1, asks for `^1.30.0` **[measured, M54]**; the version its lockfile
resolves is recorded, and a difference from 1.32.0 is reported, not forced.

### 2.5 The oracle: the gate's own `verify`

A candidate's **finished build output** — the folder its build produces for a static host — is
judged by `bi_como_codigo.release.verify`, the function the publishing workflow runs before any
upload ([`package_gate.md` §2](package_gate.md)), with `live` returning `NO_LIVE` and a root of the
prototype's own, `prototypes/framework/<candidate>/release/`, holding the prototype's contract and
profiles and that candidate's inclusion list and media types. `verify` refuses a clear value of the
fixture outside the envelope, a Parquet or payload magic outside an envelope, a data key in the
clear, a source map, a file outside the inclusion list and an extension outside the media types.

- **A refusal by content fails the candidate on the criterion**: a clear value, a Parquet or payload
  magic outside an envelope, a data key in the clear. No setting or rework turns that result into
  a pass within the stage; it is reported with the refusal's code.
- **A refusal by form is a cost**: a file outside the inclusion list, an extension outside the media
  types, a source map or a `sourceMappingURL` comment, a second `manifest.json`. Each is cleared by a
  setting of the candidate's build — never by changing `verify` —, and the setting is recorded; the
  inclusion list and media types are the narrowest that cover the output, and their length is a
  measured cost (§6). A form refusal that no setting clears means the candidate cannot go through
  the publishing workflow, and it fails on that, said apart from the criterion.
- **Counter-proof, per candidate [planned]:** each candidate is also built in its natural clear mode
  — Evidence with the fixture as a clear Parquet source; the own build with a page that fetches the
  clear Parquet —, and `verify` must refuse that output on the inspection by content, not on the
  inclusion list. It proves the oracle sees each candidate's way of carrying data, before its
  "pass" on the encrypted build means anything.

### 2.6 The browser check

A Node script drives headless Chrome through the DevTools protocol, as `m49` did, against each
finished output served by a local static server on `127.0.0.1` **[planned]**:

- logs in, waits for the table, reads its cells from the DOM and compares them with the same query
  run by Python's DuckDB over the clear fixture — equal, cell by cell, as text in `pt-BR`;
- applies the filter on one channel and on the empty slice, and compares again;
- logs out, and checks that the table is gone and that a query on the dropped table fails;
- records every network request: only the local origin and, for the own build, `cdn.jsdelivr.net`
  at the pinned paths;
- times login-to-table five times per candidate, after the PBKDF2 derivation that M49 measured.

## 3. Candidate A — Evidence

**Version.** `@evidence-dev/evidence` 40.1.8 with `@evidence-dev/core-components` 5.4.2, both of
2026-02-06 — nine months without a release on 2026-11-13 **[measured, M54]** —, on SvelteKit 2.8.4
and ECharts 5.6.0, installed with `npm ci` from a committed lockfile.

**How it carries data [assumed, probe A1].** Evidence runs its *sources* at `npm run sources`, writes
their results as Parquet into its static folder, prerenders the pages at `npm run build` and runs
the page queries in the browser on DuckDB-WASM. Probe A1 builds the clear counter-proof and records
where the fixture's rows land in the output — Parquet under the static folder, values inlined into
the prerendered HTML or JSON — before the encrypted route is attempted.

**The encrypted route [planned].** No source holds data: the only source is empty, or absent if
Evidence allows. A Svelte component of the page fetches the manifest and the envelope, opens it with
`web/envelope.mjs` and loads the Parquet into Evidence's own DuckDB-WASM instance; the chart and the
table are Evidence's components, fed by page queries over that table. Each step is a probe:

| Probe | Question | If no |
|---|---|---|
| A2 | Can page code reach Evidence's DuckDB-WASM instance through a public module, with no patch? | Through a patched module (`patch-package`) — a cost, recorded |
| A3 | Does the build succeed, and prerender nothing, when a page query names a table that exists only after login? | Queries moved from markdown into the component; Evidence's SQL blocks lost — "missing" |
| A4 | Do the page queries re-run when the table appears and when the filter changes? | A manual refresh through the component — recorded |
| A5 | Do Evidence's chart and table take the result of a query run by our own code? | Charts written by hand — Evidence reduced to a layout, recorded as "missing" |
| A6 | Does the build install and run with `npm ci --ignore-scripts`? | The scripts it needs, by package, recorded |

A fork of Evidence is out of scope: if the page needs one, the candidate's result is "not possible
without a fork", with the probe that showed it.

## 4. Candidate B — a build of our own

**What it is [planned].** No framework and no bundler: a static HTML page and plain ES modules —
the envelope's reader, a small report runner, the page —, DuckDB-WASM 1.32.0 and the chart library
loaded from jsDelivr at pinned versions with subresource integrity where the loader allows it, and a
build step in Python that copies the files and names them by content hash (PLAN §3.4, "versions are
bound").

**The report as one reviewable file.** P01 is declared in `p01.report.json`: its queries, its
filter, its table columns and its chart — the chart a **Vega-Lite** specification (`vega` 6.4.0,
`vega-lite` 6.5.0, `vega-embed` 7.3.0 **[measured, M54]**), rendered as SVG. Vega-Lite is chosen
because its specification is data, not code: the report file stays a text a reviewer reads in a
diff, as Evidence's markdown is, and it renders to SVG, which 2.5 needs for themes and a text
alternative. ECharts, Evidence's own library, would compare charts like for like but is configured
in JavaScript objects with callbacks; Observable Plot is code. The choice is the prototype's and is
the Owner's to overturn before the build starts (§8).

**What it must write that Evidence gives.** The layout, the filter control, the table and its
`pt-BR` formatting, the empty-state text, the loading state — each counted (§6).

## 5. Safety of the build

- Every npm package pinned, with its lockfile committed under the candidate's folder and installed by
  `npm ci`; `node_modules/`, `.evidence/` and the build outputs ignored by Git.
- Installs and builds run with no GitHub, Google or Firebase credential in their environment:
  `env -i` with `HOME`, `PATH` and the npm cache only.
- No prototype runs in CI and none enters `make check`: each has its own target,
  `make prototype-own` and `make prototype-evidence`, which build, run `verify` on the output and
  run the browser check. `make check` keeps its time and its dependencies.
- The prototypes import `bi_como_codigo` and `web/envelope.mjs` as they are; they change neither.

## 6. What is measured of each

| Measure | How |
|---|---|
| The criterion | `verify` on the encrypted build: passes, or the refusal's code; the counter-proof refused by content (§2.5) |
| The page works | The browser check of §2.6: cells equal to the oracle after login, after the filter and on the empty slice; logout leaves no table |
| Lines we wrote | Per file, split into report declaration, glue and configuration |
| Dependencies | Packages in the lockfile; size of `node_modules`; time of `npm ci` from an empty cache; scripts that had to run (A6) |
| Build | Time; files and bytes of the finished output |
| The gate's lists | Lines of the inclusion list and extensions of the media types the output needs |
| First load | Bytes transferred until the login box, and until the table, from the network log |
| Login to table | Median and range of five runs |
| What was missing | Each probe answered "no", with its output, and each workaround |
| Upkeep | Latest release and its date; the licence |

What 2.5 owns — keyboard, focus, 360 px, themes, the M5 rule — is not measured here; a candidate that
plainly cannot reach one of them is reported as such, with the observation behind it.

## 7. The order of the work

1. The fixture, the package and the oracle's harness — `verify` on a prototype root —, with the
   counter-proof mechanics proved on a hand-made folder holding a clear value. **[planned]**
2. Candidate B, which sets the page and the browser check.
3. Candidate A, probes A1 to A6 in order; a "no" is recorded and the next probe runs where it still
   can.
4. The measures of §6, in one sitting per candidate, on this machine.
5. The results written in §10, and the implementation handed to Codex with the `review` skill.
6. The Owner chooses; the ADR is the Owner's.

## 8. Choices taken in this plan

| Choice | Taken | Alternatives | Why |
|---|---|---|---|
| The fixture's shape | P01's real columns, invented values | 2.2b's three-column fixture | The page needs months, channels and categories to show what a framework costs; invented values keep "no report data before 2.4" |
| The oracle | The gate's own `verify` on the finished output | A search written for 2.3 | The same function that will judge the chosen framework's output in the publishing workflow; a candidate that passes here passes there |
| B's chart library | Vega-Lite, as SVG | ECharts; Observable Plot | §4 |
| B's loading | jsDelivr, pinned | Vendored copies | PLAN §3.4 already loads the engine from jsDelivr; vendoring is measured as a cost only if SRI cannot be applied |
| Where they live | `prototypes/framework/`, tracked, not published | A branch; a scratch folder | Codex reviews what was measured; the chosen one moves to `site/` in 2.5, the other stays as the record of the comparison |

## 9. Not verified, and assumptions

- **[assumed]** Evidence's data path as described in §3 — probe A1 measures it.
- **[assumed]** that Evidence's prerendered pages hold no query results when no source holds data —
  A3.
- **[assumed]** that DuckDB-WASM 1.32.0 from jsDelivr runs in headless Chrome from a page served on
  `127.0.0.1`, with its worker created from a blob of the CDN script.
- **[assumed]** that each candidate's output can hold the package as `verify` finds it: `_package`
  takes the one `manifest.json` of the whole folder, so a framework that writes a `manifest.json` of
  its own — a web-app manifest, a bundler's — is refused before any inspection. That is recorded as
  a cost of the candidate, with the setting that removes it; the gate is not changed for a
  prototype.
- **[assumed]** that the value inspection's needles cover the fixture, given §2.1's amounts.
- Not measured, and not in this stage: the latency on a phone, a slow network, browsers other than
  Chrome.

## 10. Results

**Pending** — written when §7's steps 1 to 4 have run.
