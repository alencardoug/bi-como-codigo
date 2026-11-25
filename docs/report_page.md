# The report page — stage 2.5

> **What lives here:** the short plan of stage 2.5 ([N115](../PLAN.md#12-the-decisions)): the
> complete P01 report on the page of ADR-0004. It covers what is built, where it lives, how each
> part of the criterion is checked, the order of the work, and the decisions it asks of the Owner.
>
> **What does not:**
> - the criterion of the stage — [PLAN §6.2](../PLAN.md#62-the-stages), stage 2.5;
> - why the page is our own, and what 2.3 measured of it —
>   [ADR-0004](adr/0004-build-the-reports-and-the-portal-on-a-page-of-our-own.md) and
>   [`framework_prototype.md` §10](framework_prototype.md#10-results);
> - the chart's interactions, approved by the Owner — N104 and its demonstration,
>   [`evidence/20261124/`](../evidence/20261124/README.md#the-charts-interactions-approved-by-the-owner-n104);
> - the package, the envelope and the gate CI runs — [`package_gate.md`](package_gate.md),
>   [`encryption_envelope.md`](encryption_envelope.md);
> - the exporter that makes the real package — [`exporter.md`](exporter.md);
> - the login screen, the profiles and P13 — stage 2.6.

| Field | Information |
|---|---|
| Date | 2026-11-25 — revision 6: the summary as a crosstab, by the Owner's N120 (§6, §9). Revision 5: check 4 and the checks on the real package built (§9). Revision 4: step 3's page and checks 1 to 3 built (§5, §9). Revision 3: step 2 built (§5), and an assumption on media types (§8). Revision 2: approved by the Owner. Revision 1, the plan with N116 to N119 |
| Author | Claude Code |
| Status | **Plan, approved by the Owner on 2026-11-25 (N115)**, with its decisions N116 to N119 and the choices of §7. Work starts from the tag `checkpoint-2.4` (`e9f3007`); nothing built yet |

**[measured]** has output behind it; **[planned]** is intent; **[assumed]** is a premise the stage
proves or refutes (§8).

---

## 1. What exists

- **Candidate B's P01 page** (`prototypes/framework/own/`). It has a declaration
  (`p01.report.json`), a runner that knows no DOM, a page, the envelope's reader and the engine
  pinned on jsDelivr. It passed 2.3's criterion and its browser check on invented data.
- **N104's demonstration** over B's artifact: the legend that highlights and isolates, and the
  vertical with its popup. It is not built into the page.
- **What 2.3 left for this stage**, from the screenshots of 2026-11-24:
  - the line is drawn straight across a cell with no row (G);
  - a channel with no row in the last month loses that month from its axis;
  - the popup's values come from `DOUBLE`;
  - there is no touch or keyboard path, and no dark theme;
  - the browser oracle of N96 was a diagnostic, not a judgement.
- **From 2.4:** the 16 reports' contracts, the profiles, `site/package/` with invented envelopes of
  the 16 real shapes, and the real package once the live run is done (N109, N114).
- **Not yet:** no product page. `site/` holds the test page of 2.2.

## 2. The measure that shapes the stage: the gate meets the page's own code

`verify` searches every non-envelope file of `deploy/` for every report value, **by substring**
([`package_gate.md` §6](package_gate.md#6-the-inspection-for-clear-report-values-n81)). It looks
for texts of three or more characters, and for numbers with three or more significant digits or a
fraction. 2.3 never met this: its invented integers had five digits or more (N94).

`evidence/20261125/collision_surface.py` builds the gate's own needles, with its functions unchanged,
from M59's capture of the 16 views (outside Git). It searches them in B's artifact as built at 2.3,
in the site's public files and in N104's demonstration, and prints no value. This is M62
([`evidence/20261125/`](../evidence/20261125/README.md)) **[measured]**:

- the needles number 57,506; 186 of the 900 three-digit integers are a value in some view;
- **8 of the artifact's 9 code files hold at least one value**, 21 hits in all. The page as built
  would be refused;
- most of the hits sit inside something longer:
  - integrity hashes;
  - longer numbers;
  - words, such as a three-letter channel type inside an identifier.
- **6 stand alone as tokens:**
  - a three-digit constant of the envelope's reader;
  - a five-letter channel type that is also a word of the page's `cache: "no-store"`;
  - a CSS value;
  - a number in the declaration;
  - an amount in a code comment;
  - a second five-letter text.

  Outside the artifact, the year in `site/releases.md` is N108's first case.

Integrity hashes change with every pin and every edit, so the hits inside them move from release to
release. N116 settles this (§6).

## 3. What is built **[planned]**

### 3.1 Where the page lives

- The page goes under `site/`. The report is `site/relatorios/p01.html` with its declaration
  `site/relatorios/p01.report.json`. The shared code goes under `site/app/`: runner, page, chart,
  popup, tables, theme. The envelope's reader moves there from `web/envelope.mjs`, and `test-js`
  follows it.
- **No build step** (C1): the files are served as committed. Modules of the page's own origin need
  no integrity, since Hosting sends them `no-cache`. The pinned third-party bodies keep their
  integrity in an import map that a script writes from `cdn.json`, and `make check` fails when the
  committed page differs from what the script writes. 2.3's build hashed names for nothing this
  stage needs.
- `release/include.txt` and `release/media_types.txt` admit those paths, `.mjs` as
  `text/javascript` and `.css` as `text/css`. Both are protected files (§5).

### 3.2 The P01 declaration

2.3's declaration, with these changes:

- **Only additive columns are summed.** The metadata exported by 2.4 marks `order_count` as
  `non_additive`: an order with items in two categories counts in both
  ([`view_rules` at `b0ef66e`](https://github.com/alencardoug/mvp_eng_dados_2/blob/b0ef66e/docs/pacote_de_metadados.json)).
  A test reads the declaration and the metadata, and refuses a `sum` over a column that is not
  `additive`. No metric is redefined (CLAUDE.md §6, rule 3).
- **The chart reads the whole grid** of months by root categories, as the summary already does, with
  a null where there is no row:
  - the line breaks at G (Vega-Lite's `invalid` mode, measured in §8);
  - the x domain is every month, so the partial month stays on the axis under every filter;
  - the colour domain is the fixed list of categories, so a category keeps its colour under every
    filter.
- **The popup's values come from the exact decimal text**, formatted as the tables format them. The
  chart gets `DOUBLE` only to draw.
- **The partial month is the view's last month.** On M59's capture, its units are 7 % of the median
  of the twelve months before **[measured]**. The stage confirms this on the exported package. The
  notice changes from "os números ainda vão mudar", which frozen synthetic data does not do, to say
  that the month is incomplete in the data (C4).

### 3.3 The chart's interactions (N104), completed

- **Legend and lines**, as the demonstration does them:
  - hovering a label or a line highlights that series;
  - a click isolates it, shift-click adds another, and a double-click restores all.
- **The vertical and its popup:**
  - every series at the month, by value, in pt-BR;
  - a series with no row reads "Sem vendas neste recorte.";
  - the partial month carries its notice.
- **Keyboard** (C3): the plot is one focusable element.
  - ← and → move the vertical a month, Home and End go to the ends, and Esc closes it;
  - the popup's text is also given to a polite live region;
  - the legend's labels are buttons: Enter isolates, Shift+Enter adds.
- **Touch:** a tap puts the vertical on the nearest month, and a tap on a label isolates it. A
  "Mostrar todas" button appears while a selection is active, so nothing depends on a double tap.

### 3.4 Keyboard, focus, 360 px, light and dark

- Native controls, a visible focus ring everywhere, and a fixed tab order: filters, logout, legend,
  chart, tables — as built (§9).
- At 360 px, the page has no horizontal scroll. Each table scrolls inside its own region, and the
  axis thins its labels.
- Colour tokens on `:root`, the dark ones under `prefers-color-scheme` (N118). Vega's config follows
  the theme. Contrast is computed, not judged by eye: text at least 4.5:1, each series at least 3:1
  against its background, in both themes.

## 4. The checks **[planned]**

Every browser check drives headless Chrome through the DevTools protocol, as 2.3's did, with no npm
package. A check prints counts and file names, never a value. Its record in `evidence/` holds
counts and digests.

1. **Tables and chart against the package.** The expected values are computed in Python with DuckDB,
   from the Parquet the envelope opens with the public password (N22). They do not reuse the page's
   SQL. Per filter, `todos` and each channel:
   - the summary's cells, each a value, a G or a Z, and the detail of every month;
   - for the chart, each series read back from the SVG through the view's scales: its value per
     month to half a pixel, a gap at each G, every month on the x domain, and the same colour per
     category under every filter;
   - the popup's text at every month, exactly.
2. **Interactions.** Legend, hover, click, shift-click and double-click, the keyboard path and the
   touch path (emulated touch events). Each state is recorded as the series' opacities and the
   popup's text, against what is expected.
3. **Accessibility.**
   - The tab order equals the declared one;
   - every focusable element looks different when focused;
   - at 360 px the document is no wider than the viewport;
   - both colour schemes are emulated, and contrast is computed from the computed styles.
4. **The browser oracle of N96, now judged**, on the invented fixture. Its values are distinctive.
   On real data, short numbers sit in the browser's own binaries, as §2 found in code.
   - **Judged:**
     - no WebCrypto derivation, unwrap or decrypt outside a login attempt, and none that succeeds
       in a wrong attempt;
     - no write to any store (B writes none);
     - after logout, the engine worker that held the table has ended, and the worker the new login
       page starts holds no table;
     - nothing the browser can still read at the end holds a fixture value.
   - **Reported, not judged:** the bytes on disk after close that no decoder opens (V8's code
     cache, Chrome's own databases), as in 2.3, listed as unobserved.

Checks 1 to 3 run on the invented fixture and on the real package. Check 4 runs on the fixture
only. Where each one runs is N119's.

## 5. The order of the work

1. After 2.4's merge and the tag `checkpoint-2.4`: the branch for 2.5. **Done**: `report-2.5`.
2. **One protected PR** (no preview; the Owner reviews it):
   - `include.txt` and `media_types.txt`;
   - the change to the gate of N116, with the mutations of
     [`package_gate.md` §9](package_gate.md#9-the-mutations-and-their-tests-n76) proved again, plus new
     ones of its own;
   - the approvals of N108 the real package still needs, from `export collisions`, which uses the
     gate's matching and so follows N116.

   **Built on 2026-11-25**: N116 in `contract.found`, with MUT-07e and its counter-test; the page's
   paths and types. No approval is new: under N116 the two of 2.4's run, `2026` and `Logística`,
   still stand as tokens where the site shows them, so both stay needed.
3. **Ordinary PRs**, each with its preview (N117): the page, then the real package from 2.4's run in
   `site/package/` (N109). Checks 1 to 3 run locally before each PR and against each preview.
   **The page and checks 1 to 3 are built** (§9), on the branch `p01-page`, stacked on step 2's PR.
   Between the two, `export collisions` runs at the page's commit in a short read window: the
   page's own code may still hold a value as a token, as M62 found six in 2.3's page. Each one
   leaves the code or is approved under N108 in a protected PR, before the real package's PR.
4. Close: evidence, this document's status, PLAN's status of 2.5, and `make check` green.

## 6. The Owner's decisions

Asked on 2026-11-25, each answered with the recommended alternative. They live in
[PLAN §1.2](../PLAN.md#12-the-decisions), with the alternatives weighed:

- **N116** — `verify` matches a value only where it stands as a token, in every file. The page's code
  is still searched, and the few token hits left leave the code or are approved under N108.
- **N117** — the page first, on the invented fixture, then the real package, each in its own
  ordinary PR with its preview.
- **N118** — light and dark follow the system's scheme only. No toggle, no store.
- **N119** — checks 1 to 3 on the fixture in `make check`. Check 4 and the checks on the real package
  run in targets of their own.

Asked while building, after the first look at the real package:

- **N120** — the summary is a crosstab: a month per row, a root category per column, each cell the net
  revenue. Units stay in the detail.

## 7. Choices taken here, unless the Owner objects

- **C1** — no build step (§3.1).
- **C2** — accessibility checked by our own probes (§4, check 3), not `axe-core`, which would be an npm
  dependency of the tests.
- **C3** — the chart's keyboard path (§3.3).
- **C4** — the notice of the partial month (§3.2). Its Portuguese text is reviewed in the PR.
- **C5** — the envelope's reader moves to `site/app/` (§3.1).

## 8. Not verified, and assumptions

- **[measured]** The pinned Vega-Lite 6.5.0 breaks a line at a null and keeps a month whose
  values are all null on the x axis, in its default mode and in `break-paths-show-domains`. Under
  `filter` it draws straight across and drops that month, as 2.3's page did with no row at all
  (M63, [`evidence/20261125/`](../evidence/20261125/README.md)). So the grid's null rows fix both
  defects. The declaration names `break-paths-show-domains` rather than lean on the default, and
  check 1 of §4 holds it.
- **[measured, approximately]** §2 reads the capture's CSV text as each value's canonical form. The
  authoritative search is `verify`'s, on the exported package.
- **[assumed]** Hosting serves `.mjs` as `text/javascript`, which a module script needs, and `.css`
  as `text/css`, the types `release/media_types.txt` declares. The preview of the page's PR (N117)
  proves it.
- The real package on a preview is encrypted under public passwords (N22): whoever has the preview's
  URL can read it. That is the same as the publication at 2.10, by design.

## 9. The implementation

**What was built** for P01, as §3 planned it, with these choices made while building:

- `site/relatorios/p01.html` and `p01.report.json`; in `site/app/`, the page (`page.mjs`), the engine
  (`engine.mjs`), the package's source (`source.mjs`), the runner (`report.mjs`), the tables
  (`tables.mjs`), the chart (`chart.mjs`), the styles (`page.css`), Arrow's shim and the pins. The
  reader moved there from `web/` (C5, `92a66eb`), with the JavaScript suite and the prototype's harness.
- **The pins** (C1): `tests/report_pins.py` writes each page's import map and scripts and
  `site/app/pins.mjs` from `site/app/cdn.json`, the pins of 2.3 unchanged. `make check` refuses a page
  that differs. `cdn.json` is not deployed.
- **The legend is the page's own**, buttons above the plot, not Vega's. The vertical, the highlight and
  the isolation are Vega signals the page sets, so the pointer, the keyboard and touch take one path.
  A tap places the vertical only. Isolating is the legend's job on touch.
- **The partial month is drawn as such.** The first look at the real package showed every line falling
  in its last month. The line from the month before to it is dashed, and the month is marked "mês
  incompleto" on the chart.
- **Direct labels** at each line's end, spread apart with leader lines, from 40rem up. Below that, the
  legend and the popup carry identity, and the chart takes the whole width.
- **The palette** is the first four slots of the dataviz skill's validated categorical palette, checked
  with its validator: worst adjacent CVD ΔE 11.8 in light and 11.1 in dark, against `#1a1b1e`. Three
  light slots fall below 3:1 against white, and the summary table is their relief. **[measured]**
- **N116 shapes the code**: no colour token is a hex made only of digits, and the package is fetched
  with `cache: "no-cache"`. Ciphertext may sit in the HTTP cache, and 2.3's `no-store` would hold a
  channel type of the real data as a token.
- **The summary is a crosstab** (N120). On the real package, the long table had 132 rows, a month
  by a root category each. It now has 33 rows, a month each, and a column per root category. Its
  query still gives the grid as long rows; the runner (`report.pivot`) only lays them out and
  formats them, sums nothing and refuses a cell given twice. The month is a row header and stays
  in place as the table scrolls sideways; so do the caption and the notice of the partial month.
  A G shows `—`, keyed once under the table, and is read as "Sem vendas neste recorte.".
- **The invented P01** (`tests/site_fixture.py`, `p01_rows`) is a grid of fourteen months, three
  channels and four root categories. It holds a G under every filter, a G under one channel, a Z, a
  channel with no row in the last month, and the partial month. `site/package/` was sealed again from it.

**Checks 1 to 3** are `tests/test_report_page.py`, in `make check` (N119), with
`tests/browser/report_page.mjs` reading the page. They check:

- the pins, the additivity of every sum and the question, against the pinned metadata;
- the inputs;
- under each filter: the summary, its header, cells and key, and the detail, cell by cell; every month on the axis; each series
  read back from the SVG; the colours; the popup at every month, exactly;
- the mark of the partial month;
- the legend's isolation, Shift and double click, hover;
- a click on a line;
- the keyboard's vertical and its announcement;
- the tab order and every focus ring;
- 360 px with a tap;
- both schemes' contrast;
- logout.

The month's x is read where the vertical stands. The value's y is read from the axis labels less
their baseline offset, since Vega rounds its grid lines to whole pixels; a point must fall within
0.75 px. The pinned bodies are served from a cache by their sha256 (`BICE_CDN_CACHE`), seeded from
2.3's copies. DuckDB's extension host refuses Python's own HTTP client.

- **[measured]** 36 checks in about 17 s on this machine, stable over runs; 38 with the crosstab.
- **[measured]** Counter-proof of the crosstab: with its G cells as plain text and no row headers,
  the summary's check fails under every filter.
- **[measured]** Counter-proofs: with 2.3's chart query, which has no null rows, 7 checks fail — the
  axis, the lines through G, a popup's month, the mark. Summing `order_count` fails the additivity
  check.
- **[measured]** On the real package, served locally, no error reached the console and the page did
  not scroll sideways at 360 px. Its screenshots stay outside Git.

**On the real package** the same checks run with `BICE_REPORT_PACKAGE` naming a sealed package's
folder: the page is served with it, and the oracle opens P01 with the public password through the
Python reader, its Parquet read in a private temporary folder removed at once. The command prints
names and counts only (`tests/test_report_page.py`'s docstring). `Makefile` is protected, so there is
no target yet; a variable stands in for one.

- **[measured]** On 2.4's package: 37 passed, and the invented grid's own case was skipped.
- That run caught the tap check judging by the rotated labels' anchors, a constant distance off their
  months. With 33 months at 360 px, that is a neighbour. The check now reads the vertical itself.

**Check 4**, N96's oracle, is `tests/test_report_oracle.py`, run with `BICE_ORACLE=1`, before each PR and
against a preview's URL (`BICE_ORACLE_URL`). It drives 2.3's own diagnostic,
`prototypes/framework/browser/diagnostic.mjs`, unchanged: the same journey, and hooks in every realm,
workers included. It judges four things:

- WebCrypto only within a login attempt, and no successful unwrap or decrypt in the wrong one;
- no write to any store;
- every worker of the session ended at logout, with no report on the way back;
- no value of the package readable at the end.

It reports the closed profile's files that hold a text of the invented package.

- **[measured]** 6 passed in about 18 s; on disk, no file held one.
- **[measured]** Counter-proofs: a page that keeps a chart row in `sessionStorage` and derives a key on
  load fails three of the judged checks.

**Not done yet**: the page's PR and its preview (N117), after PR #33. Then `export collisions` at the
page's commit, check 4 against the preview, and the real package's PR.

