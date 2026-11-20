# The framework prototype — stage 2.3

> **What lives here:** how stage 2.3 compares the two framework candidates of N3 on the same P01
> page — the fixture both read, the page both build, the oracle that fails a candidate whose finished
> output or browser state carries clear report data, what is measured of each and under what
> conditions, the probes each candidate needs, how its dependencies are kept away from this
> machine's credentials and from the fixture, the order of the work — and, once it runs, the results
> the Owner chooses from.
>
> **What does not:** why there is a comparison and who chooses — [PLAN §1.2](../PLAN.md#12-the-decisions),
> N3, and [§7](../PLAN.md#7-what-is-still-decided-at-the-right-moment); where the engine is loaded
> from — N2 and N94; what the oracle guards against — N95; the envelope the page opens —
> [`encryption_envelope.md`](encryption_envelope.md); the package-to-artifact gate whose `verify` is
> one part of the oracle here, its formats and its limits — [`package_gate.md`](package_gate.md); the
> complete P01 report, with its accessibility, narrow screens, themes and the partial-month and
> empty-slice rules in full — stage 2.5; real report data — stage 2.4.

| Field | Information |
|---|---|
| Date | 2026-11-20 — revision 7, answering round 6 of Codex's review (FPROTO-6-01 to -08). Revision 6 answered round 5 (FPROTO-5-01 to -08), revision 5 answered round 4 (FPROTO-4-01 to -07) with the Owner's N95, revision 4 answered round 3 (FPROTO-3-01 to -07) with N94, revision 3 round 2 (FPROTO-2-01 to -08) and revision 2 round 1 (FPROTO-1-01 to -06), the same day; revision 1, 2026-11-13, went to round 1 |
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
  adds to it (§2.5) is the prototype's, and whether any of it joins the gate is decided with the
  framework, at 2.5.

**What the oracle guards against (N95).** The **ordinary behaviour** of each candidate: what its
framework, its libraries and the browser do on their own — caches, prerendering, storage, workers,
history —, and the page code this repository writes, which Codex reviews with the implementation.
Code of ours written to deceive the oracle, and a compromised dependency, are outside it; §9
writes them as residual risks. Within that scope the oracle fails closed: what it cannot observe is
inconclusive, never clean.

**How the criterion is met here.** The page that would be published is the **encrypted route**: a
build that **never receives report data**, with the sealed package placed in the finished output by
the harness afterwards (§2.2). No dependency code of that route ever runs with a network: its
packages are fetched by the harness itself and installed and built offline, so nothing the machine
serves — an earlier artifact, the clear mode — is in its reach (§2.2, §5). And the fixture whose
package is measured is drawn only after the encrypted builds exist (§2.1). Each candidate's **clear
mode** — its natural way of carrying data, with a clear fixture of its own as its source — is built
apart, in its own work tree, and shows whether and how the candidate runs report queries at build
time (A1); it is the diagnostic the criterion asks about, and the oracle's proof that it sees each
candidate's carriers. A candidate whose encrypted route cannot deliver the page is reported as **"the
encrypted route is not possible"**, with the probe and its output (A3); it is not said to have run a
query unless an output shows it did. What can still carry clear data in the encrypted route is the
browser, which §2.5.3 judges.

## 2. The common ground

### 2.1 The fixture

P01 is the view `monthly_revenue_by_channel_and_category`
([eng_dados at `f86b9fb`](https://github.com/alencardoug/mvp_eng_dados_1/blob/f86b9fb/dbt/models/consumption/monthly_revenue_by_channel_and_category.sql)):
`year_month`, `year_number`, `month_number`, `sales_channel_name`, `channel_type`,
`root_category_name`, `category_name`, `order_count`, `unit_count`, `gross_revenue_amount`,
`discount_amount`, `net_revenue_amount`, at the grain `[year_month, sales_channel_name,
category_name]`. The fixture keeps those names, in that order, and invents every value
**[planned]**. Its shape is fixed except for one parameter; its values are drawn.

Two fixtures exist, of different seeds: the **clear-mode fixture**, which feeds the clear mode and
its controls (A1, §2.5.5) and lives under `prototypes/framework/clear/`; and the **measured
fixture**, sealed into the package the encrypted route is judged and measured with. Both follow
this section.

**The shape** — large enough that every count of the gate's needles — the row count, `order_count`,
`unit_count` — has five digits or more; the calendar's years have four, and the draw covers them:

- 61 consecutive months — five years and a partial one; 3 channels, `fixture_canal_a` and
  `fixture_canal_b` of one channel type and `fixture_canal_c` of another; 5 root categories,
  `fixture_raiz_1` to `_5`, with 12 categories each, `fixture_cat_1_01` to `fixture_cat_5_12`. A full
  month has 180 rows; a **group** is the 12 rows of one channel and one root category in one month.
- **The gap, G**: `fixture_canal_c` has no row of `fixture_raiz_3` — its whole group — in the fifth
  month. Filtered on that channel, the page's summary has an empty cell there (§2.3).
- **The zero, Z**: `fixture_canal_b` has its whole group of `fixture_raiz_2` in the seventh month,
  with units and a gross revenue on every row, and a discount equal to that gross revenue: the
  `net_revenue_amount` of each of its 12 rows is `0.00`. Filtered on that channel, the summary cell
  exists and is zero — the case the page must not confuse with G.
- **The partial month**, the last: no row of `fixture_canal_c`, and *k* of the 10 groups of the
  other two channels, **whole groups only**, 5 ≤ *k* ≤ 10, with smaller amounts. Every populated
  summary cell, there as everywhere, gathers 12 native rows or more, never one. The page shows a
  fixed notice for it; the rule of M5 itself is 2.5's.
- 60 × 180 − 12 + 12*k* rows: 10,848 to 10,908. *k* is the one parameter of the shape, and it exists
  for the draw below. Round 4 found none of the six counts in either pinned DuckDB-WASM file
  (FPROTO-4, its §5).

**The values.** Drawn deterministically by `prototypes/framework/fixture.py` from a recorded seed,
with the control totals computed in Python with `decimal`, as `tests/site_fixture.py` does:

- amounts with two decimals and at least five digits in all, each distinct across the three amount
  columns, at least ten of them with a fraction ending in `0` — so that the JavaScript spelling
  `1234.5` of `1234.50` is exercised —, **with Z's exceptions, and only those**: on each of Z's 12
  rows the discount equals the gross revenue and the net is `0.00`; the twelve `0.00` are neither
  distinct nor eligible needles, which `contract.needles` and the coverage assertion account for;
- `order_count` and `unit_count` integers of five or six digits, each distinct across the fixture;
  **no sum of `order_count` over the rows of a summary cell, under any filter, equals a value the
  page displays** — every such cell gathers several rows, so the assertion can hold, and a summary
  count invented by summing is told apart from a native one (§2.6);
- the calendar too: the 61 months are a window chosen by the draw.

The generator checks the shape — 61 months, the row count for its *k*, no row in G, Z's 12 rows with
the exceptions above, *k* whole groups in the last month, no summary cell of a single row — and
fails before sealing if any does not hold.

**The G mutant** (FPROTO-4-06), for the proof of §2.6, is derived from the measured fixture after it
is drawn: G's group filled with 12 rows whose amounts and counts are zero. It has its own expected
shape — the canonical one with those 12 rows added and the zero exception extended to them — and
its own check. It is sealed and validated like any package, and assembly takes **the mutant's rows**
as the expected rows for that control (§2.2), so that it opens. The browser check of §2.6 then
compares the mutant's detail with the mutant's rows, and keeps the canonical expectation for one
cell only, G's summary cell (FPROTO-5-06).

**The draw against the baseline.** `verify`'s inspection searches each eligible value, the totals
object and the derived totals as byte substrings in every non-envelope file of the artifact
([`package_gate.md` §6](package_gate.md)), and the carrier inspection of §2.5.2 searches more
spellings in more carriers. A candidate's own code can hold such bytes by chance. The engine is not
in the artifact — both candidates load it from jsDelivr (N94; A7 for Evidence) —, the counts have
five digits or more, and the rest is checked, not assumed:

1. each candidate's encrypted route is built — before any measured fixture exists — and its
   **builder output** archived (§2.5.2); by §2.2 it cannot depend on the fixture, and it is byte for
   byte the non-package part of the artifact;
2. the generator draws a fixture, seals it, opens it with `envelope.open_report`, computes
   `contract.check_payload` and `contract.needles` on the payload — the values, the totals object,
   the row count, the sums —, and searches **both** candidates' builder outputs with **both**
   inspections: `contract.inspect`'s own search, and the carrier inspection's **full dispatch** —
   every role and layer of §2.5.2, stand-alone JSON and other data-bearing documents included —,
   over the fixture's needles and the page's query results;
3. a colliding value is redrawn; a colliding row count changes *k*; a colliding calendar moves the
   window. At most 1,000 draws in all, recorded with the seed and every rejection by needle class
   and inspection;
4. if no draw is clean, the run **stops with the draw exhausted** — the colliding class, inspection
   and file named —, a harness limitation that withholds every verdict (§2.5.4), never a failure of
   the candidate and never cleared by `public_values.json`, which keeps meaning "public by design".

**There is one measured fixture for both candidates.** The draw runs once, after both builder
outputs are final — after every probe of §3 that rebuilds Evidence; if either candidate is rebuilt
afterwards, the draw is redone against both new builder outputs, both artifacts are reassembled
with the new package, and every measure taken with the old one is discarded. Each measure is
recorded with the digests of the package and of the artifact it was taken on.

**The coverage assertion.** Before sealing, the harness computes `contract.needles` on the fixture's
payload and asserts that every eligible number contributes each of its spellings and every text of
three characters or more contributes itself, with no public value excluding any — the count, after
`needles`' own deduplication, is printed and compared with the one computed from the fixture alone.

The SQL types are written in a contract of the prototype's own, in the format of
`release/contract.json`, with the grain above and the sums on `unit_count` and the three amounts —
not on `order_count`, which is not additive across categories (M4). The repository's `release/`
is not touched.

### 2.2 The package, the inputs, and where the package enters

`prototypes/framework/fixture.py` seals the fixture with the envelope's producer
(`envelope.encrypt_package`) under a profiles declaration of the prototype with one profile,
Diretoria, with the showcase's public password (N22), entitled to P01. Round 1 of the review ran
the producer and `validate_manifest` on one profile, and on a profile with no report, and both pass
(FPROTO-1, its §4): Logística stays out — the access matrix is 2.6's —, and step 1 of §7 repeats
that run here.

**No dependency code runs with a network** (FPROTO-4-01). The npm packages a candidate's lockfile
names are fetched by the harness's own fetcher — plain HTTPS GETs of the tarball URLs the lockfile
records, from `registry.npmjs.org` only, each checked against the lockfile's `integrity` — into a
content-addressed cache of that candidate, archived with its listing. Nothing of a package runs
during the fetch. Every phase that runs package code — `npm ci --offline --ignore-scripts`, any
script A6 finds necessary, run alone with `npm rebuild <package>`, and the build — runs in the
sandbox with `--unshare-net`, reading that cache: it has no loopback to the host and no route
anywhere, so nothing the machine serves at that moment — an earlier artifact, the clear mode, the
local server of §2.7 — is in its reach, on a first run or on a rerun.

**The encrypted route's inputs are an allowlist.** Its work folder is assembled fresh for every
install and every build, from a list the harness writes and archives — path and SHA-256 of each
file —:

- the candidate's tracked sources, from `git ls-files prototypes/framework/<candidate>/` at a
  recorded commit, each checked against the commit's blob;
- `web/envelope.mjs`, likewise;
- the candidate's npm cache, by its archived listing;
- for Evidence, if A3 needs one, an **empty source**: a Parquet with P01's twelve columns and types
  and **zero rows**, written by the harness from the prototype's contract — a schema the contract
  already makes public, and nothing else;
- for the build, the `node_modules/` the install phase produced, archived with its listing.

Before each phase the harness lists every file in the work folder and compares the listing with the
allowlist: an extra, missing or changed file refuses the phase. The fixture generator, every
fixture, every package and the whole **clear mode** — its fixture, its work tree, its npm cache, its
build output, its query caches, its `.evidence/` and `.svelte-kit/` folders — live under
`prototypes/framework/clear/`, which is never bound into the encrypted route's sandbox; the clear
mode never shares a work folder or a cache with it.

**The package enters after the build.** The page fetches the package at run time from a fixed path,
`package/`. Assembly, a step of the harness outside the sandbox:

1. refuses if the builder output already has a `package/` entry — the candidate does not get to
   write where the package goes; that is the candidate's form, recorded as `FORM` (§2.5.1), not
   overwritten;
2. **validates the package on its own**, before and apart from `verify`: `envelope.validate_manifest`,
   `envelope.check_package` with the declared passwords, `contract.inventory_exact` and
   `contract.entitlements_exact` against the prototype's declarations, and `contract.check_payload`
   on the opened report, the same functions the gate uses; and checks that the opened rows **are the
   expected rows** — the drawn fixture's, or, for the G mutant's control, the mutant's —, row for
   row. A refusal is `HARNESS_ERROR`. The digest of the
   manifest and of each envelope is recorded as **the validated package**;
3. copies the builder output and then the package into the artifact folder;
4. checks that the artifact, less `package/`, is byte for byte the archived builder output, and that
   `package/` holds exactly the validated files.

The public password is no shortcut: a page or a build helper that holds it has nothing to open at
build time.

Both pages open the package with the same reader, `web/envelope.mjs`, imported as is: login derives
the key, unwraps the data key and returns the control totals and the Parquet; the Parquet is then
registered in a DuckDB-WASM instance and queried there. The envelope's reader is not re-implemented
in either candidate, and the page's only path to the report is that reader — which Codex checks in
the page code it reviews (N95).

### 2.3 The page

The same page, in Portuguese, in both **[planned]**:

1. a login box with the Diretoria password; a wrong password shows that nothing opened; **nothing is
   decrypted before the visitor submits** — no key derived, no key unwrapped, no envelope opened;
2. after login, a filter by `sales_channel_name` — its values read from the data, with "todos" —
   and a month selector for the detail table;
3. a chart of `net_revenue_amount` by `year_month`, one series per `root_category_name`;
4. **the summary**: a table by `year_month` and `root_category_name` with `net_revenue_amount` and
   `unit_count`, summed from the rows of the filter. It has **no `order_count`**: its cells gather
   several native rows, and the view carries no order identities from which their distinct count
   could be rebuilt (M4);
5. **the detail**: a table at the view's own grain — channel and category, for the selected month
   and the filter — with `order_count`, `unit_count` and `net_revenue_amount` as they are in the
   rows, nothing summed. This is the only place `order_count` appears;
6. in the summary, a cell with no row under the filter says **"Sem vendas neste recorte."** — not
   `R$ 0,00`, not blank —, and a cell whose rows sum to zero shows `R$ 0,00`; the fixed notice
   **"Mês em curso: os números ainda vão mudar."** on the last month, which names no month;
7. **a logout that ends the session's data context**: it terminates the DuckDB-WASM worker — with
   its registered files — and then replaces the page with the login page by a full navigation,
   `location.replace`, so that the history keeps one entry, the login page's, and no JavaScript
   object, worker or registered file of the session survives it;
8. no store is written with data, during the session or after it: not CacheStorage, IndexedDB,
   `localStorage`, `sessionStorage`, the origin private file system, cookies or a service worker —
   what a framework writes there on its own is exactly what §2.5.3 looks for.

Queries run only in the browser, after login. Number formatting is `pt-BR`. No text of the page,
fixed or generated before login, carries a fixture value.

### 2.4 The engine

DuckDB-WASM **1.32.0**, the last stable release on npm, of 2025-12-16 — `latest` points to a
development build, `1.33.1-dev57.0` — **[measured, M54]**. **Both candidates load it from jsDelivr,
pinned to that version** (N2, PLAN §3.4; N94): the engine is 34.2 MB uncompressed and 6.8 MB with
brotli (M15), which would count against Hosting's daily quota at every first load, and whose bytes
hold almost any short integer (§2.1). The own build does it by design. Evidence brings its own
engine: `@evidence-dev/universal-sql` 3.0.1 asks for `^1.30.0` **[measured, M54]** and bundles it
through Vite, serving its WASM and worker from the page's origin; whether it can load them from
jsDelivr instead is probe A7 (§3). The version its lockfile resolves is recorded, and a difference
from 1.32.0 is reported, not forced.

**The pinned third-party bodies.** Every file either candidate loads from jsDelivr is declared, by
URL and SHA-256, in the candidate's `prototypes/framework/<candidate>/cdn.json`; the digests are
taken once by the harness, and for npm-published files checked against the same file of the npm
tarball. The own build's subresource-integrity attributes are generated from it.

### 2.5 The oracle

The **artifact** — the builder output with the validated package added by the harness — is judged
by the gate's `verify` (§2.5.1); the builder output and the artifact are inspected for fixture data
(§2.5.2); the browser is judged from before the page's first script to after logout (§2.5.3). The
verdict combines the three (§2.5.4), and the controls of §2.5.5 prove each part before its "pass"
means anything.

#### 2.5.1 The gate's own `verify`, and its harness

`bi_como_codigo.release.verify` is the function the publishing workflow runs before any upload
([`package_gate.md` §2](package_gate.md)); whatever is chosen will have to pass it at 2.5, so it
runs here unchanged. Its limits are its own document's: it reads bytes and searches spellings, and
its first refusal by form stops it before the inspection by content. Here it is a necessary
condition, never a sufficient one.

**The harness [planned].** For each run, `prototypes/framework/harness.py` assembles a root of its
own, outside the candidate's folder:

```
<run>/root/release/contract.json       copied from prototypes/framework/release/
<run>/root/release/profiles.json       copied from prototypes/framework/release/
<run>/root/release/public_values.json  copied from prototypes/framework/release/ — {"about": …, "values": []}
<run>/root/release/include.txt         copied from prototypes/framework/<candidate>/release/
<run>/root/release/media_types.txt     copied from prototypes/framework/<candidate>/release/
<run>/artifact/                        the builder output, with the validated package in package/
```

and calls `release.verify(<run>/root, <run>/artifact, live=lambda: release.NO_LIVE)`: `verify`
appends `release/` to the root itself. The three shared declarations live once; the two lists are
the candidate's, in the gate's syntax — globs under `site/`, matched against the artifact's paths
with the prefix removed —; the formats are `package_gate.md`'s. Round 2 ran this layout, with a
clean control passing and a clear label refused (FPROTO-2, its §5).

**Whose refusal it is.** The declarations and the package are the harness's, and only the files of
the builder output are the candidate's. A run's outcome is classified by the stage that produced it
— assembly, then `verify` — against the gate's own messages and codes in `release.py` and
`contract.py`:

| Stage and outcome | Class |
|---|---|
| Assembly: the package refused by its own validation | `HARNESS_ERROR` |
| Assembly: a `package/` entry in the builder output | `FORM` |
| `verify`: an exception that is not `release.Refused` | `HARNESS_ERROR` |
| `verify`: `include.txt: … is not a path under site/`; `public_values_invalid`, `contract_invalid`, `declarations_agree` — the declarations | `HARNESS_ERROR` |
| `verify`: `0 package manifests in the artifact` — the harness did not place the package | `HARNESS_ERROR` |
| `verify`: `package manifest refused`, `… is in the manifest and not in the artifact`, `envelopes not in the manifest`, `inventory_exact`, `entitlements_exact`, `package refused`, a `totals_*`, `schema_exact`, `not_null`, `grain_unique`, `content_bound` or `parquet_unreadable` — the package, already validated by assembly | `HARNESS_ERROR` |
| `verify`: `N package manifests` with N ≥ 2 — a `manifest.json` of the builder's; `… is not under the inclusion list`; `extension not in media_types.txt`; `is a source map`; `references a source map`; `under Hosting's reserved __/ URLs`; `is a symbolic link`; `is not a plain file` | `FORM` |
| `verify`: `holds a Parquet magic outside an envelope`, in a file the harness parses as a Parquet with P01's schema and **zero rows** | `SCHEMA_ONLY` |
| `verify`: any other `holds a Parquet magic outside an envelope`; `holds a clear payload outside an envelope`; `holds a data key in the clear` | `CONTENT` |
| `verify`: `clear_value` or `clear_totals` in a named file | `CONTENT` or `COLLISION`, decided below |
| `verify`: no refusal | `PASS` |

**A collision is established by reproduction** (FPROTO-4-05). `clear_value` and `clear_totals` name a
file and a code, not the needle. For either, the harness re-runs the gate's own search on that
file of the archived artifact, with the same values, the same public set and the same role of the
haystack — the whole file, or for the manifest its labels (N83) —, and must reproduce the named
code; a search that does not reproduce it is `HARNESS_ERROR`. If it reproduces, and the file is
byte-identical to the same file of the archived builder output — so it cannot hold the fixture, by
§2.2 —, the refusal is a `COLLISION`, with the matching needles listed by class; otherwise it is
`CONTENT`. After a clean draw (§2.1) a `COLLISION` means the draw and `verify` disagree, which stops
the run.

Any message the table does not list is `HARNESS_ERROR`, so that an unknown refusal is never read as
the candidate's pass or as its failure. A `HARNESS_ERROR` or a `COLLISION` stops the run; it is
fixed in the harness or in the draw, and the run is repeated — never written as a cost or a failure
of the candidate. Step 1 of §7 proves each row with its own control (§2.5.5).

#### 2.5.2 The builder output and the artifact, inspected

**Outputs are kept.** Every builder output is archived, as a tarball with its SHA-256, the moment
its build ends and before any check — under `prototypes/framework/<candidate>/runs/`, ignored by
Git —, and so is every artifact and everything §2.5.3 collects in the browser. A setting produces a
new run; the earlier archives stay and keep their verdicts (§2.5.4).

**The carrier inspection [planned].** `prototypes/framework/inspect_output.py` reads a set of files
and names the carrier of any fixture value it finds. It runs on the builder output — where, by §2.2,
nothing can be found, and finding something means the harness let data into the build —, on the
artifact, and on what §2.5.3 collects. Its needles are the fixture's values **and the results of the
page's queries** — every summary and detail cell under every filter, from the oracle of §2.6 —, since
a cache of a query holds results, not rows.

**Numbers are compared by role** (FPROTO-4-03). Small integers — a protocol version of `1`, a month
number — are everywhere in code and metadata, so what is compared depends on what the file is:

- **the integer needles are the counts**: the row count, every `order_count` and `unit_count`, and
  every integer of the page's query results, all of five digits or more by §2.1. The fixture's
  small integers — `month_number`, and `year_number` as a number — are never integer needles on
  their own: a protocol version of `1` or a month number in a metadata document is nothing to
  report;
- **the calendar is matched as a pair** (FPROTO-6-03): inside a structured, data-bearing record — one
  JSON or devalue object, one Arrow or Parquet row, one stored record, one history state —, two
  integer fields whose values are the `year_number` and the `month_number` of one month of the
  fixture's window are a finding, `INSPECT_CALENDAR`, whatever the fields are called; so is a
  `year_month` string. A report filter snapshot holding `2048` and `5` side by side is found; a
  version `1` beside a scroll offset is not a month of the window unless its pair is;
- **code-bearing files** — HTML, JavaScript, CSS, WASM, fonts, images, anything served as the page
  itself —: every text needle; every amount with a fraction, in each spelling of
  `contract.spellings` and in its shortest JavaScript spelling; and the integer needles only inside
  a structured carrier found in them;
- **data-bearing carriers** — a JSON, devalue, Arrow IPC or Parquet document found anywhere, a
  SvelteKit fetched-data script, and every store, write and history or navigation state of §2.5.3
  —: every text needle and amount, the integer needles in any spelling, so that `20000` in
  `orders=20000` written to a store is found, and the calendar pairs.

**The draw and the inspection use one function.** The draw of §2.1 calls the inspection's own
recursive dispatch — the same roles, layers and needles — on both builder outputs, so that what it
calibrates is exactly what is later inspected; a candidate value found there by any predicate is
redrawn.

For each file, recursively to a depth of three:

| Layer | What is done |
|---|---|
| The validated package | a file of `package/` whose path and digest are the validated package's (§2.2) is an envelope or the manifest, whatever `verify` reached. An envelope is not inspected further. The manifest is judged by role: its labels searched with the **full** needle set — text and numeric spellings —, as the gate does (N83; FPROTO-4-04); its typed fields — versions, identifiers, sizes, digests — validated by `validate_manifest` and not compared with the fixture's numbers. Any other file of `package/`, any other `manifest.json` and any copy with another digest is inspected like the rest |
| Pinned third-party bodies | a body whose URL and SHA-256 are declared in `cdn.json` (§2.4) is recorded and not inspected further; a body at a declared URL with another digest is **inconclusive** |
| Decoders | gzip, zlib and raw deflate; brotli; zstd; base64, standard and URL-safe, on runs of 16 characters or more; hex on runs of 32 or more; percent-encoding; JSON and JavaScript string escapes; HTML entities — each decoded result is inspected again |
| Structured carriers | JSON, and Svelte's devalue as JSON-like text, parsed — SvelteKit's fetched-data scripts (`data-sveltekit-fetched`, with or without `data-b64`) among them —: every number compared **as a number**, so `1234.5` matches `1234.50`; Arrow IPC, stream and file, and Parquet, parsed with `pyarrow`: every cell compared as a value, and a Parquet with P01's schema and no row recorded as schema only |
| Text | every text needle as a byte string; the spellings of the role above |
| Binary numbers | every amount with a fraction as the 8 bytes of an IEEE 754 double, both byte orders, and as the 16 bytes of an Arrow `decimal128` at scale 2 |
| What remains | a binary file byte-identical to a file of the candidate's locked dependency tree is recorded and not inspected further; any other binary that no layer decodes is **inconclusive** |

Each finding carries its code — `INSPECT_TEXT`, `INSPECT_NUMBER`, `INSPECT_CALENDAR`, `INSPECT_ARROW`,
`INSPECT_PARQUET`, `INSPECT_BINARY` — and the decoding path, never the value. The decoder list is closed: a carrier
outside it is not "clean", it is inconclusive. In the encrypted route the list is a second line,
not the argument: §2.2 keeps data out of the build; the list names the carrier when a control or
the clear mode puts data in.

#### 2.5.3 In the browser

Every Chrome target of the run — the page, its frames and its workers of every type, nested ones
included — is observed from before its first script runs: the check discovers every target of the
browser (`Target.setDiscoverTargets`) and attaches to each with execution paused at start, repeating
the auto-attach inside every attached session, so that nested targets are reached; the
instrumentation below is installed in each target before it resumes, and in every page realm by
`Page.addScriptToEvaluateOnNewDocument`. The check then reconciles what it instrumented with what
exists: every discovered target, and every execution context reported by `Runtime` in each — page,
frames, workers —, must carry the instrumentation. **A target or context without it, a request
without a captured body where one was expected, or a store that could not be enumerated makes the
run inconclusive**; a reply that has no body by its status — a `304`, a `204` — is recorded as such,
not as a missed capture.

The **journey** observed is fixed: navigation; a **wrong password**, submitted; the right one; the
filters and months of §2.6; logout; the new login page. In each instrumented realm:

- **Decryption is observed where it can happen.** `crypto.subtle.deriveKey`, `deriveBits`,
  `unwrapKey` and `decrypt` are wrapped, and each call is recorded with its timestamp, realm,
  submission and outcome. What each moment allows is fixed by the unchanged reader
  (`web/envelope.mjs`) (FPROTO-5-01): **before any submission**, no call at all; **after a wrong
  password's submission**, a derivation, and an `unwrapKey` that fails — no successful unwrap, no
  `decrypt`, no report opened; **after the right password's submission**, a derivation, a successful
  unwrap and the report's `decrypt`. A call before any submission is `PREMATURE_DECRYPT`; a
  successful unwrap or a `decrypt` after a wrong password is `UNEXPECTED_DECRYPT`; both are
  findings, and both fail the criterion (§2.5.4). A call belongs to the submission that was active
  when the call **started**; the permission a submission gives ends at logout, and the replacement
  login page starts again from "before any submission" (FPROTO-6-01).
- **Every store is observed from the moment it is opened** (FPROTO-6-02). Hooking each write path
  of each API cannot be complete, so the check holds the entry points, which are few, and treats
  anything it cannot capture after them as inconclusive:
  - **the entry points** — `indexedDB.open`, `caches.open` and `caches.has`, the names they are given
    recorded and inspected; `navigator.storage.getDirectory`; `navigation.updateCurrentEntry`,
    `navigation.navigate` and `navigation.reload` with a state; `history.pushState` and
    `replaceState`; the `document.cookie` setter and `cookieStore.set`;
    `navigator.serviceWorker.register` — are wrapped in every realm, page and worker, and each call
    is recorded;
  - **Web Storage** values come from the protocol's `DOMStorage` events, which carry the value
    whatever path the page used — `setItem` or a named property, as SvelteKit's own snapshots do;
  - **IndexedDB** values come from hooks on `IDBObjectStore.put` and `add` and `IDBCursor.update`;
    the protocol's `Storage.trackIndexedDBForStorageKey` events are the control: a content change it
    reports that no hooked call explains is inconclusive;
  - **CacheStorage** contents come from `Storage.trackCacheStorageForStorageKey`, each content event
    triggering an enumeration of that cache on the spot, and each entry's body correlated with the
    effective network body of the same request when the write was an `add` or `addAll`; an entry
    whose body is neither enumerated nor correlated is inconclusive. A cache's name is inspected as
    text when it is opened, so a name created and deleted before logout is still seen;
  - **history and navigation state** — the state and URL of every `pushState`, `replaceState`,
    `navigation.updateCurrentEntry` and navigation with a state, and `navigation.currentEntry
    .getState()` at each enumeration — go to the inspection as data-bearing; a report selection in
    the state of the one entry is a finding even after logout replaced that entry;
  - **the origin private file system** has no write path the check can observe completely —
    native writers and pipes bypass any stream hook —, so **any** call to
    `navigator.storage.getDirectory` in a judged run makes it inconclusive, whatever it wrote;
  - every value captured goes to the carrier inspection as a data-bearing carrier (§2.5.2), at the
    moment of the write; a value written and deleted before logout is still a write. A store opened
    whose mutation the check could not capture is inconclusive.
- **The stores are enumerated by storage key**, through the DevTools protocol rather than the page:
  for each origin and storage key the run touched — `Storage.getStorageKey` per frame —, the
  IndexedDB databases and their records, the CacheStorage caches and their entries, `localStorage`
  and `sessionStorage`, the cookies the browser holds for it, the service worker registrations with
  their scripts, and, from inside the page realm, the origin private file system walked from
  `navigator.storage.getDirectory()`. `Storage.getUsageAndQuota` is a cross-check, not a substitute:
  usage above zero with nothing enumerated is inconclusive. They are enumerated before the first
  submit, after the wrong password, after logout and on the new login page.
- **Every effective response body** of every target is captured and inspected — before login as a
  carrier that must hold nothing; after login, the package's envelope bodies are recognised by
  binding, not exempted by URL: a body from the local origin at the canonical `package/` path whose
  decoded bytes have the validated digest (§2.2) is an envelope, and any other body there is
  inspected — during the wrong attempt too, which fetches the envelope before its unwrap fails. The
  pinned third-party bodies are recognised by `cdn.json` (§2.5.2). **A reused body** — a `304`
  revalidation, a memory or disk cache hit — is the effective response even when the wire carried
  none: its bytes are captured from the protocol with `Network.getResponseBody`, which is preferred;
  failing that, it is bound to the response already inspected **for the same request variant** —
  same URL, same selected encoding, same strong `ETag` —, which a `304` confirms (FPROTO-6-05). Only
  a reused body neither captured nor bound is inconclusive.
- **After logout**: the targets must hold no worker or frame of the session — a DuckDB worker still
  alive after logout is a finding by itself, whatever it holds —; the page's execution context must
  be the login page's new one; and the history is checked against what §2.3 item 7 makes it:
  `Page.getNavigationHistory` must hold exactly one entry, the login page's, and `history.back()`
  must cause no traversal — no navigation event within two seconds and the same execution context
  after it. A report page restored from the back-forward cache, or any entry of it in the history,
  is a finding.

Everything collected goes to the carrier inspection of §2.5.2. A value found fails the criterion,
as a build-time one would: a framework that caches query results in the browser, decrypts before it
is asked, or keeps the session's data alive after logout, carries clear data outside the envelope.
What is not judged here, and is said so: the browser's own HTTP cache of the envelope, which is
ciphertext, and memory the operating system has not yet reclaimed.

#### 2.5.4 The verdict

One function, `verdict(runs)`, over every **judged** run of the encrypted route of a candidate,
tested in step 1 of §7 with a table of cases — synthetic run histories, judged within the test and
kept apart from any candidate's history. Every real run is labelled when it starts — `judged`,
`probe` or `control` —, and only judged runs enter a candidate's verdict; a probe's or a control's
run is the evidence of that probe or control, and the harness asserts that none of them is in a
candidate's history. A run is a sequence of stages — build, archive,
inspection of the builder output, assembly, `verify`, inspection of the artifact, browser capture —,
each with its class or its absence. **The mandatory stages depend on how the run ended**: every
judged run requires its build, archive and the inspection of its builder output; one whose assembly
ended in `FORM` requires nothing more — `verify` and the browser do not apply to an artifact that
was not assembled —; every other requires all seven. **A judged run with a mandatory stage missing
stays open** until a later judged run closes it (FPROTO-6-04): a run that failed or was interrupted
**before an artifact existed** — before its archive, or at assembly with `HARNESS_ERROR` — is closed
by a later judged run with **the same build input**, the digest of its allowlist, that completes the
stage it lacked; a run whose artifact exists is closed only by **the same artifact digest** run again
from an equivalent starting state with the stage complete. The precedence, first match wins:

1. **fails the criterion** — in any judged run: `verify`'s `CONTENT`; a finding of the carrier
   inspection in the builder output, the artifact or the browser; `PREMATURE_DECRYPT` or
   `UNEXPECTED_DECRYPT`; a session's worker, context or history entry alive after logout. A later run never undoes it, and neither does a
   `HARNESS_ERROR` in a later run: a setting that removed the carrier does not remove the run that
   showed it;
2. **not run** — no run of the encrypted route exists, or **the encrypted route is not possible**
   (A3), with its probe: no verdict on the criterion, and the result says why;
3. **stopped** — the latest run ended in `HARNESS_ERROR`, `COLLISION`, the draw exhausted, or a build
   or a browser capture interrupted: no verdict until it is repeated;
4. **not established** — any judged run, earlier or latest, has a mandatory stage missing, or an
   inconclusive file, target, context, body or store, that no later evidence resolved. Resolving means re-inspecting **that archived output or
   capture** with the decoder that reads it, or re-running **the same artifact digest from an
   equivalent starting state** — a fresh profile for a cold capture, the primed state of §2.7 for a
   warm one — with the capture complete; a later run of another artifact, or from another state,
   does not resolve an earlier one;
5. **a cost** — the latest run's assembly or `verify` refused by `FORM`, or `verify` by
   `SCHEMA_ONLY`, and nothing above: cleared by a setting of the candidate's build, never by
   changing `verify`; the setting is recorded, the content of the output that carried the refusal
   was judged in its own run, and the inclusion list and media types are the narrowest that cover
   the artifact, their length a measured cost (§6). A schema-only Parquet is no report data, but
   the gate will not publish it, so it is a cost of the arrangement that emits it. A refusal no
   setting clears means the candidate cannot go through the publishing workflow, and it fails on
   that, said apart from the criterion;
6. **passes** — in the latest judged run every mandatory stage completed, `verify` passed, nothing was
   found and nothing is inconclusive, and no earlier judged run is in 1 or 4.

#### 2.5.5 The controls

No part of the oracle is trusted until it has failed something real. Each control has **one** leak,
in one carrier, and asserts its own diagnosis at the layer it is for — the class of the stage, the
carrier code of the inspection, or the browser finding — and records the others, even where another
part trips too. Controls built from the clear mode carry the clear-mode fixture, and are inspected
with its needles:

| Control | Built from | Expected |
|---|---|---|
| Clean | the candidate's builder output and the validated package | `verify` `PASS`; no finding; verdict passes |
| Clean metadata | the clean artifact plus a JSON with a protocol version of `1` and a month number | no finding: small integers are not integer needles (§2.5.2) |
| A count in a JSON | the clean artifact plus a JSON holding one fixture `order_count` | `INSPECT_NUMBER` |
| An incidental literal | a builder output with a literal equal to a candidate fixture amount in its shortest JavaScript spelling | the draw rejects that amount and records the rejection; the accepted fixture's artifact, with the same literal, has no finding |
| Package only, with a form refusal | the clean artifact plus an empty `manifest.json` of the builder's | `verify` `FORM`; no inspection finding, nothing inconclusive — the package's files are recognised by digest |
| A numeric label behind form | a validated package whose manifest label holds a fixture amount, plus a second `manifest.json` | `verify` `FORM`; inspection `INSPECT_NUMBER` in the label; verdict fails |
| Harness classes | a missing declaration; a malformed `public_values.json`; a malformed `include.txt`; the package not placed; a corrupted envelope; a package of another fixture | `HARNESS_ERROR` for each — the last two already at assembly —; verdict stopped |
| Assembly form | a builder output with its own `package/` | assembly `FORM`; the inspection of its builder output still runs; verdict a cost |
| Schema only | a builder output with the zero-row schema Parquet of §2.2; and the same file with one row of the fixture | `SCHEMA_ONLY` and a cost for the first; `CONTENT` and `INSPECT_PARQUET`, verdict fails, for the second |
| Collision | an artifact holding DuckDB-WASM 1.32.0's EH WASM in a file identical to the builder output's, with a forced fixture whose row count is one round 3 measured in it; the same with the reproduction search given another haystack role | `COLLISION`, with the row count's class named; `HARNESS_ERROR` for the second; and a fixture with no clean draw against that output ends as draw exhausted, not as a failure |
| A fixed label | the clean artifact plus a file holding one fixture label | `verify` `CONTENT`; inspection `INSPECT_TEXT` |
| A varying value, one carrier each | the clean artifact plus one file — an amount in `pt-BR`: `verify` `CONTENT`, `INSPECT_TEXT`; an amount in its JavaScript spelling: `verify` `PASS`, `INSPECT_NUMBER`; Arrow IPC: `verify` `PASS`, `INSPECT_ARROW`; Parquet with rows: `verify` `CONTENT` for its magic, `INSPECT_PARQUET`; gzip, brotli and base64 of a JSON of rows, JSON-escaped text, a base64 payload in a service worker: `verify` `PASS`, the inspection's code with its decoding path | as listed, each asserted at its own layer |
| Content behind form | a label in a `.map`; a label in a second `manifest.json` | `verify` `FORM`; inspection `INSPECT_TEXT`; verdict fails |
| Carrier nobody listed | rows encrypted under a key the oracle does not hold | inspection inconclusive; verdict not established — and still so after a later clean run of another artifact |
| A pinned body changed | a CDN response at a declared URL with other bytes, served by the check | inconclusive; the declared body, clean |
| The package's body | the clean envelope at its canonical URL; a clear body served at that URL instead; a warm revalidation with body capture unavailable and the variant bound by its `ETag`; a revalidation with body capture unavailable and no `ETag` | clean; the inspection's own diagnosis for the clear body; clean for the bound reuse; inconclusive for the last |
| Data in the inputs | a fixture file, a package, a clear-mode cache, each planted in an encrypted work folder | the allowlist check refuses the phase, naming the file |
| No network for package code | an install and a build, each with a local listener serving a package on the loopback | the phase cannot reach it: the probe of §5 in that mode, through the real wrapper |
| Browser, one each | the normal journey, a wrong password then the right one; a page that decrypts at startup with the public password; one whose wrong attempt unwraps successfully and decrypts, with no report rendered; one that writes a result into IndexedDB after login and deletes it before logout; one that updates a record through `IDBCursor.update`; one that writes a fixture label into `sessionStorage` by a named property and removes it before logout; one that writes `orders=` and a fixture count into `localStorage`; one that writes a result into CacheStorage; into a file of the origin private file system that it keeps after logout; one that puts a report selection into the history state by `replaceState`; one that keeps a selected month in the current entry by `navigation.updateCurrentEntry`; a worker that opens a cache named after the selected channel and deletes it before logout; a worker that fills a cache with `addAll`; a page that writes an OPFS file through a native writer and removes it; a filter snapshot in `sessionStorage` with a typed `year_number` and `month_number` of the window and no text; a logout that drops the table and keeps the worker with its registered file; a logout by `location.assign`, with the back-forward cache available, whose report page `history.back()` restores; a nested worker the check is denied; a context left uninstrumented; a response body withheld | clean for the first; `PREMATURE_DECRYPT`; `UNEXPECTED_DECRYPT`, and a failing judged verdict; a write finding, at the moment of the write, for each of the five writes; a finding for the retained store; a history finding; a navigation-state finding; a finding for the cache's name; the `addAll` entries correlated with their bodies, and a finding if they hold a value; inconclusive for the OPFS use; `INSPECT_CALENDAR`; a finding for the kept worker; a finding for the restored page; inconclusive for the last three. The collectors for retained values are proved apart, each on a value left in its store |
| Verdict cases | synthetic histories, judged in the test: no run; a build interrupted before its archive, then a clean retry with the same build input; a build interrupted; a capture interrupted; the draw exhausted; an earlier inconclusive run followed by a pass; an incomplete cold capture followed by a clean warm one of the same artifact; a browser capture absent on artifact A followed by a clean run of artifact B; the same, then A run again from a fresh profile with the capture complete and clean; an assembly `FORM` with its builder output inspected; the same without that inspection; a content failure followed by a `HARNESS_ERROR` | not run; passes; stopped; stopped; stopped; not established; not established; not established; passes; a cost; not established; fails. And on the real history: no control or probe run is in it |
| Clear mode | the candidate's natural clear build, in its own work tree, with the clear-mode fixture — Evidence with it as a clear Parquet source; the own build with a page that fetches the clear Parquet | the inspection names every carrier A1 found, each also copied **alone** into a clean artifact and diagnosed there |

The controls run first on hand-made outputs (step 1 of §7), then on each candidate's own builder
output, so that the carriers are the ones the candidate actually writes; A1 supplies them for
Evidence.

### 2.6 The browser check

A Node script drives headless Chrome through the DevTools protocol, as `m49` did, against each
artifact served on `127.0.0.1` (§2.7) **[planned]**. Its oracle is the same queries run by Python's
DuckDB over the clear fixture:

- submits a wrong password, and checks that nothing opened;
- logs in, waits for the tables, reads their cells from the DOM and compares them with the oracle —
  equal, cell by cell, as text in `pt-BR`;
- applies the filter on "todos", `fixture_canal_a`, `fixture_canal_b` and `fixture_canal_c`, and
  the month selector on the fifth, the seventh and the last months, and compares again;
- **G**: under `fixture_canal_c`, the summary cell of the fifth month and `fixture_raiz_3` reads
  exactly "Sem vendas neste recorte."; **Z**: under `fixture_canal_b`, the cell of the seventh month
  and `fixture_raiz_2` reads `R$ 0,00`; the notice of the last month is present;
- **`order_count`**: the detail cells equal the native values of the fixture; the summary's header
  has exactly the columns of §2.3 item 4, and no summary element holds any of the sums §2.1 made
  distinct;
- logs out, and runs §2.5.3's after-logout collection;
- records every network request of every target: only the local origin and `cdn.jsdelivr.net` at
  the declared URLs.

**The check is proved to fail**: its comparator runs again on altered copies of the DOM it read —
G's cell turned to `R$ 0,00`, G's notice blanked, Z's cell turned to the notice, a summed count
written into a summary cell — and must refuse each, for that reason; and the own build is served
once with the G mutant of §2.1: the page must open it, its detail must equal the mutant's rows, and
the check, keeping the canonical expectation for G's summary cell alone, must refuse that page on G
and on nothing else.

### 2.7 How the costs are measured

So that bytes and times describe the candidates and not the state of a cache or of the person
running them **[planned]**:

- **Serving.** One local static server for both, written for the prototype: it sends
  `firebase.json`'s headers — `Cache-Control: no-cache` on every file —, compresses text files with
  brotli or gzip as the request accepts, as Hosting does **[assumed]**, with `Vary: Accept-Encoding`,
  and gives each representation its own strong `ETag` — the SHA-256 of the bytes sent and their
  encoding —, which §2.5.3 binds reused bodies with. jsDelivr serves itself;
  its encoding is recorded as received. If A7 fails, Evidence's engine is served by the local server:
  that is recorded as a delivery condition of its own, with the engine's bytes counted on the local
  origin and Hosting's quota cost estimated from them.
- **The same package.** Both candidates are measured on artifacts assembled with the one package of
  the final draw (§2.1), each measure recorded with the package's and the artifact's digests.
- **One journey, fixed.** The script navigates; types the password and submits **as soon as the
  password field is present and enabled** — not after a pause, so that work a candidate starts on
  load, as Evidence's `+layout.js` starts its engine, falls inside the measured time —; and waits for
  the summary. The wrong-password step of §2.6 is not part of the timed journey.
- **One clock** (FPROTO-4-07). Page marks are taken as `performance.timeOrigin + performance.now()`,
  in milliseconds of wall time; the DevTools protocol's network events carry a monotonic timestamp,
  and `Network.requestWillBeSent` carries both its monotonic timestamp and its wall time. Every
  session's monotonic times are mapped to wall time through those pairs, per session, and the
  largest disagreement between pairs is recorded as the clock's error; a cutoff is a page mark on
  that one axis.
- **Four timestamps**, from one script injected before any page script runs, in both: navigation
  start, the login box present, `submit`, and the first moment every expected cell of the summary is
  present with its expected text. Two observations are reported, apart: **navigation to summary**,
  what a visitor waits for, and **submit to summary**, with the PBKDF2 derivation of M49 inside.
- **Cold runs.** Five, each in a new Chrome process with a fresh, empty `--user-data-dir`.
- **Warm runs.** Five, **each in its own fresh profile and Chrome process**, each after the same
  predeclared priming: two full journeys — login, the summary with every request of the engine and
  the package finished, logout —, each followed by **quiescence**: the tab closed, no request in
  flight and no target of it left for two seconds. The measured journey is then the third use of
  every script, and no sample inherits another's state. The condition is reported as what it is —
  **two standard priming journeys** —, not as an equal cache state (FPROTO-6-06): each sample keeps
  its **cache evidence** — per request, served from memory or disk cache, revalidated with a `304`
  or fetched again with a `200`, and, from a Chrome trace of the `v8` category, which scripts
  consumed a compiled-code cache. Samples whose evidence matches form one series; a sample whose
  evidence differs is reported in its own series with the difference named, and the warm statistic
  is never taken across them. The priming and sample traces are checked to be of the same artifact
  and delivery condition, and the split is proved once on a deliberately mismatched trace. What
  carries over from the priming, and the origin storage the candidate kept, are listed beside each
  sample. Cold and warm are reported apart, never in one statistic.
- **Bytes.** For every request of every target — page, worker, frame —, from the DevTools protocol:
  origin, `Content-Encoding`, the wire status from `Network.responseReceivedExtraInfo` beside the
  effective one, whether it came from the memory cache, the disk cache or a service worker, and the
  encoded bytes reported by `Network.dataReceived` and `Network.loadingFinished`. At each cutoff two
  quantities are reported: **encoded bytes observed by the cutoff** — what the protocol had reported
  by then, partial transfers included, labelled as such, since Chromium may report progress late
  and in batches — and **completed responses**, those finished before it, with their
  `encodedDataLength`; their sum over the whole journey is checked against the completion totals. A
  revalidation answered `304` counts its wire bytes, and the body it let the browser reuse is
  reported apart, as **served from cache**, with its size; the same for memory and disk cache hits.
  Totals split by origin — the local origin is what Hosting would serve and count,
  `cdn.jsdelivr.net` is not — and, for each local file, its size raw and brotli-compressed.

Every number is kept with its trace — timestamps, requests, cache flags, clock pairs, digests — in
the evidence of the stage, and the byte accounting is checked on one worker transfer that spans a
cutoff and on one warm revalidation before it is trusted.

## 3. Candidate A — Evidence

**Version.** `@evidence-dev/evidence` 40.1.8 with `@evidence-dev/core-components` 5.4.2, both of
2026-02-06 — nine months without a release on 2026-11-13 **[measured, M54]** —, on SvelteKit 2.8.4
and ECharts 5.6.0, fetched by the harness from a committed lockfile and installed offline with
`npm ci --offline --ignore-scripts` (§2.2, §5).

**How it carries data [assumed, probe A1].** Evidence runs its *sources* at `npm run sources`, writes
their results as Parquet into its static folder, runs the page queries at build time to prerender
them — `@evidence-dev/universal-sql` 3.0.1 serialises each result as Arrow IPC under
`.svelte-kit/output/prerendered/dependencies/api/prerendered_queries/`, and the page's
`+layout.js` reads those files back in the browser —, and runs the queries again in the browser on
DuckDB-WASM, whose database and worker live at module scope in its browser client, with the WASM and
worker files imported as Vite assets. That is read from the pinned source by rounds 1 to 4 of the
review
([`cache-duckdb.js`](https://cdn.jsdelivr.net/npm/@evidence-dev/universal-sql@3.0.1/src/cache-duckdb.js),
[`+layout.js`](https://cdn.jsdelivr.net/npm/@evidence-dev/evidence@40.1.8/template/src/pages/+layout.js),
[`browser.js`](https://cdn.jsdelivr.net/npm/@evidence-dev/universal-sql@3.0.1/src/client-duckdb/browser.js)),
not run. Probe A1 builds the clear mode, with the clear-mode fixture, in its own work tree (§2.2),
before the encrypted route, and lists every carrier the fixture's rows and results land in —
Parquet, the prerendered Arrow, SvelteKit's fetched-data scripts, values inlined into HTML, JSON or
devalue, anything else —; each becomes a control of §2.5.5. A1 is also the record of whether
Evidence, as it comes, runs report queries at build time, and says so only from query evidence: a
prerendered query result with the clear-mode fixture's rows in it, at the cache path above
(FPROTO-4-01).

**The encrypted route [planned].** No source holds data: the only source is empty — the zero-row
Parquet of §2.2, if Evidence needs one — or absent if Evidence allows, and the package is not in the
build. A Svelte component of the page fetches the manifest and the envelope at run time, opens it
with `web/envelope.mjs` after submit and loads the Parquet into Evidence's DuckDB-WASM instance; the
chart and the tables are Evidence's components, fed by page queries over that table. Each step is a
probe, in this order — the same order as §7:

| Probe | Question | If no |
|---|---|---|
| A6 | Does the build install and run with `npm ci --offline --ignore-scripts` — run **first**, before any script of a dependency can run? | The scripts it needs, by package, recorded from `npm query` and run alone with `npm rebuild <package>`, offline, in the sandbox |
| A1 | In the clear mode, with the clear-mode fixture, where do the rows and results land, and does it query them at build time? | — (it is a measurement) |
| A7 | Can Evidence load DuckDB-WASM 1.32.0's WASM and worker from jsDelivr, pinned, instead of from the page's origin (N94)? | Through a patched module — a cost, recorded. If no arrangement does, the engine is served from Hosting: recorded as Evidence's cost — the quota of N2, the delivery condition of §2.7, and the engine's bytes in the artifact `verify` judges, where §2.1's draw may then end exhausted, which is reported as such |
| A2 | Can page code reach Evidence's DuckDB-WASM instance through a public module, with no patch — to register the Parquet after submit, and at logout to terminate its worker? | Through a patched module (`patch-package`) — a cost, recorded |
| A3 | Does the build succeed with only the allowlisted inputs, prerendering no query result — no `prerendered_queries` file with rows —, when a page query names a table that exists only after login? | Queries moved from markdown into the component; Evidence's SQL blocks lost — "missing". If no arrangement builds and delivers the page, **the encrypted route is not possible**, with the output that shows why — the build's own error, kept apart from a sandbox limit, which is fixed in the harness first |
| A4 | Do the page queries re-run when the table appears and when the filter or the month changes? | A manual refresh through the component — recorded |
| A5 | Do Evidence's chart and tables take the result of a query run by our own code? | Charts written by hand — Evidence reduced to a layout, recorded as "missing" |

A4 and A5 run on the assembled artifact; a change they force rebuilds Evidence, which sends the work
back to the draw (§2.1, §7). A fork of Evidence is out of scope: if the page needs one, the
candidate's result is "not possible without a fork", with the probe that showed it.

## 4. Candidate B — a build of our own

**What it is [planned].** No framework and no bundler: a static HTML page and plain ES modules —
the envelope's reader, a small report runner, the page —, DuckDB-WASM 1.32.0 and the chart library
loaded from jsDelivr at the URLs and digests of its `cdn.json` (§2.4), with subresource integrity
where the loader allows it, and a build step in Python that copies the files and names them by
content hash (PLAN §3.4, "versions are bound"). It installs nothing from npm.

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
and their `pt-BR` formatting, the empty-state text, the loading state, the logout of §2.3 item 7 —
each counted (§6).

## 5. Safety of the build

Pinning is not isolation: an exact lockfile still runs whatever its packages' scripts do, and
`env -i` empties the environment but leaves the filesystem — the home folder with its credentials,
the checkout, the publishing tools — within reach. So **[planned]**:

- Every npm package pinned, with its lockfile committed under the candidate's folder, its tarballs
  fetched by the harness (§2.2) and installed offline by `npm ci --offline --ignore-scripts`, always
  first (A6); a script found necessary is run alone, by package, offline, and recorded.
  `node_modules/`, `.evidence/`, `runs/`, `clear/` and the build outputs are ignored by Git.
- **Installs and builds run in a sandbox**: `bubblewrap` (0.6.1 on this machine), in a work folder
  assembled from the allowlist of §2.2, bound read-write and the only thing writable; the system's
  `/usr` and the TLS and DNS files bound read-only; an empty `HOME` on a `tmpfs`; the real home
  folder, the checkout, `prototypes/framework/clear/`, `~/.config`, `~/.ssh`, the Codex and Docker
  sockets and folders **not bound at all**. The clear mode runs in a sandbox of its own, with its own
  work folder and cache.
- **What the sandbox inherits is named, not left over**: `--clearenv`, then only `PATH`, `HOME`,
  `LANG`, `TZ` and the npm cache variable set explicitly; `--unshare-pid` with its own `/proc`, so no
  process of the host is visible; `--unshare-ipc`, `--unshare-uts`, `--new-session` and
  `--die-with-parent`; the harness starts it with every file descriptor beyond 0, 1 and 2 closed; and
  **`--unshare-net` in every phase that runs package code**, install and build alike. The builder
  output is copied out of the work folder by the harness, outside the sandbox. The only network
  access of the route is the harness's fetcher, which runs no package code.
- **The sandbox is proved before its first use, through the same wrapper the phases use**: a probe
  stats — never reads — the real home folder, `~/.config/gcloud`, `~/.config/configstore`, `~/.ssh`,
  the checkout's `.git`, `prototypes/framework/clear/` and the Docker socket, by their absolute host
  paths, and must get "no such file" for each; it stats a sentinel file the harness planted in this
  session's scratch folder, and a planted fixture file under `clear/`, and must find neither; it
  reads its own environment, and a synthetic token the harness put in **its own** environment before
  starting the sandbox must be absent; it lists `/proc`, and no PID of the host may appear; it lists
  its open file descriptors, and only 0, 1 and 2 may; it tries to write outside the work folder, and
  must fail; it tries to reach the registry and a listener the harness opened on the host's
  loopback, and must reach neither. Each check is shown to fail on a wrapper with the corresponding
  option removed — round 4 showed the loopback reachable with the network shared and refused with
  `--unshare-net` (FPROTO-4, its §5). No real credential is read by the probe.
- What is left is written as it is (N95): a compromised dependency could still write something
  misleading into its own output, which the oracle would inspect but not explain, and a kernel or
  `bubblewrap` flaw is not defended against.
- No prototype runs in CI and none enters `make check`. **One entry point runs the comparison**,
  `make prototype` (FPROTO-5-08): it fetches and builds what is missing — through
  `make prototype-build-own` and `make prototype-build-evidence`, which only fetch, build in the
  sandbox and archive a builder output —, and then draws, assembles, runs the oracle, the browser
  check and the measures. Its state is one file, `prototypes/framework/runs/state.json`, ignored by
  Git, keyed by **identities, not only digests** (FPROTO-6-07): each build invocation's own id and
  its build input — the allowlist's digest —, the digests of the two final builder outputs, the
  harness inputs that judge or time them — the commit of `prototypes/framework/`, the release
  declarations, `cdn.json`, the lockfiles, the sandbox wrapper —, the draw, the package's digest and
  the measures taken with all of them. **Any** build invocation of either candidate invalidates the
  draw, both artifacts and both sets of measures, even when it reproduces the same bytes, and so
  does a change to any harness input; the comparison is reported only when both artifacts carry the
  same package digest under the same harness inputs, and a candidate whose encrypted route is not
  possible leaves it explicitly incomplete. The first comparison, a byte-identical rebuild and a
  declaration change are each shown to give a fresh comparison and never a stale one. The inspection's Python libraries — `pyarrow`,
  `brotli`, `zstandard` — go in a dependency group of their own, which `make check` does not install.
  `make check` keeps its time and its dependencies.
- The prototypes import `bi_como_codigo` and `web/envelope.mjs` as they are; they change neither.

## 6. What is measured of each

| Measure | How |
|---|---|
| The criterion | The verdict of §2.5.4 over every run of the encrypted route, with each stage's class, the inspection's findings and the browser's; the controls of §2.5.5, each with its expected diagnosis; A1's record of the clear mode |
| The page works | The browser check of §2.6: a wrong password opens nothing; cells equal to the oracle after login, under each filter and month, G and Z told apart, `order_count` only native; logout ends the session's context; the check's own refusals of the altered DOM and of the mutant |
| Lines we wrote | Per file, split into report declaration, glue and configuration |
| Dependencies | Packages in the lockfile; size of `node_modules`; time of the fetch and of the offline install from an empty cache; scripts that had to run (A6) |
| Build | Time; files and bytes of the builder output; whether the engine is in it (A7) |
| The gate's lists | Lines of the inclusion list and extensions of the media types the artifact needs |
| The draw | Seed, *k*, the calendar window, rejections by needle class and inspection, the package's digest (§2.1) |
| First load | §2.7: encoded bytes observed by the login box and by the summary, and completed responses, cold, by origin, wire and raw, with what was served from cache |
| Navigation to summary, submit to summary | §2.7: median and range of five cold and of five warm journeys, apart, with the clock's error |
| What was missing | Each probe answered "no", with its output, and each workaround |
| Upkeep | Latest release and its date; the licence |

What 2.5 owns — keyboard, focus, 360 px, themes, the M5 rule — is not measured here; a candidate that
plainly cannot reach one of them is reported as such, with the observation behind it.

## 7. The order of the work

1. **The ground, before either candidate [planned]**: the sandbox and its probe (§5); the fetcher;
   the allowlist and its check (§2.2); the fixture's shape and generator, with its shape checks and
   the coverage assertion, on a throwaway seed, and the G mutant's own check; assembly with its own
   validation; the harness and its classification (§2.5.1); the inspection, the browser collection
   and the verdict function; every control of §2.5.5 that needs no candidate, on hand-made outputs.
2. **The clear mode, first**: the clear-mode fixture, then each candidate's clear build in its own
   sandbox — A6 and A1 for Evidence —, and the controls built from its carriers.
3. **The encrypted route**: Candidate B's builder output, archived; Candidate A's, through probes
   A7, A2 and A3, in that order, each "no" recorded and the next probe run where it still can, until
   its builder output is final, archived. No measured fixture exists yet.
4. **The draw**, once, against both builder outputs; the package; both artifacts assembled; the
   G mutant derived, sealed and assembled for B.
5. On both artifacts: A4 and A5 for Evidence; the controls on each candidate's own builder output;
   the browser check and its proof. A rebuild of either candidate here sends the work back to step 4.
6. The measures of §6 under §2.7, in one sitting per candidate, on this machine, on the artifacts of
   step 4.
7. The results written in §10, and the implementation handed to Codex with the `review` skill.
8. The Owner chooses; the ADR is the Owner's.

## 8. Choices taken in this plan

| Choice | Taken | Alternatives | Why |
|---|---|---|---|
| What the oracle guards against | Ordinary behaviour of the frameworks, libraries and browser, and our reviewed page code (N95) | Also code turned against the oracle | The Owner's choice: the stage decides between frameworks by what they do on their own; deliberate deception by our own code is a review matter, not an oracle one |
| The fixture's shape | P01's real columns, invented values, 61 months and 60 categories, with G, Z and the partial month in whole groups | 2.2b's three-column fixture; the 13 months of revision 3 | The page needs months, channels and categories to show what a framework costs; counts of five digits or more keep the gate's substring search from deciding by chance; whole groups keep every summary cell multi-row |
| The fixture's values | Drawn after the encrypted builds, against both builder outputs with both inspections, with *k* free; a clear-mode fixture of its own | Fixed values; public values; one fixture for both modes | `verify` searches substrings, and a fixed value can be in a bundle by chance; drawn afterwards, the measured fixture cannot have been read by those builds; `public_values.json` keeps meaning "public by design" |
| Where the engine loads from | jsDelivr, pinned, in both (N94) | Evidence's own origin | N2 and §3.4 already say so, for the quota; its 34 MB hold almost every short integer, which the gate would read as data |
| How dependencies install | Fetched by the harness, installed and built offline | `npm ci` with the network open in the install phase | No package code then runs with a route to anything the machine serves (FPROTO-4-01) |
| Where the package enters | After the build, by the harness, validated on its own and bound to the drawn fixture | In the build's static folder | A build with the package in reach can open it with the public password and leave no trace; a package validated apart from `verify` is recognised even when `verify` stops on form |
| The oracle | The gate's own `verify`, the carrier inspection by role and the browser observed from before its first script, writes included, under one verdict | `verify` alone; a differential build | `verify` is what will judge the chosen framework in the publishing workflow, but cannot see a compressed, encoded or binary value; the differential of revision 2 could not see a result equal for every fixture |
| Logout | Terminate the engine's worker, then `location.replace` | Drop the tables | A dropped table leaves the registered file in the worker; a replaced page leaves one history entry and nothing of the session to check object by object |
| Where `order_count` shows | Only in a detail table at the view's grain | In the summary, per row | No summary cell keeps the grain at which the count is defined (M4) |
| Isolation | `bubblewrap`, with an allowlisted work folder, a named environment, its own PID namespace, no home folder, no checkout, no clear mode and no network | `env -i`; a container | `env -i` is not a sandbox; `bubblewrap` is on the machine and binds only what is named; Docker's daemon runs as root and is itself a credential |
| B's chart library | Vega-Lite, as SVG | ECharts; Observable Plot | §4 |
| B's loading | jsDelivr, pinned by `cdn.json` | Vendored copies | PLAN §3.4 already loads the engine from jsDelivr; vendoring is measured as a cost only if SRI cannot be applied |
| Where they live | `prototypes/framework/`, tracked, not published | A branch; a scratch folder | Codex reviews what was measured; the chosen one moves to `site/` in 2.5, the other stays as the record of the comparison |

## 9. Not verified, and assumptions

- **Outside the oracle, by N95**: page code of ours written to deceive it, and a compromised
  dependency. Our page code is reviewed by Codex with the implementation; the dependencies are
  pinned by lockfile and digest and run with no network.
- **[assumed]** Evidence's data path as described in §3, read from its source by the reviewer, not
  run — probe A1 measures it.
- **[assumed]** that Evidence installs and builds offline from a fetched cache (A6) and builds its
  page with only the allowlisted inputs (A3); if not, its encrypted route is not possible, and that
  is a result, not a defect of the plan.
- **[assumed]** that Evidence can load its engine from jsDelivr (A7) and that its worker can be
  terminated from page code (A2).
- **[assumed]** that DuckDB-WASM 1.32.0 from jsDelivr runs in headless Chrome from a page served on
  `127.0.0.1`, with its worker created from a blob of the CDN script.
- **[assumed]** that each candidate's artifact can hold the package as `verify` finds it: `_package`
  takes the one `manifest.json` of the whole folder, so a framework that writes a `manifest.json` of
  its own is refused by form. That is a cost of the candidate, with the setting that removes it; the
  gate is not changed for a prototype.
- **[assumed]** that the draw of §2.1 converges within 1,000 draws against both builder outputs with
  both inspections; if not, the run stops with the draw exhausted, reported. What a collision means
  for real data at 2.5 — a real count of three digits that a bundle happens to hold — is a question
  for the gate then, not answered here.
- **[assumed]** that the DevTools protocol attaches every target before its first script, reports
  every execution context, returns every body and enumerates every store §2.5.3 needs; what it does
  not is inconclusive. That a candidate decrypts only through WebCrypto: a decryption of its own
  would escape `PREMATURE_DECRYPT`; within N95, the page's only path is `web/envelope.mjs`.
- **[assumed]** that Hosting compresses text as the local server of §2.7 does; wire bytes from the
  local origin are an estimate of Hosting's, and raw bytes are reported beside them.
- **[measured, partly]** `bubblewrap` 0.6.1 runs unprivileged on this kernel with the home folder not
  bound (the author's answer to round 1) and hides a host sentinel; with no `--clearenv` an
  inherited token stays visible, and with no PID namespace the parent's PID does (FPROTO-2, its §5);
  a host loopback listener is reachable with the network shared and refused with `--unshare-net`
  (FPROTO-4, its §5). The full wrapper of §5 is not yet run.
- **[measured, by the reviewer]** each of the row counts 220 to 226 occurs in each of DuckDB-WASM
  1.32.0's EH and MVP WASM files, and `contract.inspect` refuses them there (FPROTO-3, its §5); none
  of the six counts of §2.1 does, in either file or either pinned worker (FPROTO-4, its §5).
- Not measured, and not in this stage: the latency on a phone, a slow network, browsers other than
  Chrome.

## 10. Results

**Pending** — written when §7's steps 1 to 6 have run.
