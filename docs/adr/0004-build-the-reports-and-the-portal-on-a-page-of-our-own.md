# ADR-0004 — Build the reports and the portal on a page of our own, with DuckDB-WASM and Vega-Lite

| Field | Information |
|---|---|
| Status | Accepted |
| Date | 2026-11-24 |
| Decider | The Owner |
| Resolves | The pending row "Framework of the reports and the portal" of the [record](README.md#3-pending), and the plan's N3 |
| Supersedes / superseded by | — |

## Context

N3 left the framework open: *a comparative prototype on P01 — Evidence against a build of our own
with DuckDB-WASM and a charting library —, and the choice after it*
([PLAN §1.2](../../PLAN.md#12-the-decisions)). The constraint that shaped the comparison is the
showcase's own: a report is published only as an encrypted package that the page opens in the
browser after login (ADR-0001), so a framework that runs report queries over clear data at build
time, or keeps their results in its finished output, fails ([PLAN §6.2](../../PLAN.md#62-the-stages),
stage 2.3).

Stage 2.3 built the same P01 page twice, on an invented fixture, and measured both
([`docs/framework_prototype.md`](../framework_prototype.md)). Its plan went through eight rounds of
Codex's review, its ground through five, and its comparison through four, which closed under N103.
In the last full run, at `a4f333f` on 2026-11-23 (§10):

- **Both pass the criterion.** Neither encrypted builder output nor artifact carries a fixture
  value: `verify` `PASS`, the inspection with no finding, and all 34 controls on the builder outputs
  as expected. Both pass the browser check with its four proofs.
- **B, the build of our own**, takes 529 lines (declaration, glue and configuration), no npm package,
  a 0.04 s build of 9 files and 36 KB, an 11-file artifact of 0.34 MB, and 3.6 s for one `verify`.
  From submit to summary it takes 0.71 s warm.
- **Evidence** takes 393 lines, 918 npm packages (616 MB in `node_modules`), a 48.5 s build of
  114 files and 10.0 MB, a 116-file artifact of 10.33 MB, and 704 s for one `verify`: the gate is
  about two hundred times slower than on B. From submit to summary it takes 1.38 s warm. It got
  there only through plugins of ours for the engine (A7) and the icon set (A8), a global its client
  sets (A2), inputs written by our own component (A4) and formatting in SQL (A5). Its service worker
  is registered on every page and no setting of ours removed it. Its queries fail at build time,
  logged, and its build output differs from one build to the next. Its last release was on
  2026-02-06 (M54).

The screenshots of 2026-11-24 ([`evidence/20261124/`](../../evidence/20261124/README.md)) added what
the comparison did not judge. The browser check compared the tables, not the charts, and each
candidate's chart has defects of its own. Evidence's default sort puts a text month axis in
descending order of value, not of time. Its labels shrink to "2", and the colour of each category
changes with the filter. B's line is drawn straight across a cell with no row (G), and a channel
with no row in the last month loses that month from its axis
([`framework_prototype.md` §10](../framework_prototype.md#10-results)).

## Alternatives considered

| Alternative | For | Against |
|---|---|---|
| **B — a page of our own: a declaration per report (`p01.report.json`), DuckDB-WASM, Vega-Lite and Arrow from jsDelivr pinned by digest (N94, N98), no build dependency** | No npm package and no dependency code at build time, so the isolation of §5 has nothing to contain; the build takes milliseconds and comes out the same each time; the artifact is small, so the gate runs in seconds; the fastest submit to summary; every carrier of the page is ours and listed; nothing to patch | More lines of our own, and each component the portal needs from 2.5 on — inputs, tables, accessibility, themes, narrow screens — written and kept by us; the chart's handling of G and of a missing last month to be declared; no community components or documentation to lean on |
| **A — Evidence 40.1.8** | Fewer lines for this page; Markdown and SQL pages; ready-made components and theming | 918 packages and a build that runs their code; plugins of ours for the engine and the icons, and four more workarounds, kept against every release; a service worker on every page that §2.3 item 8 does not allow; a build that differs from one build to the next; a gate of almost twelve minutes per `verify`; a chart whose default sort breaks the order of time; nine months without a release when it was measured |

## Decision

The reports and the portal are built as pages of our own, Candidate B of stage 2.3: each report is a
declaration — its queries, inputs, chart and tables — that our code renders in the browser over the
package it opens, with DuckDB-WASM, Vega-Lite and Arrow loaded from jsDelivr, pinned, and no build
dependency. The Owner decided this on 2026-11-24, for all the reasons the comparison gave.

## Consequences

- **Positive:**
  - The encrypted route stays as the prototype proved it. The build never receives data, has no
    dependency code to isolate, and outputs only files this repository writes.
  - The gate stays fast enough to run on every release and every control (3.6 s per `verify`).
  - The page loads 0.32 MB of its own on a cold start, beside the engine from jsDelivr. Its first
    load and its timings are those of §10.
  - A new report is a new declaration, reviewed in full (`CLAUDE.md` §5), and not a new framework
    page.
  - Stage 2.5 starts from a page that already passes the criterion and the browser check. It plans
    the browser oracle of N96 for this page alone.
- **Negative:**
  - Every component the portal needs is ours to write, test and keep: inputs, tables, the chart's
    handling of absent and partial data, keyboard and focus, 360 px, light and dark (stage 2.5).
    No community maintains any of it.
  - The chart's defects found on 2026-11-24 are ours to fix in the declaration, and stage 2.5's
    criterion — filter, chart and table agree with the package — now also needs an oracle for the
    chart, which the 2.3 check did not have.
  - The three libraries pinned on jsDelivr must be updated by hand. Each update is a new pin, with
    its digest checked.
  - The 136 lines more than Evidence for P01 grow with every report and with the portal.
- **Continued operation on Google Cloud:** the page is a static artifact, the same for every
  environment. Nothing in it names a path, a credential or an environment. The engine and the
  libraries come from public pinned URLs. Sandbox, qa and prod differ only in where the artifact is
  published, which is ADR-0002's and ADR-0003's.
- **Documents to update:** PLAN's N3 and §7, which point to this ADR, and its status of stage 2.3;
  [`docs/framework_prototype.md`](../framework_prototype.md), whose status records the choice and
  whose §10 owns the results and the charts' findings; the record's index and the README's count;
  [`evidence/20261124/`](../../evidence/20261124/README.md), the screenshots and the chart's oracle.
