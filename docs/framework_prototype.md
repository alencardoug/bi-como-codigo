# The framework prototype — stage 2.3

> **What lives here:** how stage 2.3 compares the two framework candidates of N3 on the same P01
> page — the fixture both read, the page both build, the oracle that fails a candidate whose finished
> output or browser state carries clear report data, what is measured of each and under what
> conditions, the probes each candidate needs, how its dependencies are kept away from this
> machine's credentials, the order of the work — and, once it runs, the results the Owner chooses
> from.
>
> **What does not:** why there is a comparison and who chooses — [PLAN §1.2](../PLAN.md#12-the-decisions),
> N3, and [§7](../PLAN.md#7-what-is-still-decided-at-the-right-moment); the envelope the page opens —
> [`encryption_envelope.md`](encryption_envelope.md); the package-to-artifact gate whose `verify` is
> one half of the oracle here, its formats and its limits — [`package_gate.md`](package_gate.md); the
> complete P01 report, with its accessibility, narrow screens, themes and the partial-month and
> empty-slice rules in full — stage 2.5; real report data — stage 2.4.

| Field | Information |
|---|---|
| Date | 2026-11-20 — revision 3, answering round 2 of Codex's review (FPROTO-2-01 to -08). Revision 2, the same day, answered round 1 (FPROTO-1-01 to -06); revision 1, 2026-11-13, went to round 1 |
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

**How the criterion is met here.** Revision 2 tried to prove, after the fact, that a build which
had the sealed package in reach had not opened it; round 2 showed that a build-time query whose
result is the same for every fixture, or is discarded, leaves no trace to compare (FPROTO-2-01).
So the question is moved before the build: **the build never receives report data** — neither the
clear fixture nor the sealed package —, and the package is placed in the finished output by the
harness afterwards (§2.2). A candidate that cannot build its page without the report in reach
runs report queries at build time by necessity, and fails the criterion on that, with the probe
that showed it (A3). What can still carry clear data is then the browser, after login, which §2.5.3
judges.

## 2. The common ground

### 2.1 The fixture

P01 is the view `monthly_revenue_by_channel_and_category`
([eng_dados at `f86b9fb`](https://github.com/alencardoug/mvp_eng_dados_1/blob/f86b9fb/dbt/models/consumption/monthly_revenue_by_channel_and_category.sql)):
`year_month`, `year_number`, `month_number`, `sales_channel_name`, `channel_type`,
`root_category_name`, `category_name`, `order_count`, `unit_count`, `gross_revenue_amount`,
`discount_amount`, `net_revenue_amount`, at the grain `[year_month, sales_channel_name,
category_name]`. The fixture keeps those names, in that order, and invents every value
**[planned]**. Its shape is fixed except for one parameter; its values are drawn.

**The shape.**

- 13 consecutive months; 3 channels, `fixture_canal_a` and `fixture_canal_b` of one channel type and
  `fixture_canal_c` of another; 3 root categories, `fixture_raiz_1` to `_3`, with 2 categories each,
  `fixture_cat_1a` to `fixture_cat_3b`. A full month has 18 rows.
- **The gap, G**: `fixture_canal_c` has no row of `fixture_raiz_3` — neither of its categories — in
  the fifth month. Filtered on that channel, the page's summary has an empty cell there (§2.3).
- **The zero, Z**: `fixture_canal_b` has both rows of `fixture_raiz_2` in the seventh month, with
  units and a gross revenue, and a discount equal to that gross revenue: `net_revenue_amount` is
  `0.00` on both. Filtered on that channel, the summary cell exists and is zero — the case the
  page must not confuse with G.
- **The partial month**: the last month has no row of `fixture_canal_c` and *k* rows of the other
  two channels, 6 ≤ *k* ≤ 12, with smaller amounts. The page shows a fixed notice for it; the rule
  of M5 itself is 2.5's.
- 214 + *k* rows — 13 × 18, less the 2 of G and the 18 − *k* missing from the partial month: 220
  to 226. *k* is the one parameter of the shape, and it exists for the draw below (FPROTO-2-03).

**The values.** Drawn deterministically by `prototypes/framework/fixture.py` from a recorded seed,
with the control totals computed in Python with `decimal`, as `tests/site_fixture.py` does:

- amounts with two decimals, each with at least three significant digits and each distinct across
  the three amount columns, at least ten of them with a fraction ending in `0` — so that the
  JavaScript spelling `1234.5` of `1234.50` is exercised —, **with Z's exceptions, and only
  those** (FPROTO-2-05): on each of Z's two rows the discount equals the gross revenue and the net
  is `0.00`; the two `0.00` are neither distinct nor eligible needles, which `contract.needles` and
  the coverage assertion account for;
- `order_count` and `unit_count` integers, each distinct across the fixture, with at least three
  significant digits; **no sum of `order_count` over the rows of a populated summary cell, under any
  filter, equals a value the page displays** — so that a summary count invented by summing is told
  apart from a native one (§2.6);
- the calendar too: the 13 months are a window chosen by the draw.

The generator checks the shape — 13 months, 214 + *k* rows, no row in G, two rows in Z with the
exceptions above, *k* rows in the last month — and fails before sealing if any does not hold.

**The draw against the baseline** (FPROTO-2-03). `verify`'s inspection searches each eligible value,
the totals object and the derived totals as byte substrings in every non-envelope file of the output
([`package_gate.md` §6](package_gate.md)). A candidate's own code — a bundle, the DuckDB WASM that
Evidence ships — can hold such bytes by chance: round 2 measured the row count `226` 33 times in
DuckDB-WASM 1.32.0's EH WASM, which alone makes `verify` refuse an honest output. Because the build
never receives report data (§1, §2.2), the **builder output** — what a candidate's build writes, before
the harness adds the package — does not depend on the fixture by construction, and it is byte for
byte the non-package part of the artifact `verify` judges. That makes it the baseline, with no
circularity:

1. each candidate is built once; its builder output is archived (§2.5.2);
2. the generator draws a fixture, seals it, computes `contract.needles` on the opened payload — the
   values, the totals object, the row count, the sums — and searches the full set in every file of
   **both** candidates' builder outputs;
3. a colliding value is redrawn; a colliding row count changes *k*; a colliding calendar moves the
   window. At most 1,000 draws in all, recorded with the seed and every rejection by needle class;
4. if no draw is clean — a collision the shape cannot avoid —, the result is a **harness limitation**,
   reported with the colliding class and file, never a failure of the candidate and never cleared by
   `public_values.json`, which keeps meaning "public by design".

Rebuilding a candidate after the draw — a setting changed, a probe answered — changes its builder
output, and the draw is redone against the new one before `verify` runs.

**The coverage assertion.** Before any build, the harness computes `contract.needles` on the
fixture's opened payload and asserts that every eligible number contributes each of its spellings
and every text of three characters or more contributes itself, with no public value excluding any —
the count, after `needles`' own deduplication, is printed and compared with the one computed from
the fixture alone.

The SQL types are written in a contract of the prototype's own, in the format of
`release/contract.json`, with the grain above and the sums on `unit_count` and the three amounts —
not on `order_count`, which is not additive across categories (M4). The repository's `release/`
is not touched.

### 2.2 The package, and where it enters

`prototypes/framework/fixture.py` seals the fixture with the envelope's producer
(`envelope.encrypt_package`) under a profiles declaration of the prototype with one profile,
Diretoria, with the showcase's public password (N22), entitled to P01. Round 1 of the review ran
the producer and `validate_manifest` on one profile, and on a profile with no report, and both pass
(FPROTO-1, its §4): Logística stays out — the access matrix is 2.6's —, and step 1 of §7 repeats
that run here.

**The package never enters the build** (FPROTO-2-01). The build's work folder holds the candidate's
sources and `web/envelope.mjs`, and nothing derived from the fixture: no clear file, no sealed
package, no query cache, no generated source. The harness asserts it before each build — no file
of the work folder holds a needle, a Parquet or payload magic, or an envelope's magic. The page
fetches the package at run time from a fixed path, `package/`, which the build leaves empty. After
the build, a step of the harness outside the sandbox copies the builder output into the artifact
folder and the sealed package into its `package/`; the package's files are the ones the producer
wrote, unchanged, and `verify` validates them. The public password is no shortcut: a page or a
build helper that holds it has nothing to open at build time.

Both pages open the package with the same reader, `web/envelope.mjs`, imported as is: login derives
the key, unwraps the data key and returns the control totals and the Parquet; the Parquet is then
registered in a DuckDB-WASM instance and queried there. The envelope's reader is not re-implemented
in either candidate.

### 2.3 The page

The same page, in Portuguese, in both **[planned]**:

1. a login box with the Diretoria password; a wrong password shows that nothing opened;
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
   its registered files — and then replaces the page with the login page by a full navigation, so
   that no JavaScript object, worker or registered file of the session survives it (FPROTO-2-02).

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

The **artifact** — the builder output with the package added by the harness — is judged by the
gate's `verify` (§2.5.1); the builder output and the artifact are inspected for fixture data
(§2.5.2); the browser is judged before login and after logout (§2.5.3). The verdict combines the
three (§2.5.4), and the controls of §2.5.5 prove each part before its "pass" means anything.

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
<run>/artifact/                        the builder output, with the package in package/
```

and calls `release.verify(<run>/root, <run>/artifact, live=lambda: release.NO_LIVE)`: `verify`
appends `release/` to the root itself. The three shared declarations live once; the two lists are
the candidate's, in the gate's syntax — globs under `site/`, matched against the artifact's paths
with the prefix removed —; the formats are `package_gate.md`'s. Round 2 ran this layout, with a
clean control passing and a clear label refused (FPROTO-2, its §5).

**Whose refusal it is** (FPROTO-2-04). The declarations and the package are the harness's, and only
the files of the builder output are the candidate's. So `verify`'s outcomes are classified by what
they are about, not by being a `release.Refused`:

| Outcome | Class |
|---|---|
| An exception that is not `release.Refused` — a missing declaration, an I/O error | `HARNESS_ERROR` |
| A refusal of the declarations — `public_values_invalid`, a contract or profiles refused, `declarations_agree` | `HARNESS_ERROR` |
| A refusal of the package — the manifest refused, an envelope missing, stray or corrupt, `inventory_exact`, `entitlements_exact`, `check_package`, a report that cannot be checked | `HARNESS_ERROR` |
| A file outside the inclusion list, an extension outside the media types, a `.map` file, a `sourceMappingURL` reference, a path under `__/`, a second `manifest.json` | `FORM` |
| A clear value or totals, a Parquet or payload magic outside an envelope, a data key in the clear — in a file of the builder output | `CONTENT`, unless the draw's baseline holds that needle in that file, which is then a `COLLISION` |
| No refusal | `PASS` |

The classification reads the refusal's message against the gate's fixed messages and codes; a
message it does not know is `HARNESS_ERROR`, so that an unknown refusal is never read as the
candidate's pass or as its failure. A `HARNESS_ERROR` or a `COLLISION` stops the run; it is fixed in
the harness or in the draw, and the run is repeated — it is never written as a cost or a failure
of the candidate. Step 1 of §7 proves each class with its own control (§2.5.5).

#### 2.5.2 The builder output and the artifact, inspected

**Outputs are kept.** Every builder output is archived, as a tarball with its SHA-256, the moment
its build ends and before any check — under `prototypes/framework/<candidate>/runs/`, ignored by
Git —, and so is every artifact. A setting produces a new run; the earlier archives stay and keep
their verdicts (§2.5.4).

**The carrier inspection [planned].** `prototypes/framework/inspect_output.py` reads a set of files
and names the carrier of any fixture value it finds. It runs on the builder output — where, by §2.2,
nothing can be found, and finding something means the harness let data into the build —, on the
artifact outside its validated envelopes, and on what §2.5.3 collects in the browser. Its needles
are the fixture's values **and the results of the page's queries** — every summary and detail cell
under every filter, from the oracle of §2.6 —, since a cache of a query holds results, not rows. For
each file, recursively to a depth of three:

| Layer | What is done |
|---|---|
| Decoders | gzip, zlib and raw deflate; brotli; zstd; base64, standard and URL-safe, on runs of 16 characters or more; hex on runs of 32 or more; percent-encoding; JSON and JavaScript string escapes; HTML entities — each decoded result is inspected again |
| Structured carriers | JSON, and Svelte's devalue as JSON-like text, parsed — SvelteKit's fetched-data scripts (`data-sveltekit-fetched`, with or without `data-b64`) among them —: every number compared **as a number** with the needles, so `1234.5` matches `1234.50`; Arrow IPC, stream and file, and Parquet, parsed with `pyarrow`: every cell compared as a value |
| Text | every text needle as a byte string; every amount with a fraction in each spelling of `contract.spellings` and in its shortest JavaScript spelling — integers are compared only inside structured carriers, where a match is a value and not a fragment of code |
| Binary numbers | every amount with a fraction as the 8 bytes of an IEEE 754 double, both byte orders, and as the 16 bytes of an Arrow `decimal128` at scale 2 |
| Envelopes | a file of `package/` that `verify` validated against the manifest is recorded as an envelope and not inspected further; any other file there is inspected like the rest |
| What remains | a binary file byte-identical to a file of the candidate's locked dependency tree is recorded and not inspected further; any other binary that no layer decodes is **inconclusive** |

Each finding carries its code — `INSPECT_TEXT`, `INSPECT_NUMBER`, `INSPECT_ARROW`, `INSPECT_PARQUET`,
`INSPECT_BINARY` — and the decoding path, never the value. The decoder list is closed: a carrier
outside it is not "clean", it is inconclusive. In the encrypted route the list is a second line,
not the argument: §2.2 keeps data out of the build; the list names the carrier when a control or
the clear mode puts data in.

#### 2.5.3 In the browser

The browser check of §2.6 collects, through the DevTools protocol, with auto-attach on, so that the
page, its workers and its frames are all reached (FPROTO-2-02):

- **before login**, where nothing decrypted may exist: the body of every network response of every
  target, and the contents of CacheStorage, IndexedDB, `localStorage`, `sessionStorage` and the
  scripts of any service worker;
- **after logout**: the same storage again; the list of targets, which must hold no worker or frame
  of the session — a DuckDB worker still alive after logout is a finding by itself, whatever it
  holds —; and the page's execution context, which must be a new one, from the navigation of §2.3
  item 7 — not the session's, and not the session's page restored from the back-forward cache.

Everything collected goes to the carrier inspection of §2.5.2. A value found fails the criterion,
as a build-time one would: a framework that caches query results in the browser, or keeps the
session's data alive after logout, carries clear data outside the envelope. **A response whose body
the protocol could not return, a target that could not be attached, or a storage that could not be
read is inconclusive, never clean.** What is not judged here, and is said so: the browser's own
HTTP cache of the envelope, which is ciphertext, and memory the operating system has not yet
reclaimed.

#### 2.5.4 The verdict

One function, `verdict(runs)`, over every archived run of the encrypted route of a candidate, tested
in step 1 of §7. Its precedence, first match wins (FPROTO-2-04):

1. **fails the criterion** — in any run: `verify`'s `CONTENT`; a finding of the carrier inspection
   in the builder output, the artifact or the browser; a session's worker or context alive after
   logout; or the candidate cannot build its page with no report data in reach (A3). A later run
   never undoes it: a setting that removed the carrier does not remove the run that showed it;
2. **stopped** — the latest run ended in `HARNESS_ERROR` or `COLLISION`: no verdict until it is
   repeated;
3. **not established** — any run, earlier or latest, has an inconclusive file, target or storage
   that no later evidence resolved. Resolving means re-inspecting **that archived output** with the
   decoder that reads it, or showing by a run that the carrier is absent *and* that its absence is
   not a setting that only hid it; a later run without the carrier alone does not resolve an
   earlier one;
4. **a cost** — the latest run's `verify` refused by `FORM`, and nothing above: cleared by a setting
   of the candidate's build, never by changing `verify`; the setting is recorded, the content of the
   output that carried the form refusal was judged in its own run, and the inclusion list and media
   types are the narrowest that cover the artifact, their length a measured cost (§6). A form
   refusal no setting clears means the candidate cannot go through the publishing workflow, and it
   fails on that, said apart from the criterion;
5. **passes** — `verify` passed, nothing was found and nothing is inconclusive, in the latest run,
   and no earlier run is in 1 or 3.

#### 2.5.5 The controls

No part of the oracle is trusted until it has failed something real. Each control has **one** leak,
in one carrier, and asserts its own diagnosis — the class of `verify`, the carrier code of the
inspection, or the browser finding — even where another part trips too (FPROTO-2-04):

| Control | Built from | Expected |
|---|---|---|
| Clean | the candidate's builder output and the package | `verify` `PASS`; no finding; verdict passes |
| Harness classes | a missing declaration; a malformed `public_values.json`; a manifest refused; an envelope corrupted | `HARNESS_ERROR` for each, with its cause; verdict stopped |
| Collision | an artifact holding DuckDB-WASM 1.32.0's EH WASM, with a fixture whose row count is `226` (round 2) | the draw rejects *k* = 12; forced, `verify` refuses and the class is `COLLISION`, not `CONTENT` |
| A fixed label | the clean artifact plus a file holding one fixture label | `verify` `CONTENT`; inspection `INSPECT_TEXT` |
| A varying value, one carrier each | the clean artifact plus one file: an amount in `pt-BR`; an amount in its JavaScript spelling; Arrow IPC; Parquet; gzip, brotli and base64 of a JSON of rows; JSON-escaped text; a base64 payload in a service worker | the inspection names its carrier; `verify`'s class is recorded beside it — `CONTENT` where its spelling is visible, `PASS` where it is not, which is the gap the inspection is there for |
| Content behind form | a label in a `.map`; a label in a second `manifest.json` | `verify` `FORM`; inspection `INSPECT_TEXT`; verdict fails |
| Carrier nobody listed | rows encrypted under a key the oracle does not hold | inspection inconclusive; verdict not established — and still so after a later run without the file |
| Data in the build | the package placed in the build's work folder | the pre-build assertion of §2.2 refuses to build |
| Browser, one each | a page that writes one result into CacheStorage; one into `localStorage`; a logout that drops the table and keeps the worker with its registered file; a logout with no navigation; a response body withheld | a finding for each of the first four; inconclusive for the last |
| Clear mode | the candidate's natural clear build — Evidence with the fixture as a clear Parquet source; the own build with a page that fetches the clear Parquet | the inspection names every carrier A1 found, each also copied **alone** into a clean artifact and diagnosed there |

The controls run first on hand-made outputs (step 1 of §7), then on each candidate's own builder
output, so that the carriers are the ones the candidate actually writes; A1 supplies them for
Evidence.

### 2.6 The browser check

A Node script drives headless Chrome through the DevTools protocol, as `m49` did, against each
artifact served on `127.0.0.1` (§2.7) **[planned]**. Its oracle is the same queries run by Python's
DuckDB over the clear fixture:

- logs in, waits for the tables, reads their cells from the DOM and compares them with the oracle —
  equal, cell by cell, as text in `pt-BR`;
- applies the filter on "todos", `fixture_canal_a`, `fixture_canal_b` and `fixture_canal_c`, and
  the month selector on the fifth and seventh months, and compares again;
- **G**: under `fixture_canal_c`, the summary cell of the fifth month and `fixture_raiz_3` reads
  exactly "Sem vendas neste recorte."; **Z**: under `fixture_canal_b`, the cell of the seventh month
  and `fixture_raiz_2` reads `R$ 0,00`; the notice of the last month is present;
- **`order_count`**: the detail cells equal the native values of the fixture; the summary has no
  count column, and no summary element holds any of the sums §2.1 made distinct;
- logs out, and runs §2.5.3's after-logout collection;
- records every network request of every target: only the local origin and, for the own build,
  `cdn.jsdelivr.net` at the pinned paths.

**The check is proved to fail**: its comparator runs again on altered copies of the DOM it read —
G's cell turned to `R$ 0,00`, G's notice blanked, Z's cell turned to the notice, a summed count
written into a summary cell — and must refuse each, for that reason; and the own build is served
once with a fixture mutant whose G is filled with a zero row, and the check must refuse that page
on G.

### 2.7 How the costs are measured

So that bytes and times describe the candidates and not the state of a cache or of the person
running them (FPROTO-1-05, FPROTO-2-06) **[planned]**:

- **Serving.** One local static server for both, written for the prototype: it sends
  `firebase.json`'s headers — `Cache-Control: no-cache` on every file —, and compresses text files
  with brotli or gzip as the request accepts, as Hosting does **[assumed]**. jsDelivr serves itself;
  its encoding is recorded as received.
- **One journey, fixed.** The script navigates; types the password and submits **as soon as the
  password field is present and enabled** — not after a pause, so that work a candidate starts on
  load, as Evidence's `+layout.js` starts its engine, falls inside the measured time and not before
  it —; and waits for the summary.
- **Four timestamps**, from one script injected before any page script runs, in both: navigation
  start, the login box present, `submit`, and the first moment every expected cell of the summary is
  present with its expected text. Two observations are reported, apart: **navigation to summary**,
  what a visitor waits for, and **submit to summary**, with the PBKDF2 derivation of M49 inside.
- **Cold runs.** Five, each in a new Chrome process with a fresh, empty `--user-data-dir`.
- **Warm runs.** In one profile, a priming journey that goes all the way — login, the summary with
  every request of the engine and the package finished, logout —; then five journeys, each in a new
  tab. What carries over is the HTTP cache and whatever origin storage the candidate kept, which the
  §2.5.3 dump lists beside the times. Cold and warm are reported apart, never in one statistic.
- **Bytes.** For every request of every target — page, worker, frame —, from the DevTools protocol:
  origin, `encodedDataLength`, `Content-Encoding`, status, and whether it came from the memory cache,
  the disk cache or a service worker. A request counts toward a cutoff — the login box, the summary
  — if it finished before it; one still in flight at the cutoff is counted apart, as in flight.
  Totals split by origin — the local origin is what Hosting would serve and count,
  `cdn.jsdelivr.net` is not — and, for each local file, its size raw and brotli-compressed.

Every number is kept with its trace — timestamps, requests, cache flags — in the evidence of the
stage.

## 3. Candidate A — Evidence

**Version.** `@evidence-dev/evidence` 40.1.8 with `@evidence-dev/core-components` 5.4.2, both of
2026-02-06 — nine months without a release on 2026-11-13 **[measured, M54]** —, on SvelteKit 2.8.4
and ECharts 5.6.0, installed with `npm ci --ignore-scripts` from a committed lockfile (§5).

**How it carries data [assumed, probe A1].** Evidence runs its *sources* at `npm run sources`, writes
their results as Parquet into its static folder, runs the page queries at build time to prerender
them — `@evidence-dev/universal-sql` 3.0.1 serialises each result as Arrow IPC under
`.svelte-kit/output/prerendered/dependencies/api/prerendered_queries/`, and the page's
`+layout.js` reads those files back in the browser —, and runs the queries again in the browser on
DuckDB-WASM, whose database and worker live at module scope in its browser client. That is read
from the pinned source by rounds 1 and 2 of the review
([`cache-duckdb.js`](https://cdn.jsdelivr.net/npm/@evidence-dev/universal-sql@3.0.1/src/cache-duckdb.js),
[`+layout.js`](https://cdn.jsdelivr.net/npm/@evidence-dev/evidence@40.1.8/template/src/pages/+layout.js),
[`browser.js`](https://cdn.jsdelivr.net/npm/@evidence-dev/universal-sql@3.0.1/src/client-duckdb/browser.js)),
not run. Probe A1 builds the clear mode and lists every carrier the fixture's rows and results land
in — Parquet, the prerendered Arrow, SvelteKit's fetched-data scripts, values inlined into HTML,
JSON or devalue, anything else —; each becomes a control of §2.5.5 before the encrypted route is
attempted.

**The encrypted route [planned].** No source holds data: the only source is empty, or absent if
Evidence allows, and the package is not in the build (§2.2). A Svelte component of the page fetches
the manifest and the envelope at run time, opens it with `web/envelope.mjs` and loads the Parquet
into Evidence's own DuckDB-WASM instance; the chart and the tables are Evidence's components, fed by
page queries over that table. Each step is a probe, in this order:

| Probe | Question | If no |
|---|---|---|
| A6 | Does the build install and run with `npm ci --ignore-scripts` — run **first**, before any script of a dependency can run? | The scripts it needs, by package, recorded from `npm query` and run alone with `npm rebuild <package>`, inside the sandbox |
| A1 | Where do the fixture's rows and results land in the clear mode? | — (it is a measurement) |
| A2 | Can page code reach Evidence's DuckDB-WASM instance through a public module, with no patch — to register the Parquet, and at logout to terminate its worker? | Through a patched module (`patch-package`) — a cost, recorded |
| A3 | Does the build succeed with no report data in reach, prerendering no query result — no `prerendered_queries` file with rows —, when a page query names a table that exists only after login? | Queries moved from markdown into the component; Evidence's SQL blocks lost — "missing". If no arrangement builds without data, the candidate **fails the criterion** (§1) |
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
and their `pt-BR` formatting, the empty-state text, the loading state, the logout of §2.3 item 7 —
each counted (§6).

## 5. Safety of the build

Pinning is not isolation: an exact lockfile still runs whatever its packages' scripts do, and
`env -i` empties the environment but leaves the filesystem — the home folder with its credentials,
the checkout, the publishing tools — within reach (FPROTO-1-06). So **[planned]**:

- Every npm package pinned, with its lockfile committed under the candidate's folder and installed by
  `npm ci --ignore-scripts`, always first (A6); a script found necessary is run alone, by package,
  and recorded. `node_modules/`, `.evidence/`, `runs/` and the build outputs are ignored by Git.
- **Installs and builds run in a sandbox**: `bubblewrap` (0.6.1 on this machine), in a work folder
  that is a copy of the candidate's sources plus `web/envelope.mjs` — never the package (§2.2) —,
  bound read-write and the only thing writable; the system's `/usr` and the TLS and DNS files bound
  read-only; an empty `HOME` on a `tmpfs`; the real home folder, the checkout, `~/.config`, `~/.ssh`,
  the Codex and Docker sockets and folders **not bound at all**.
- **What the sandbox inherits is named, not left over** (FPROTO-2-08): `--clearenv`, then only
  `PATH`, `HOME`, `LANG`, `TZ` and the npm cache variable set explicitly; `--unshare-pid` with its
  own `/proc`, so no process of the host is visible; `--unshare-ipc`, `--unshare-uts`,
  `--new-session` and `--die-with-parent`; the harness starts it with every file descriptor beyond
  0, 1 and 2 closed. The network is open for `npm ci` only, to reach the registry; the build runs
  with `--unshare-net`. The builder output is copied out of the work folder by the harness, outside
  the sandbox.
- **The sandbox is proved before its first use, through the same wrapper the builds use**, in both
  of its modes: a probe stats — never reads — the real home folder, `~/.config/gcloud`,
  `~/.config/configstore`, `~/.ssh`, the checkout's `.git` and the Docker socket, by their absolute
  host paths, and must get "no such file" for each; it stats a sentinel file the harness planted in
  this session's scratch folder, and must not find it; it reads its own environment, and a synthetic
  token the harness put in **its own** environment before starting the sandbox must be absent; it
  lists `/proc`, and no PID of the host may appear; it lists its open file descriptors, and only 0,
  1 and 2 may; it tries to write outside the work folder, and must fail; it tries to reach the
  registry, and must succeed in the install mode and fail in the build mode. Each check is shown
  to fail on a wrapper with the corresponding option removed. No real credential is read by the
  probe.
- What is left is written as it is: a dependency's code still runs with the network open during
  `npm ci` — with nothing of this machine's to send —, and a kernel or `bubblewrap` flaw is not
  defended against.
- No prototype runs in CI and none enters `make check`: each has its own target,
  `make prototype-own` and `make prototype-evidence`, which build in the sandbox, add the package,
  run the oracle and the browser check. The inspection's Python libraries — `pyarrow`, `brotli`,
  `zstandard` — go in a dependency group of their own, which `make check` does not install. `make
  check` keeps its time and its dependencies.
- The prototypes import `bi_como_codigo` and `web/envelope.mjs` as they are; they change neither.

## 6. What is measured of each

| Measure | How |
|---|---|
| The criterion | The verdict of §2.5.4 over every run of the encrypted route, with `verify`'s class, the inspection's findings and the browser's; the controls of §2.5.5, each with its expected diagnosis |
| The page works | The browser check of §2.6: cells equal to the oracle after login, under each filter and month, G and Z told apart, `order_count` only native; logout ends the session's context; the check's own refusals of the altered DOM and of the mutant |
| Lines we wrote | Per file, split into report declaration, glue and configuration |
| Dependencies | Packages in the lockfile; size of `node_modules`; time of `npm ci` from an empty cache; scripts that had to run (A6) |
| Build | Time; files and bytes of the builder output |
| The gate's lists | Lines of the inclusion list and extensions of the media types the artifact needs |
| The draw | Seed, *k*, the calendar window, rejections by needle class (§2.1) |
| First load | §2.7: bytes until the login box and until the summary, cold, by origin, wire and raw, with what was in flight |
| Navigation to summary, submit to summary | §2.7: median and range of five cold and of five warm journeys, apart |
| What was missing | Each probe answered "no", with its output, and each workaround |
| Upkeep | Latest release and its date; the licence |

What 2.5 owns — keyboard, focus, 360 px, themes, the M5 rule — is not measured here; a candidate that
plainly cannot reach one of them is reported as such, with the observation behind it.

## 7. The order of the work

1. **The ground, before either candidate [planned]**: the sandbox and its probe (§5); the fixture's
   shape and generator, with its shape checks and the coverage assertion; the package, repeating the
   one-profile run; the harness and its classification (§2.5.1); the inspection, the browser
   collection and the verdict function; every control of §2.5.5 that needs no candidate, on
   hand-made outputs.
2. Candidate B, which sets the page and the browser check: its builder output, the draw against it
   and Evidence's — for which Evidence is built here once, with no probe yet —, the artifact, the
   controls on its own builder output, the browser check and its proof.
3. Candidate A, probes A6, A1 and A2 to A5 in order; a "no" is recorded and the next probe runs
   where it still can; then its artifact, with the draw redone if its builder output changed, and
   its controls.
4. The measures of §6 under §2.7, in one sitting per candidate, on this machine.
5. The results written in §10, and the implementation handed to Codex with the `review` skill.
6. The Owner chooses; the ADR is the Owner's.

## 8. Choices taken in this plan

| Choice | Taken | Alternatives | Why |
|---|---|---|---|
| The fixture's shape | P01's real columns, invented values, with G, Z and the partial month named | 2.2b's three-column fixture | The page needs months, channels and categories to show what a framework costs; invented values keep "no report data before 2.4" |
| The fixture's values | Drawn against both candidates' builder outputs, with *k* free | Fixed values; public values | `verify` searches substrings, and a fixed value — the row count `226` measured — can be in a bundle by chance; `public_values.json` keeps meaning "public by design" |
| Where the package enters | After the build, by the harness | In the build's static folder | A build with the package in reach can open it with the public password and leave no trace (FPROTO-2-01); one without it has nothing to query |
| The oracle | The gate's own `verify`, the carrier inspection and the browser collection, under one verdict | `verify` alone; a differential build | `verify` is what will judge the chosen framework in the publishing workflow, but cannot see a compressed, encoded or binary value; the differential of revision 2 could not see a result equal for every fixture (FPROTO-2-01) |
| Logout | Terminate the engine's worker, then a full navigation | Drop the tables | A dropped table leaves the registered file in the worker (FPROTO-2-02); a new page leaves nothing of the session to check object by object |
| Where `order_count` shows | Only in a detail table at the view's grain | In the summary, per row | No summary cell keeps the grain at which the count is defined (M4) |
| Isolation | `bubblewrap`, with a named environment, its own PID namespace, no home folder, no checkout and no network at build | `env -i`; a container | `env -i` is not a sandbox; `bubblewrap` is on the machine and binds only what is named; Docker's daemon runs as root and is itself a credential |
| B's chart library | Vega-Lite, as SVG | ECharts; Observable Plot | §4 |
| B's loading | jsDelivr, pinned | Vendored copies | PLAN §3.4 already loads the engine from jsDelivr; vendoring is measured as a cost only if SRI cannot be applied |
| Where they live | `prototypes/framework/`, tracked, not published | A branch; a scratch folder | Codex reviews what was measured; the chosen one moves to `site/` in 2.5, the other stays as the record of the comparison |

## 9. Not verified, and assumptions

- **[assumed]** Evidence's data path as described in §3, read from its source by the reviewer, not
  run — probe A1 measures it.
- **[assumed]** that Evidence can build its page with no report data in reach — A3; if not, it fails
  the criterion, and that is a result, not a defect of the plan.
- **[assumed]** that Evidence's DuckDB-WASM worker can be terminated from page code — A2.
- **[assumed]** that DuckDB-WASM 1.32.0 from jsDelivr runs in headless Chrome from a page served on
  `127.0.0.1`, with its worker created from a blob of the CDN script.
- **[assumed]** that each candidate's artifact can hold the package as `verify` finds it: `_package`
  takes the one `manifest.json` of the whole folder, so a framework that writes a `manifest.json` of
  its own is refused by form. That is a cost of the candidate, with the setting that removes it; the
  gate is not changed for a prototype.
- **[assumed]** that the draw of §2.1 converges within 1,000 draws against both builder outputs; if
  not, the result is a harness limitation, reported. What a collision means for real data at 2.5 — a
  real row count or value of three digits that a bundle happens to hold — is a question for the gate
  then, not answered here.
- **[assumed]** that the DevTools protocol returns the bodies and attaches the targets §2.5.3 needs;
  what it does not return is inconclusive.
- **[assumed]** that Hosting compresses text as the local server of §2.7 does; wire bytes from the
  local origin are an estimate of Hosting's, and raw bytes are reported beside them.
- **[measured, partly]** `bubblewrap` 0.6.1 runs unprivileged on this kernel with the home folder not
  bound (the author's answer to round 1) and hides a host sentinel; with no `--clearenv` an
  inherited token stays visible, and with no PID namespace the parent's PID does (FPROTO-2, its §5).
  The full wrapper of §5 is not yet run.
- Not measured, and not in this stage: the latency on a phone, a slow network, browsers other than
  Chrome.

## 10. Results

**Pending** — written when §7's steps 1 to 4 have run.
