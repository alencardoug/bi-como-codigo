# Plan — bi-como-codigo and the study content

> **What lives here:** the plan for the two new pieces of content — the `bi-como-codigo` showcase and
> the study content — and for the maintenance release of eng_dados they require: what gets built,
> the architecture, the impacts of the separation, the stages with the effort of each, the Owner's
> decisions, taken and pending, and what was measured to support all of it.
>
> **What does not:** the original proposal by Codex and the reviews of it and of this plan (see
> [`REVIEW.md`](REVIEW.md): §§1–11, findings RP-01 to RP-15, RV2-01 to RV2-14 in round 2, RV3-01 to RV3-04 in round 3, RV4-01 in round 4 and the closure in round 5); what
> eng_dados is and how it is operated (see its
> [README](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/README.md) and
> [Local Execution](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/execucao_local.md));
> how stage 1.6 regenerates eng_dados, line by line (see the
> [regeneration runbook](docs/regeneration_runbook.md), stage 1.4); the decisions, once recorded —
> they become ADRs in the repository that owns them.

| Field | Information |
|---|---|
| Date | 2026-11-25 — revision 77: stage 2.5's step 2 in PR #33 and its step 3 built — the P01 page and checks 1 to 3 ([`docs/report_page.md`](docs/report_page.md) §9). Revision 76: stage 2.4 done, merged by PR #32 at `e9f3007` with the tag `checkpoint-2.4`, and stage 2.5's short plan approved by the Owner. Revision 75: the short plan of stage 2.5, [`docs/report_page.md`](docs/report_page.md), with M62, M63 and the Owner's N116 to N119. Revision 74: stage 2.4's live run done, its two collisions approved under N108 ([`docs/exporter.md`](docs/exporter.md) §16). 2026-11-24 — revision 73: the Owner's N115, stages 2.5 to 2.10 without Codex's rounds, from a return point at 2.4's merge. Revision 72: the Owner's N114, the live run before the one protected PR. Revision 71: the review of the exporter's code closed after round 3 under N113 ([`docs/exporter.md`](docs/exporter.md) §14, §16). Revision 70: the Owner's N113, and round 2 of the review of the exporter's code answered ([`docs/exporter.md`](docs/exporter.md) §16). Revision 69: round 1 of Codex's review of the exporter's code answered ([`docs/exporter.md`](docs/exporter.md) §16). Revision 68: the Owner's N111 and N112, from round 1 of Codex's review of the exporter's code. Revision 67: step 2 of stage 2.4 done — the catalogue read, `release/views.json` approved by the Owner, the declarations migrated to the 16 reports ([`docs/exporter.md`](docs/exporter.md) §16). Revision 66: step 3 of stage 2.4 built — the exporter, its fake warehouse and its mutations, and a probe against an isolated PostgreSQL ([`docs/exporter.md`](docs/exporter.md) §16). Revision 65: round 3 of the review of the exporter's plan answered in its revision 4, which closes the review under N110 with declared limits. Revision 64: the review of the exporter's plan closes after round 3, of regressions only (N110). Revision 63: round 2 of Codex's review of the exporter's plan answered in its revision 3. Revision 62: round 1 of Codex's review of the exporter's plan answered in its revision 2, with the Owner's N105 to N109. Revision 61: the plan of stage 2.4, [`docs/exporter.md`](docs/exporter.md), written for Codex's review, with three questions for the Owner. Revision 60: N86 is in `main`, merged from PR #31 with the Owner's authorisation; `make check` needs both checkouts, and 2.4 waits only for its plan and a read window. Revision 59: the chart's interactions approved by the Owner, a legend that highlights and isolates a series and a vertical with every series at the month (N104), for stage 2.5. Revision 58: the Owner chose the framework, Candidate B, a page of our own with DuckDB-WASM and Vega-Lite, recorded in [ADR-0004](docs/adr/0004-build-the-reports-and-the-portal-on-a-page-of-our-own.md) (N3); stage 2.3 is done, and the screenshots of both pages found defects in each chart that its check did not judge ([`evidence/20261124/`](evidence/20261124/README.md)), carried to 2.5. Revision 57, 2026-11-23: the review of stage 2.3's comparison closed under N103, after round 4's corrections, with its declared limits ([`docs/framework_prototype.md`](docs/framework_prototype.md) §9); the framework's choice is the Owner's. Revision 56: stage 2.3's comparison run in full for the last time at `a4f333f`, from a snapshot of its commit: both candidates pass, the 34 controls are as expected ([`docs/framework_prototype.md`](docs/framework_prototype.md) §10). Revision 55: how the review of stage 2.3's comparison closes — after a last round of regressions only, the run at `a4f333f` the last (N103). Revision 54: stage 2.3's comparison run in full again at `5fdaa02`, after round 2 of its review answered CMP-2-01 to -10: both candidates pass the criterion and the browser check with its four proofs, the 34 controls are as expected, and §10 says only what the run's results hold ([`docs/framework_prototype.md`](docs/framework_prototype.md) §7, §10). Revision 53, 2026-11-22: stage 2.3's comparison run in full at `356bec1`, after round 1 of its review: both candidates pass the criterion and the browser check, the 34 controls on their builder outputs are as expected, and the gate's time is measured ([`docs/framework_prototype.md`](docs/framework_prototype.md) §10). Revision 52: round 1 of Codex's review of stage 2.3's comparison, twelve findings, eight blocking, all answered; its results stand for the harness reviewed and are replaced by the next full run ([`docs/framework_prototype.md`](docs/framework_prototype.md) §5, §10). Revision 51: the controls of stage 2.3 run on each candidate's own builder output, all as expected ([`docs/framework_prototype.md`](docs/framework_prototype.md) §10). Revision 50: stage 2.3's steps 4 to 6 run once before the review, both candidates passing the criterion ([`docs/framework_prototype.md`](docs/framework_prototype.md) §10). Revision 49: the Owner's mandate of 2026-11-22 (N101), and the verdict of stage 2.3 judging the runs of one harness, Claude Code's choice under it (N102). Revision 48: Evidence's build of stage 2.3 is probed once more, with its brand icons cut to the four it uses (probe A8), by the Owner's N100, after the draw against its builder output was measured impossible. Revision 47: the carrier inspection of stage 2.3 no longer counts a decoding that changes nothing as a layer, and searches as data a JSON script that an unescaping layer broke, by the Owner's N99. Revision 46: a page may load DuckDB's `parquet` extension from `extensions.duckdb.org`, pinned, beside jsDelivr, by the Owner's N98. Revision 45, 2026-11-21: the review of stage 2.3's step 1 closes after round 5's corrections, by the Owner's N97, with the isolation wrapper and the browser diagnostic out of it. Revision 44, 2026-11-20: the verdict of stage 2.3 judges the finished build output, as its criterion says; the browser is measured as a diagnostic, and its complete oracle is built at 2.5 for the chosen framework (N96), from round 7 of the review of 2.3's plan. Revision 43, 2026-11-20: what the oracle of stage 2.3 guards against — the ordinary behaviour of the frameworks, their libraries and the browser, not code turned against it (N95), from round 4 of the review of 2.3's plan; its review goes on until no blocking finding is left. Revision 42, 2026-11-20: both framework candidates of stage 2.3 load DuckDB-WASM from jsDelivr, Evidence through a probe of its own (N94), from round 3 of the review of 2.3's plan. Revision 41, 2026-11-20: the Owner creates the cross-project mailbox `mvp_eng_dados_2` asked for (N92), closing its question of §7, and keeps the pin at `b0ef66e` although the source moved on to `2ea212b`, whose two commits only add its V8 to the package's `open_items` (N93). Revision 40, 2026-11-20: `mvp_eng_dados_2` answered UQ-21 to UQ-23 in three commits on top of `v2.3.0`, the last `b0ef66e`, with no new tag and no warehouse build: each view audit now names the commit of the definition it checked, and V5 to V7 are closed; the pin of 2.4–2.10 and of the package moves to `b0ef66e` (N91), checked by M61; the views stay those of M59. Revision 39, 2026-11-19: `mvp_eng_dados_2` closed two more phases, the base reopening (`v2.2.0`, `f5a5173`) and the reorder point per pair (`v2.3.0`, `2bceb47`); the Owner moves the pin of 2.4–2.10 and of the metadata package to `v2.3.0` (N90); the 16 views captured at it and compared with M55 by fingerprint — only P08, P11 and P12 changed, as announced (M59) —, the package checked (M60), UQ-16 to UQ-20 answered and UQ-21 to UQ-23 asked (§3.5.1); the next steps replanned (§6.3) and §7 revised. Revision 38, 2026-11-17: `mvp_eng_dados_2` closed its consumer-base phase with the tag `v2.1.0` (`eb11709`) on regenerated data; the Owner moves the pin of 2.4–2.10 and of the metadata package to it (N89); the 16 views captured at it (M55), set against what survives of the old pin `4da9e60`, which this repository never captured (M56), the package checked (M57), and what only `mvp_eng_dados_2` can correct asked as UQ-16 to UQ-20 — first, its streaming exercise in P08 and P11 (M58) (§3.5.1); the next steps replanned (§6.3) and two questions left to the Owner (§7). Revision 37, 2026-11-14: `mvp_eng_dados_2` answered this repository's questions at `32397cc` ([`docs/upstream_questions.md`](docs/upstream_questions.md)); the Owner's Q12 and Q14 there, recorded as N87 (2.7 and `gdados` are two portals reading the one metadata package, closing the question of §7) and N88 (no new Google Cloud resource); stage 2.7 reads the package (§3.5); N88's reach on N18's fallback left to the Owner (§7). Revision 36, 2026-11-13: eng_dados continues in mvp_eng_dados_2 (its D92), on the same warehouse; the Owner's N85 (2.4–2.10 pin a commit of mvp_eng_dados_2 after its audit of the views) and N86 (two checkouts in the gate); the two portals left to the Owner (§7); what mvp_eng_dados_2 announces for the showcase (§3.5.1). Revision 35: eng_dados' stage 13 accepted, the pin of 2.3–2.10 set to its tag `v2.0.0`, M53, and stage 2.3's plan with M54. Revision 34: stage 2.2's implementation reviewed and the Owner's delegation of the test approvals (N75). Revision 33: the Owner's decision on what the candidate workflow guarantees about tokens (N74), from round 1 of the review of 2.2's plan. Revision 32: stage 2.2a done, its review closed in round 5; the Owner's decision on when eng_dados' stage 13 runs (N73). Revision 31: stage 2.2a implemented — the Owner's mandate for the night and the decisions anticipated for it (N68–N72), M48 and M49; the envelope's design review went through three rounds, and its revision 4 goes to round 4 with the code. Revision 30: Part II opened with stage 2.2a — the Owner's decisions N64–N67, the envelope's byte format written for review in [`docs/encryption_envelope.md`](docs/encryption_envelope.md), and M47. Revision 29: stage 1.9 done — the whole v1.1.0 reviewed by Codex in three batches, with the Owner's decisions taken during the review (N57–N63) and M46, the consumer's duty on `generated` lineage in §3.5, and the Owner's acceptance; the tag `v1.1.0` marks the acceptance commit in eng_dados. Revision 28: stage 1.6 done, with the Owner's decision on the legacy keys the regeneration gives back (N56) and M45; the Owner accepted N55's GCP counterpart as written. Revision 27 recorded stage 1.5 as done, with the Owner's decisions on the legacy keys the regeneration removes (N54) and on recording the retained ledger as a decision record of its own in eng_dados (N55), and M42–M44. Revision 26 recorded stage 1.8 as done, with the Owner's decision on reviewing its text (N53) and M41, revision 25 recorded the Owner's decisions for stage 1.8, in two rounds (N46–N52), and its first part, revision 24 recorded stage 1.7 as done, with the Owner's decisions from its prototype (N44, N45) and the measurements M39–M40, revision 23 recorded the Owner's decisions on stage 1.7 — where an inherited description lives, how inheritance crosses the retail–legacy union and what the ratchet counts — and on the runbook's O6 (N40–N43), with M38, revision 22 recorded the Owner's decisions of 2026-10-28 on the order of the remaining Part I stages and on the three generator fixes (N36–N39), revision 21 recorded stage 1.4 as done, its runbook's review closed in round 9, revision 20 recorded M37, P8's host-process check, revision 19 recorded the Owner's decision on concurrent capture callers (N35), revision 18 recorded the runbook's state after round 7, revision 17 recorded it after round 6, revision 16 recorded the Owner's decisions for round 5 — the recovery phase's barrier (N32), the ledger's epochs (N33) and a transition whose record failed (N34) —, revision 15 recorded round 4's (N30, N31, M36), revision 14 added round 3's (N29, M34–M35), revision 13 added round 2's (M31–M33), revision 12 round 1's (M27–M30); revision 11 recorded the Owner's decisions and the measurements for the runbook of stage 1.4 (N26–N28, M24–M26) |
| Author | Claude Code, at the Owner's request |
| Base | eng_dados at `26b58b3` |
| Status | **Complete proposal, in execution.** Part I is done: v1.1.0 accepted and tagged in eng_dados (stage 1.9). **Stage 2.2a is done on 2026-11-06, its criterion met**: the envelope's format version 1, specified in [`docs/encryption_envelope.md`](docs/encryption_envelope.md), is implemented — the Python producer and reader and a JavaScript reader written apart from it, on WebCrypto —; both readers consume the fixed, complete vectors; the known-answer vectors of the primitives pass in both; 151 shared cases, every negative case of §3.6 among them, end in their exact refusal in both, and every predicate is proved by its counter-proof (M48); the derivation costs 378 ms in Chrome (M49). Codex reviewed it in five rounds — the design in rounds 1–3, seven findings, two blocking; the implementation in rounds 4–5, six findings, none blocking —, all applied, and round 5 found no blocking finding and closed the review (N72). The Owner accepted the per-profile encryption decision as written, in ADR-0001. **Stage 2.2 is done on 2026-11-06, its criterion met**: its plan, [`docs/publishing_pipeline.md`](docs/publishing_pipeline.md), closed in round 4 of Codex's review; its resources exist (N70); its implementation closed in round 3 of a review of its own — 14 findings, three blocking, among them a path traversal in the pinned artifact downloader, all applied —; of the tests of its §7, all of them, T1 to T11 — T2 through a fork in the Owner's organisation `alencardoug-lab`, T5 in both schedules, T10 in both parts — passed on 2026-11-06 on GitHub and Firebase, with the approvals delegated (N75, renewed by the Owner for the afternoon) — live serves the fixture site at https://bi-como-codigo.web.app —; the ruleset on `main` exists since 13:44Z; the Owner accepted its two decisions as written, hosting in ADR-0002 and the trusted workflow in ADR-0003. **Stage 2.2b is done on 2026-11-07, its criterion met**: every mutation the package-to-artifact gate can see is refused by the publishing workflow before any upload — all of them by `verify` in `make check`, three on GitHub through the workflow —, and an honest package was previewed against live, bound to its version and promoted; its plan, [`docs/package_gate.md`](docs/package_gate.md), and its code each closed in round 5 of Codex's review; 35 mutants killed (M52); shaped by the Owner's N76–N83. **eng_dados' stage 13 is done**: the Owner accepted it on 2026-11-13, with reservations, in a session there ([its stage 13](https://github.com/alencardoug/mvp_eng_dados_1/blob/f86b9fb/docs/plano_de_desenvolvimento.md#etapa-13--replicação-no-gcp-com-terraform--m6)), its Google Cloud resources destroyed; the tag `v2.0.0` marks the acceptance commit, `f86b9fb`. The same day eng_dados was archived at that point and continues in `mvp_eng_dados_2`, which shares the warehouse and will correct values of views this showcase publishes (§3.5.1): 2.4 to 2.10 pin a commit of `mvp_eng_dados_2` after its audit of the views, not `f86b9fb` (N85), and the gate will read both repositories (N86). On 2026-11-14 it answered this repository's questions at `32397cc` ([`docs/upstream_questions.md`](docs/upstream_questions.md)), and the Owner decided there that stage 2.7 and `gdados` are two portals reading its one metadata package (N87) and that nothing new is created on Google Cloud (N88). The end of the account's free trial does not reach this project, whose billing is off (M53). Next: stage 2.3, whose plan, [`docs/framework_prototype.md`](docs/framework_prototype.md), closed in round 8 of Codex's review on 2026-11-20 (N94–N96), being implemented: its step 1, the ground, is built and its review closed after round 5's corrections (N97), with the isolation wrapper and the browser diagnostic outside it; its step 2, the clear mode, is done: Evidence installs and builds offline with no script of a dependency (A6), and its carriers are listed (A1), each caught by `verify` and by the inspection in its control; Candidate B's page is built, and its clear build's one carrier, the clear Parquet its page fetches, is caught likewise. Its step 3, the encrypted route, is done: B's builder output is archived, and Evidence loads its engine from jsDelivr (A7), builds with no source (A3) and opens the package into its own engine (A2), each with no patch, its builder output archived. Its steps 4 to 6 — the draw, the checks on both artifacts and the measures — ran in full for the last time at `a4f333f`: both candidates pass the criterion and the browser check, and are measured ([`docs/framework_prototype.md`](docs/framework_prototype.md) §10); the review of steps 2 to 6 is closed after round 4, of regressions only (N103), with its declared limits (§9). **Stage 2.3 is done on 2026-11-24, its criterion met: the Owner chose Candidate B, the build of our own, in [ADR-0004](docs/adr/0004-build-the-reports-and-the-portal-on-a-page-of-our-own.md) (N3)**; the screenshots of that day found defects in both charts that the check, which compares the tables, did not judge — Evidence's months ordered by value, B's line across a cell with no row —, for stage 2.5 ([`docs/framework_prototype.md`](docs/framework_prototype.md) §10). Stage 2.4's plan, [`docs/exporter.md`](docs/exporter.md), closed after round 3 of Codex's review (N110); **its step 3 is built**: the exporter over the fake warehouse of its §12, every mutation of that table caught by its code with its positive control, and a probe of the SQL and of the pinned psycopg against an isolated PostgreSQL 16.15 holding invented rows (its §16). **Its step 2 is done**: `export catalogue` read the warehouse's catalogue in a short window the Owner opened, `release/views.json` was drafted from it and approved by the Owner, and the trusted declarations migrated to the 16 reports with an invented package (its §11, N109). **Codex's review of its code closed after round 3 under N113** — 25 findings, 11 blocking, all answered, the rest declared limits (its §14). **Its live run is done** on 2026-11-25 (its §16): the 16 views exported, their counts and fingerprints equal to M59's, `verify` passed on the private candidate, and the two collisions — `2026` and `Logística` — approved under N108. **Stage 2.4 is done** on 2026-11-25: the Owner reviewed its one protected PR (N114), merged as PR #32 at `e9f3007`, the tag `checkpoint-2.4` on that commit (N115). Stage 2.5's short plan, [`docs/report_page.md`](docs/report_page.md), was approved by the Owner the same day: its step 2, N116 and the page's paths, is the protected PR #33, and its step 3, the P01 page with checks 1 to 3 in `make check` (N119), is built on its branch ([`docs/report_page.md`](docs/report_page.md) §9). From the tag, by N115, stages 2.5 to 2.10 go without Codex's rounds but at 2.6 and 2.10. Stage 2.1, the foundation, is done — its criterion met: the secret guard is green with the two demo passwords registered as public by design. In eng_dados, on 2026-10-23, stages 1.1, 1.2 and 1.3 are done — 1.1 and 1.2 pushed, 1.3 committed locally: 1.1 in `9c9ff9c` — the guard failed on eight views before the fix (P01, P02, P03, P05, P06, P13, P14 and the P15 denominator) and passes after; M3 redone on the views gives zero; only the two M3 groups changed; `make check` green, PASS=905 and 667 Python tests —, 1.2 in `7f97d62` — the ADR for O2, number 0049 there, `verificar.py` clean, `make check-offline` green —, 1.3 in `38c1bea` and `1e197ac` — `--json` walked hop by hop gives the 14 edges of M12; the `consumption_reader` login, through an actual connection, reads `consumption`, is refused on the other layers, cannot write and cannot escalate, with a counter-proof; `make check` green, PASS=905 and 683 Python tests. Stage 1.6 is done on 2026-11-04, its criterion met: both sources regenerated and checked by content, the legacy capture certified and the retained memory contained against the retained ledger — with the keys N54 accepted and the reappearances N56 accepted —, the four zeros on both paths, M3 and M7–M9 met in the warehouse, `make check` green (PASS=907, 885 passed), the triggered DAG run finished on its second run, the new recovery package restored through the nine steps and promoted, and the operating state given back (M45) — in eng_dados `592e2cc` to `6d93d72`, pushed. Stage 1.5 is done on 2026-11-04, its criterion met: the in-memory generation deterministic, T1's calibration on today's source equal on every table but the producer's; M7 to M9 redone on it, all at zero (M42); `make check-offline` green, 695 passed — and every hand-over of the [runbook's §3.2](docs/regeneration_runbook.md#32-what-stage-15-hands-over) delivered: H1 and H2 measured (M43, with N54), H3 to H5 (M42, M44), and the tools T1 to T4 with the gates, the recovery phase and the epochs, H6 to H8 (N55) — in eng_dados `9705aaf` to `61b9f4a`, pushed up to `c272104`. `make check` there stayed red by design on invariant 14 until stage 1.6 turned it green (`0b8a33c`). Stage 1.8 is done on 2026-11-03, its criterion met: the ceilings of `analytics` and `consumption` at zero, the text approved by the Owner as written (N53) — in eng_dados `d4c2885` to `33d6451`, `make check` green (PASS=905, 703 passed), not pushed (M41). Stage 1.7 is done on 2026-11-03, its criterion met: a carried column inherits, P01's same-name sum and an undeclared legacy bridge do not; the ceilings at what 1.7 delivers; the added `make check` cost measured, +2.1 s end to end; `make check` green (M40) — in eng_dados `ff868a9`, `1e7de44` and `eeae9d1`, not pushed. Stage 1.4 is done on 2026-10-28, its criterion met — Codex with no blocking finding: its [runbook](docs/regeneration_runbook.md) closed in round 9 of the review. Round 1 of Codex found fourteen findings, six blocking, answered in its revision 2; round 2 closed nine and found six more, four blocking, answered in revision 3; round 3 closed six and found five more, three blocking, answered in revision 4; round 4 closed six, left four partly closed and found four more, one blocking, answered in revision 5; round 5 closed three, left five partly closed and found four more, two blocking, answered in revision 6; round 6 closed four and found one more, blocking, answered in revision 7; round 7 closed two and found three more, one blocking, answered in revision 8; round 8 closed four and found two more, one blocking, bounded by the Owner's decision N35 in revision 9; round 9 was interrupted by Codex's usage limit, revision 10 applied what it had found, and round 9, rerun, closed every finding in scope — RR-43 and those that depended on it within N35 — with two observations and no blocking finding. The runbook is a specification: what it hands over to stages 1.5 and 1.6 is unimplemented and unmeasured (its §7). Nothing else is implemented. Every decision of the Owner taken (§1.2). Round 3 closed eleven round-2 findings and partly closed three. Round 4 closed five of the seven left in its scope and left RV3-02 and RV2-05 open only on RV4-01, applied in revision 9. Round 5 closed RV4-01, RV3-02 and RV2-05 with no new finding: the plan review is closed, and execution follows §6.3 (§10) |
| Nature | Lives in this repository. At stage 3.2, Part III moves to `caderno-de-dados`; Part I becomes ADRs and pending items in eng_dados |
| Evidence | [`evidence/20261022/`](evidence/20261022/) for M1–M18 and [`evidence/20261023/`](evidence/20261023/) for M19–M35 and [`evidence/20261028/`](evidence/20261028/) for M36–M37 and [`evidence/20261103/`](evidence/20261103/) for M38–M40 and [`evidence/20261105/`](evidence/20261105/README.md) for M47 and [`evidence/20261106/`](evidence/20261106/README.md) for M48–M52 and [`evidence/20261113/`](evidence/20261113/README.md) for M53–M54 and [`evidence/20261117/`](evidence/20261117/README.md) for M55–M58 and [`evidence/20261119/`](evidence/20261119/README.md) for M59–M60 and [`evidence/20261120/`](evidence/20261120/README.md) for M61 and [`evidence/20261125/`](evidence/20261125/README.md) for M62–M63: read-only probes, prototypes and counterexamples, with their literal outputs and the `ro.sh` that re-runs the SQL probes |
| Translation | Translated from Portuguese on 2026-10-22, at the Owner's request. The original is in commit `e046937` of this repository |

---

## 1. What is already decided

### 1.1 By the Owner, in the conversation of 2026-10-22

The choices from the conversation with Codex still hold
([`REVIEW.md` §1](REVIEW.md#1-the-request-and-the-choices-already-made)), redistributed by O6: P01 is
the first report of the showcase and the first lesson of the study content.

| # | Decision |
|---|---|
| **O1** | A **separate project, in a new repository**. eng_dados is complete, and the exclusion of BI and dashboards in its Charter §4 applies to it and still does |
| **O2** | **No synthetic field is restricted in the analyses**: all of them may — and should — appear |
| **O3** | Where it adds value, **fix the synthetic data** that is incoherent today |
| **O4** | **An in-depth study of the governance**: how it is built, what value it has and how to use it in the project |
| **O5** | The project **grows to every view and analysis** of eng_dados. The thesis: reports as rich as Power BI's, or richer, **with no licence**, and without bringing the whole database |
| **O6** | **Two pieces of content.** The **showcase** (`bi-como-codigo`) shows technical capability: a robust, summarised product, an executive presentation that needs no presenter; the governance of the project; and, above all, the data governance, told as a **reading portal** — "I have just arrived at this database and want to understand everything in it" —, organised and engaging, so that whoever consults it learns fast and recognises a well-governed project. The governance may be reassessed and refined. The **study** content is the learning: explorations, the path from the views to the source, understanding the governance and the project |
| **O7** | **Login, and content segregated by login,** in the showcase: two logins, one of them with access to a single report that makes sense in the story, to show **least privilege**. A simple implementation, straight in the code; no more logins and no management screen |
| **O8** | **A complete separation from eng_dados**: the new notes live in the new repositories, and eng_dados keeps only the references it needs — such as the justification for changing its database |

### 1.2 The decisions

| # | Question | Choice |
|---|---|---|
| **N1** | Name of the showcase | **`bi-como-codigo`** |
| **N2** | Data, querying and publishing | **Parquet queried by DuckDB in the browser; Firebase Hosting in a project of its own; GitHub Actions publishes on merge and builds a preview per PR; the DuckDB engine comes from jsDelivr** — the hosting recorded in [ADR-0002](docs/adr/0002-host-on-firebase-hosting-through-identity-federation.md), the publishing in [ADR-0003](docs/adr/0003-publish-through-a-trusted-workflow-on-main.md) |
| **N6** | When to fix the synthetic data | **Now, before anything else** |
| **N8** | Scope of the ADR for O2 | **Classifying is not exposing**: the classification stays — metadata, and the basis of the policy tags of Stage 13 —, and exposing synthetic data becomes free. It rewrites the rule of [Governance §4](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#4-classificação-de-sensibilidade) and settles today's divergence (RP-02) |
| **N17** | How to organise the two pieces of content | **Two repositories, two sites**; the study content reads the data the showcase publishes and has its own capture for the lessons |
| **N18** | Where the study content lives | **Private on claude.ai, as long as nothing is limited by it; if any capability is limited, a `*.web.app`.** The probe of stage 3.1 decides |
| **N20** | When to refine the governance | **In v1.1.0**, as a stage of its own, separate from the regeneration |
| **N14** | D62, D63 and D64 in v1.1.0 | **No** — they remain pending items of their own |
| **N23** | How to implement the per-profile access (O7) | **The password becomes the key**: each report is encrypted at publication, and the fixed password of each profile opens only the keys of its reports — no account, no Firebase Authentication, no Firestore |
| **N22** | Do visitors see the passwords? | **Both, below the login box**, with the text in §3.2; above the box, an explanation of what the page and the product are |
| **N4** | Which login the exporter reads the views with | **A read-only login**, member of `analyst`, created by eng_dados in v1.1.0 |
| **N16** | The dimensional model in the showcase | **Only the 16 views, for now**: the consumption contract stays intact, and detail, when a report needs it, comes with an ADR in eng_dados |
| **N7** | The study trail after the regeneration | **A notice at the top**: the real outputs were measured on the v1.0.0 data. It goes in only with the next update of the trail, never on its own |
| **N21** | Name of the study repository | **`caderno-de-dados`** |
| **N3** | Framework for the reports and the portal | **A comparative prototype on P01** — Evidence against a build of our own with DuckDB-WASM and a charting library —, and the choice after it (stage 2.3): **the build of our own**, chosen by the Owner on 2026-11-24 ([ADR-0004](docs/adr/0004-build-the-reports-and-the-portal-on-a-page-of-our-own.md)) |
| **N15** | Authentication of the CI pipeline to Firebase | **Identity federation** from GitHub to Google Cloud, with no stored key — recorded in [ADR-0002](docs/adr/0002-host-on-firebase-hosting-through-identity-federation.md) |
| **N10** | Does the study clock count `caderno-de-dados`? | **Yes** |
| **N12** | The showcase in the portfolio | **A link on the page of project A** |
| **N24** | Language of the new repositories and of the communication between agents | **Construction in English** — code, commits, technical documents, plans, reviews and the communication between Claude Code and Codex; Portuguese for what visitors read, for the study content and for the conversation with the Owner ([`CLAUDE.md`](CLAUDE.md) §2) |
| **N25** | When to create `bi-como-codigo`, and with what visibility | **Now, public** — created on 2026-10-22 to keep this version and separate it from eng_dados |
| **N26** | The rollback cut of the regeneration (2026-10-23) | **A pre-maintenance cut**: at the start of stage 1.6, a recovery package of the current state — both sources and the memory — packed from the last commit before stage 1.5, in a directory of its own outside the checkout, and verified against the databases; the approved package of 2026-09-25 stays as the fallback. Restoring the approved alone would lose what the warehouse gained after its cut (M24) |
| **N27** | Where eng_dados records v1.1.0 (2026-10-23) | **In its Development Plan**: a subsection after Stage 12, with no stage number — objective, the justification, the stages by a pinned link to this plan, criteria, acceptance and tag —, as Stage 12 did for v1.0.0 |
| **N28** | The v1.0.0 packages once the v1.1.0 package is promoted (2026-10-23) | **Both kept**, outside the checkout: the approved of 2026-09-25, validated by B5's restore, and the pre-maintenance cut, never restored but holding the state the study trail measured |
| **N29** | How the DAG's own legacy capture is recorded before its first build (2026-10-23, RR-22) | **A gate task in `fluxo_batch`**, delivered by stage 1.5: after the capture is concluded and before `dbt_seed`, it writes the memory record of the run's attempt into a directory named by the environment and fails the run when it cannot, in every run. Chosen over a gate only on request, a closed Airflow pool and the gap declared — the record precedes every build by construction ([runbook H6](docs/regeneration_runbook.md#32-what-stage-15-hands-over)) |
| **N30** | Where an earlier capture attempt's transition is recorded (2026-10-28, RR-28) | **A recovery phase of its own**, delivered by stage 1.5: `iniciar` no longer finalises earlier attempts; before opening one, `make sync-legacy` and a new DAG task record every due attempt, run `retomar` on those, record each transition as it happens and stop on any other change, so that a failure to record stops before any job is dispatched. Chosen over a hook inside `iniciar`, which would hide the checkpoint inside the function and be harder to prove on every path ([runbook H7](docs/regeneration_runbook.md#32-what-stage-15-hands-over)) |
| **N31** | How the DAG's gate is configured and retried (2026-10-25, RR-29) | **Never retried alone, never disabled**: retrying or clearing `registrar_captura_do_legado` by itself is forbidden — a failed run goes through the runbook's §5, and the whole DAG runs again, a new capture —, and an unset directory variable fails the task. The Owner asked for the best option without much code for little gain: a supported gate-only retry would need the record bound to its original attempt and a refusal of conflicting content ([runbook H6](docs/regeneration_runbook.md#32-what-stage-15-hands-over)) |
| **N32** | How complete the recovery phase's barrier is (2026-10-28, RR-32) | **The whole inventory, and a stop on an active predecessor**: before an attempt opens, every attempt of the certificate table recorded in the ledger's epoch and equal to its latest record, none `pending`, and every raw `sync_id` and Airbyte job since the baseline claimed; a predecessor still running stops with its reason, and the caller is run again. Both callers record their own attempt at its end — the CLI gains the DAG's gate. Chosen over the certificate alone, which would leave a job started outside both callers to T3 ([runbook H7](docs/regeneration_runbook.md#32-what-stage-15-hands-over)) |
| **N33** | How the ledger crosses a restore (2026-10-28, RR-34) | **Epochs**: the directory `.env` names is the ledger's root, each epoch a subdirectory opened by a baseline; A8 opens the first, the maintenance code's restore opens one by itself before its capture, and the return from `PRE` one by hand. Under `PRE` the claim is declared not to hold. Chosen over moving the directory by hand, which would split the restore target and reconfigure Airflow each time ([runbook H8](docs/regeneration_runbook.md#32-what-stage-15-hands-over)) |
| **N34** | A transition whose record failed (2026-10-28, RR-33) | **Stop for the Owner**: the recovery phase tests its directory before finalising, and a final certificate with no transition record is never recorded as one — the Owner decides whether its reading is recorded, marked as late, or the cycle goes back. Chosen over recording the expected result before publishing it, which would split the certificate's publication in eng_dados ([runbook H7](docs/regeneration_runbook.md#32-what-stage-15-hands-over)) |
| **N35** | Whether the ledger's guarantee covers capture callers alive at the same time (2026-10-28, RR-37 to RR-43) | **No — one caller alive at a time**: the claims of the runbook's H6 to H8 hold while a single capture caller is alive; two together — the CLI during a DAG run, or two of either — are a declared limitation, kept out by the operator and checked before each line of the cycle that captures: the preflight with no DAG run or sync under way, and no `mvp_ed1.airbyte` process on the host. The opening lock and the attempt lock stay as defence, with no claim against concurrency, and T3 remains the independent check of the memory. Chosen over going on hardening the protocol: three rounds found only concurrent schedules, each fix opening the next, at a cost in stage 1.5's code the Owner had asked to avoid ([runbook §4](docs/regeneration_runbook.md#4-the-cycle)) |
| **N36** | The order of the remaining Part I stages (2026-10-28) | **1.7, then 1.8, then 1.5, then 1.6**: the Owner's full review of 1.8's text runs in parallel with 1.5's code; then 1.6 (§6.3) |
| **N37** | The category tree of the generator (2026-10-28, M7) | **A declared tree in `geracao.yml`**: 4 roots × 2 middles × 2 leaves, 28 nodes, Esporte gaining its 4 leaves; the categories' `min_rows` goes from 24 to 28 and its count is the size of the tree (§5.3) |
| **N38** | The price of a product (2026-10-28, M8) | **A price range per leaf in `geracao.yml`, drawn log-uniform**, a new parameter of the engine (§5.3) |
| **N39** | The launch date against the first sale (2026-10-28, M9, D65 of eng_dados) | **`launched_at` drawn between `period_start` and the product's first sale**; null means unknown; invariant 14 is "null, or `launched_at` ≤ `placed_at`" (§5.3) |
| **N40** | Where an inherited description lives (2026-11-03) | **In the dbt `.yml`, like `sensitivity`**: `make catalog` writes the inherited text on each column that only carries its value — in place in the model's `.yml`, or in the generated file —, and `make check` fails when it falls behind; a hand-written text that differs from the inherited one holds only with `description_reason`. With `persist_docs` on, the text reaches the database's column comments, and BigQuery's in the GCP phase. Chosen over deriving it on demand with nothing written, which leaves the manifest, dbt docs and the database blank, and over writing it only in `analytics` and `consumption`, two mechanisms for one rule (§5.4) |
| **N41** | How inheritance crosses the retail–legacy union (2026-11-03) | **The bridge declares its pair, and equal branches inherit**: `legacy/ponte.py` declares, for each bridge column, the `stg_retail__*` column it means, reviewed in full as a declaration; a union inherits only when every branch carries the value and reaches the same text — anything else needs written text. Chosen over a union always requiring text, which would leave about a thousand `trusted` columns and everything downstream of them to stage 1.8, and over the retail branch deciding, which is not conservative (§5.4) |
| **N42** | What the description ratchet counts (2026-11-03, RV2-09) | **A ceiling of undescribed columns per layer**, over the materialised inventory: no layer may exceed the count measured at stage 1.7's delivery, inheritance included, and an improvement lowers the ceiling in the same commit; the same per layer for objects without `domain` or `owner`; inherited and written text reported apart. Chosen over integer-percent floors like the classification ratchet's, which would let about ten new undescribed columns into `trusted` with no change, and over floors from before inheritance (M17), which would not protect what stage 1.7 delivers (§5.4) |
| **N43** | P13's delivered legacy shipments with no accepted item (2026-11-03, runbook O6) | **A pending decision of its own in eng_dados, outside v1.1.0** — D66 there: on those shipments the view diverges from the denominator of [ADR-0033](https://github.com/alencardoug/mvp_eng_dados_1/blob/1e197ac/docs/adr/0033-entrega-medida-em-dois-graos.md#decisão), "the delivered shipments", and the fix would be a shipment-grain fact with its ADR; until then the view's description and P13's report state the population counted. Chosen over fixing it in v1.1.0, which would reopen the runbook's E11 and add a fact in the middle of the maintenance, and over redefining the concept to fit the implementation (M38) |
| **N44** | Columns that carry no source value but follow a project convention (2026-11-03, from the prototype of stage 1.7) | **One text per convention, applied by name and form**: `source_system` as a constant of a declared system and `is_deleted` as `deleted_at IS NOT NULL`, and the columns the tools add (`_airbyte_*`, `_stream_*`, `dbt_*`, `legacy_row_id`) where the tool adds them — each text once, in a `{% docs %}` block of eng_dados; a same-name column of another form gets nothing. Chosen over the name alone, which would label a future same-name column with another meaning silently, and over a hand text at each root, the same sentence dozens of times (M39) |
| **N45** | A union branch that is only a constant (2026-11-03, from the prototype of stage 1.7) | **Neutral**: a literal, a null or a cast of either — the dimensions' unknown member — does not vote; the union inherits when at least one branch carries and every carrying branch reaches the same text, and a union of constants needs text. It refines N41's "every branch carries". Chosen over requiring text for every dimension attribute with an unknown member, and for every view that reads it (M39) |
| **N46** | How far `domain` and `owner` go (2026-11-03, stage 1.8) | **Every object, derived where a declaration exists**: one `owner` per layer in `dbt_project.yml`; the `domain` of every `staging`, `trusted`, `snapshots` and `quarantine` object that conducts a source table is that table's, declared in the SQLAlchemy models — by the model's name, or by a reviewed list where the name does not say it —, written by `make catalog`; seeds and the 41 objects of `analytics` and `consumption` by hand; the legacy objects keep the generator's `legado`; a hand domain on a conducting object holds only with `domain_reason`. Chosen over the 41 of the plan only, which would leave Governance §5.1 unmet in the inner layers, and over 115 hand declarations repeating the source's domain (M40) |
| **N47** | Column comments outside the models (2026-11-03, stage 1.8) | **Snapshots yes, sources no**: `persist_docs` on the snapshots, which issues comments and changes no data; the `raw` and `raw_legacy` sources, which dbt does not build and Airbyte recreates on every reload, keep their text in dbt's catalogue only, a declared limitation. Chosen over commenting the sources from `governance garantir` on every build, and over leaving the snapshots without text |
| **N48** | The text of a source table's primary key (2026-11-03, stage 1.8) | **One text per table**: "Identifier of the order at the source, generated by the transactional database", on each of the 39 `pk()` calls, inherited by 170 columns — the dimensions' natural keys among them. Chosen over a better generic text, which would still not say whose key it is, and over keeping one that reads "generated by the database" in a dimension |
| **N49** | The fixed `false` of `is_deleted` in the append-only tables (2026-11-03, confirmation) | **A second form of the convention** of N44, with its own text, declared once |
| **N50** | How a measure's text is written (2026-11-03, stage 1.8) | **Its additivity, what it measures, and its grain or filter** — "Additive — net revenue of the realised items, summed by month, channel and category" —, with the concept defined once in the Glossary, which the view already points to. Chosen over pointing each measure at the Glossary block, which describes the concept and not the column, and over free text with no common form |
| **N51** | The `domain` of what serves every domain (2026-11-03, stage 1.8) | **A tenth value, `transversal`**, declared in Governance §5.1 beside the nine of the source, for the calendar and the geography — only what conducts no table of any domain. Chosen over the domain of the heaviest user, which would be arbitrary, and over leaving those four objects without one |
| **N52** | How the Owner reviews the written text (2026-11-03, stage 1.8) | **A review page per batch**: for 30 to 50 texts at a time, grouped by domain and from the roots towards consumption, a private page with each column's model, the SQL expression that computes it, the proposed text and how many columns inherit it; the Owner approves or corrects there, and each batch is applied and committed. Chosen over reading the `.yml` diff, which shows the text without the expression behind it, and over reviewing all of it at the end |
| **N54** | The legacy keys the regeneration removes (2026-11-04, H2) | **Accepted and declared**: against "expected: none", H2 found 4 categories added — N37's tree — and 10 legacy keys removed, 2 in `inventory_balances` and 8 in `inventory_movements`, a side effect of the fixes on the draws the stock events come from (M43). They enter `trusted.legacy_removed_records` at stage 1.6 as an effect of the regeneration, declared in the diary and in the v1.1.0 note, and T3(5) expects exactly them, given the H2 comparison (`REMOCOES_ACEITAS=`). Chosen over making the generator keep the legacy key set — code that only hides a one-time effect, reopened by any later change to the generator — and over not regenerating the legacy source, which would leave P01's legacy branch incoherent and fail D5's legacy probes |
| **N55** | Where the retained ledger is decided in eng_dados (2026-11-04) | **A decision record of its own**, eng_dados' 0050, complementing items 4 and 5 of its 0044: the ledger is a new component, which eng_dados' fifth rule gives an ADR, with its GCP counterpart — a Cloud Storage bucket with conditional create and a locked retention, the advisory locks in Cloud SQL, released only once the BigQuery insert commits —, pending stage 13. Chosen over a dated note in 0044, which would leave a new component without its own record. The counterpart, Claude Code's proposal, accepted by the Owner as written at the start of stage 1.6 (2026-11-04) |
| **N56** | The legacy keys the regeneration gives back (2026-11-04, stage 1.6, D4) | **Accepted and declared**: `customers` 1, 2 and 3, removed in eng_dados' stage 11 by the legacy CLI to exercise its ADR 0045 — the open mutation diary of the batch `3f9e5088`, with `campaigns.id` 4 changed to `0x4` —, come back with the pure new batch, and the deletion memory drops them by design ("sai quando a chave reaparece"); their history stays in the retained captures 39–55. H2 compared the batches, not the state: today's legacy was the batch plus its diary, which the reload undoes. So H2 is redone on the actual state — `make generation-compare MANIFESTO_ANTES=` applies the diary to the before side —, and T3 accepts exactly its removals (N54's ten) and its reappearances that the baseline memory held (`REAPARICOES_ACEITAS=`), the rows that remain checked by key, with a note. Chosen over re-applying the mutations now, which needs a new capture and still changes the baseline rows, and over the way back by the cut with the diary re-applied at B4, a destructive restore never proved. The current legacy loses the test mutations of stage 11, and the proof between captures of its removal test now skips until a new mutation |
| **N53** | Reviewing the written text, after batch 0 (2026-11-03) | **Approved as written; the Owner's critique comes on the finished product**: the Owner approved the 45 domains of batch 0 and the remaining text without a batch review, since what can be judged is the product it serves — the showcase. It replaces N52 for the text; corrections found then go into the declaration, never the generated output (§5.4) |
| **N57** | How the whole v1.1.0 is reviewed (2026-11-04, stage 1.9) | **Three batches by risk, each at the highest effort, and the tag only after the last**: batch 1 `33d6451..6d93d72` (stage 1.5, the retained ledger, eng_dados' ADR 0050, the recovery and T3), batch 2 `26b58b3..1e197ac` (stages 1.1–1.3), batch 3 `1e197ac..33d6451` (stages 1.7–1.8); stage 1.9's own documents, already reviewed, and the study track `3ae4ba2..26b58b3` stay out. Chosen over one review of `v1.0.0..` the tip, which would not fit one Codex budget |
| **N58** | A local command to tell the ledger which job is an attempt's (2026-11-05, batch 1, RVL1-2-02) | **Not created**: a recovery that stops on the fixed limit of an attempt's window leaves through the way back by the package (runbook §6) or a resolution the Owner defines, as eng_dados' Legacy Source §4.3 declares with its cost. Claude Code's proposal, accepted as written. Chosen over a manual association command |
| **N59** | How the review cycle of the identity guard ends (2026-11-05, batch 2, after round 6) | **A seventh round on regressions only**: round 6 found only rare, pre-existing forms, none introduced by the fixes, and the seventh checked the fixes for regressions and nothing else. Chosen over closing at round 6 and over an allow-list |
| **N60** | The text of `fact_inventory_movement.quantity_delta` (2026-11-05, batch 3, RVL3-10) | **Additive** — "signed change of the balance: positive on entry, negative on exit; its sum over a period is the net change of the stock in it" —, with `description_reason` saying why. `quantity_on_hand`, a balance, stays semi-additive. Codex's proposal, accepted as written. Chosen over the inherited "Semiaditiva" text, which forbade the time sum the signed movements are built for |
| **N61** | The validity of the SCD dimensions in SQL (2026-11-05, batch 3, rounds 4 and 5) | **Explicit UTC in SQL**: `at time zone 'UTC'` on `valid_from` and `valid_to` of the four SCD dimensions, both `timestamptz`, and the snapshot writes UTC explicitly (`snapshot_get_time`). "There are no real users of this base", so the type change is allowed. Chosen over documenting only the dependence on the session's time zone, and over aligning only the unknown member's null to `timestamp` |
| **N62** | The calendar of the day windows (2026-11-05, batch 3, RVL3-6-04) | **São Paulo, explicit**: every window of days over an instant goes through `dias_no_calendario`, in the `America/Sao_Paulo` calendar of the facts' dates, and `customers`' today is midnight in São Paulo. Measured before and after the build: active customers 497, churn 892, repurchase 243 and closed windows 3,307, all unchanged; only `days_since_last_order` moved, +0.125 day in 1,389 customers. Chosen over leaving the windows on the session's time zone |
| **N63** | Closing the review of v1.1.0 (2026-11-05, after batch 3's round 12) | **Closed with declared limits, no further refining now**: round 12 found nothing new; what was accepted is in eng_dados' owner documents (Legacy Source §4.3, Governance §5.1 and §7, Quality §4), and what was not exercised is its pending item V1, to be taken up before the next change to the code of each batch and at the opening of stage 13, which rewrites recovery, access, catalogue and guards for BigQuery. Chosen over a thirteenth round on the declared limits, which would find adversarial forms rather than defects of the current project |
| **N64** | How Part II opens (2026-11-05) | **Stage 2.2a first, with the Firebase project created by the Owner in parallel**: the envelope needs nothing external and unblocks 2.3 and 2.2b; the project and the protected environment are what 2.2 waits for. Chosen over 2.2a alone, which leaves the project as a later bottleneck, and over 2.2 first, which leaves 2.3 blocked |
| **N65** | The independent reader of stage 2.2a (2026-11-05) | **Python produces, JavaScript reads, on Node's WebCrypto in `make check`**: the producer and the vectors in Python with `cryptography`; the reader a plain ES module on `globalThis.crypto.subtle`, the same API and the same file the site imports; a headless browser only to measure latency. Chosen over a reader in a headless browser inside the gate, which costs a heavy dependency and minutes per gate, and over two Python implementations, which never exercise WebCrypto |
| **N66** | The byte format of the envelope and of its authenticated data (2026-11-05, RV3-01, M23) | **A fixed binary header, whose bytes are the authenticated data**: fixed field order and lengths, big-endian integers, and AES-GCM authenticating the header exactly as parsed ([`docs/encryption_envelope.md`](docs/encryption_envelope.md) §2). Chosen over a JSON header canonicalised by RFC 8785, readable in a diff but requiring two implementations to canonicalise identically — the risk of M23 |
| **N67** | The PBKDF2 iteration count (2026-11-05) | **600,000, the OWASP reference for PBKDF2-HMAC-SHA-256, with the latency measured**: if the desktop browser takes above about one second, the choice comes back to the Owner. The passwords are public (N22), so the count demonstrates practice rather than protecting anything. Chosen over a latency budget of about 250 ms, below the reference and needing a justification, and over a fixed 100,000, a weak parameter to an evaluator who does not read why |
| **N68** | Working through the night of 2026-11-06 (the Owner's mandate, ~00:50 local) | **Claude Code goes on alone, taking the recommended technical choice at each step and recording it**; when the Codex accounts or Claude Code run out, or an essential evaluation of the Owner is needed, it writes down where it stopped and the questions, commits with the gate green and turns the computer off. Push, accepted ADRs, the framework of 2.3 and publication stay the Owner's |
| **N69** | Pushing that night (2026-11-06, anticipated) | **Authorised, one closed delivery at a time**, only with `make check` and `make secrets-history` green and Codex's review without a blocking finding. Chosen over local commits only, which would stop stage 2.2 at its plan |
| **N70** | Creating stage 2.2's external resources (2026-11-06, anticipated) | **Authorised once the plan of 2.2 has no blocking finding from Codex**: the federation from GitHub to Google Cloud (pool, provider and a service account with Hosting only, in project `bi-como-codigo`), the protected environment with the Owner as reviewer and the protection of `main`, each resource written down with how to remove it. The fork test needs a second owner of a repository: an organisation of the Owner's, created on the web, or a simulated event with the limit declared. Chosen over the plan only |
| **N71** | If the browser's derivation goes above N67's second (2026-11-06, anticipated) | **600,000 stays up to 2 s on the desktop, recorded; above 2 s, stop and write it down**. M49 measured 378 ms, so it did not arise. Chosen over lowering the count to fit one second and over waiting |
| **N72** | Ending Codex's rounds when only adversarial forms remain (2026-11-06, anticipated) | **One last round on regressions only, then close with the limits declared**, as N59 did. Chosen over closing at once and over waiting for the Owner |
| **N73** | When eng_dados' stage 13, the replication on Google Cloud, runs (2026-11-06) | **After stage 2.10 and before 2.11, in sequence**: from 2.4 to 2.10 eng_dados stays at v1.1.0 — the exporters read its views by a pinned contract, and the portal and the project's governance are generated from its declarations at a pinned commit —, and stage 13 reopens recovery, access, catalogue and guards for BigQuery (N63). One critical path at a time, and a cost window the Owner can follow; the stage ends with its Google Cloud resources destroyed, as eng_dados' plan has it, and the showcase returns to 2.11. Chosen over starting it now, which delays the showcase and moves what 2.4 pins, and over waiting for Part III — **superseded by N84**: stage 13 runs right after 2.2b |
| **N74** | What the candidate workflow guarantees about tokens (2026-11-06, PIPE-1-02 of the review of 2.2's plan) | **No credential Google accepts, proved by a test**: in a personal repository a same-repository PR can edit its workflow's `permissions` and obtain a GitHub OIDC token, and no setting forbids it; Google's provider refuses that token, since it trusts only `publish.yml` and `promote.yml` on `main`, and the PR gets no preview, since everything under `.github/` is protected. Chosen over keeping the PR from obtaining the token at all, which would mean previews only of the Owner's own branches by manual dispatch and the end of "updating means opening a PR" (N2) |
| **N75** | Approving stage 2.2's test promotions while the Owner sleeps (2026-11-06, ~03:25 local) | **Delegated to Claude Code for that night**: the jobs of the `production` environment that the tests T1–T11 start, all on fixtures, are approved through GitHub's API with the Owner's account, and each such approval is recorded in the evidence as delegated, not as the Owner's. The approval of a real release remains the Owner's own. The Owner's words: "Aprovo antecipadamente que você atue". Extended by the Owner to the morning ("Continue aprovando você") and renewed for the afternoon of 2026-11-06, for T2, T5's delayed schedule, T8 and T10(a) |
| **N76** | What stage 2.2b's gate must catch (2026-11-06) | **What can be seen without the warehouse**: a tampered manifest, a reused key or IV, injected clear data, a view missing or extra, a changed type, a duplicated row and totals that do not match are refused in CI; M19, two labels swapped, keeps every count and sum, so it is caught by stage 2.4's row-level equality with the views on the Owner's machine, and 2.2b's criterion says so. Chosen over a digest of the rows in the totals, which would prove only what the exporter itself wrote, and over the literal criterion, which would need CI to read the warehouse ([`docs/package_gate.md`](docs/package_gate.md) §8) |
| **N77** | How CI reads the Parquet (2026-11-06) | **DuckDB for Python**, a runtime dependency from 2.2b, likely also the exporter's writer at 2.4: the engine family the browser uses (N2). Chosen over pyarrow, larger and another engine, and over no reader, which would move most mutations out of 2.2b |
| **N78** | The control totals (2026-11-06) | **A minimal schema now**, `{"contract_version", "report_version", "rows", "sums"}` with exact decimal strings for the contract's sum columns, recomputed by CI; stage 2.4 may extend it, through the gate's rule. Chosen over leaving every key to 2.4, which would leave mismatched totals untested in 2.2b |
| **N79** | The report contract (2026-11-06) | **Its format born in 2.2b**, `release/contract.json` — columns, types, nullability, grain and sum columns per report —, describing the fixtures; stage 2.4 writes the sixteen views into it, and exporter and gate read the same file. Chosen over a contract born at 2.4, which would leave types, duplicates and the inventory out of 2.2b |
| **N80** | Binding stage 2.2b's live comparison to the promotion (2026-11-06, PGATE-1-01) | **Refuse if live changed**: `verify` records which live envelopes it compared; `preview` binds them, through Hosting's API, to live's version ID — refusing a release within 10 minutes of the read —; `promote`, before the clone, stops if live is no longer that version — the recovery is a new PR. Refined after PGATE-4-01, which showed envelope paths alone let a returning package through. Chosen over recomputing the comparison inside `promote`, which would put decryption in the job that holds a credential ([`docs/package_gate.md`](docs/package_gate.md) §5.2) |
| **N81** | What counts as clear report data in the artifact (2026-11-06, PGATE-1-03) | **Every decrypted value, with a public list**: no text of 3 or more characters and no number of 3 or more significant digits or with a fraction — canonical or Brazilian form —, nor the totals, outside an envelope, except the values a protected `release/public_values.json` lists with their reason. Chosen over a row-proximity heuristic and over long-value thresholds, which let a short row through (package_gate §6) |
| **N82** | The domain of the control sums (2026-11-06, PGATE-1-05) | **Only `SMALLINT`, `INTEGER`, `BIGINT` and `DECIMAL` up to 18 digits are summed**, so DuckDB's 38-digit accumulator cannot overflow within an envelope's bound. Chosen over summing in Python, which would materialise every column and leave DuckDB (package_gate §2.1) |
| **N83** | The manifest in stage 2.2b's value inspection (2026-11-06, PGATE-2-03) | **Only its free text, the profile labels, is searched**: its other fields are strictly typed and bound to the package by its checks, and mandatory values such as `iterations: 600000` would collide with honest data. Chosen over searching every field with the public list, which random salts and ids would make unpredictable; a number hidden in a typed field by a hostile author is a declared limit (package_gate §6, §11) |
| **N84** | When eng_dados' stage 13 runs, revised (2026-11-06, ~18:45 local; supersedes N73's order) | **Right after stage 2.2b**, in a session opened in eng_dados, ending with its Google Cloud resources destroyed; then 2.3 to 2.10 here, pinned to the eng_dados commit accepted after it. Nothing of 2.3–2.10 is an input of stage 13 — it replicates eng_dados' own flow and reads eng_dados' own data governance (classification, descriptions, `meta:`, lineage), done in Part I; the portal (2.7) and the project's governance (2.8) consume it, they do not produce it — and the showcase reads eng_dados by pinned commits, so later changes there break nothing here. The Owner's words: "Se houver alguma destas etapas que possamos postergar para viabilizar que a replicação do GCP seja realizada o quanto antes, melhor." Chosen over a reduced first publication after 2.6 and over N73's order — **its pin replaced by N85** on 2026-11-13 |
| **N85** | Which eng_dados commit stages 2.4 to 2.10 pin, after eng_dados moved to `mvp_eng_dados_2` (2026-11-13; §3.5.1; revises N84's pin) | **A commit of `mvp_eng_dados_2` after its audit of the 16 views**: the first publication carries no number already known to be wrong. Stage 2.4 waits for that audit; 2.3, on invented data, does not. N84's order stands — stage 13 is done —; only its "commit accepted after stage 13" is replaced. Chosen over `f86b9fb` exported before `mvp_eng_dados_2` rebuilds the shared warehouse, which needs the two sessions coordinated and publishes values the source already knows are wrong, and over `f86b9fb` with the divergence declared as a known limit, where the pin no longer describes the warehouse that was read |
| **N86** | How the gate lives with two sources (2026-11-13; §3.5.1) | **Two checkouts**: `ENG_DADOS_DIR` keeps naming mvp_eng_dados_1, for the historical pinned links, and a second variable names `mvp_eng_dados_2`; `docs-check` verifies each pinned link against the repository its URL names. Implemented in a PR of its own — `docs_check.py` and the `Makefile` are protected. Chosen over one local mirror holding both histories, which can let a commit of one repository pass for the other unless the check separates them by URL, and over linking `mvp_eng_dados_2` unverified |
| **N87** | Stage 2.7 and `gdados`, two reading portals of the same governance (2026-11-14; taken in `mvp_eng_dados_2`'s session as its Q12, recorded at `32397cc` in its `PLANO_base_dos_consumidores.md` §6; closes the question of §7) | **Two portals, reading the one metadata package** of `mvp_eng_dados_2` (its D91): each keeps the scope of its own plan; the part they share — catalogue, questions, vocabulary, lineage — comes from the same package and cannot diverge; neither waits for the other. Stage 2.7 reads the package for the metadata it covers, not the manifest and YAML by commit; documents, ADRs and the glossary's text are still read by commit (§3.5); what its format 1 lacks for the nine chapters is asked as UQ-12 to UQ-15 of [`docs/upstream_questions.md`](docs/upstream_questions.md). N85's pin for 2.4 onwards stands. Chosen over two portals with divided scopes — the showcase pointing at `gdados`, so that the public showcase would depend on `gdados`' D04 —, over `gdados` alone and over 2.7 alone |
| **N88** | New resources on Google Cloud (2026-11-14; taken in `mvp_eng_dados_2`'s session as its Q14, recorded at `32397cc`, its Consumidores §7) | **None, in any project.** What exists here stays as it is — the Firebase project `bi-como-codigo`, the federation and the service account of N70, billing off (M53) —: nothing changes for the showcase, but nothing new is created on Google Cloud. It reaches N18's fallback, a `*.web.app` of the study content's own, which would be a new Firebase project: how is the Owner's (§7). The Owner's answer there was outside the options offered, which were about when `nl_sql` brings up a Google Cloud project of its own |
| **N89** | The pin of stages 2.4 to 2.10 and of the metadata package, after eng_dados' tag `v2.1.0` (2026-11-17; §3.5, §3.5.1; revises N85's commit, not its rule) | **`eb11709`, tag `v2.1.0` of `mvp_eng_dados_2`, for the views and for the package alike** — the tag that closes its consumer-base phase, the mark its Consumidores §6 says to prefer, with the models and the data of the regenerated warehouse, built `verified` from `4137dc7` (M55). It replaces `4da9e60`, the end of the audit of the 16 views that N85's rule named, and the package's `acb26d0` and `19c0e80` — three pins announced on 2026-11-14 and 2026-11-15 and never transcribed here. Package format still 1. N85's rule stands: a commit after the audit. Given by the Owner as an instruction, on that repository's notice of 2026-11-17; no alternative was put |
| **N90** | The pin of stages 2.4 to 2.10 and of the metadata package, after eng_dados' tags `v2.2.0` and `v2.3.0` (2026-11-19; §3.5, §3.5.1; revises N89's commit, not N85's rule) | **`2bceb47`, tag `v2.3.0` of `mvp_eng_dados_2`, for the views and for the package alike**, straight from `v2.1.0` — the mark its Consumidores §6 says to prefer, built `verified` from `bcc2d5c` (M59). Against `v2.1.0`, P08 and P11 no longer carry its streaming exercise (M58, UQ-16), P11's turnover is sized by demand, and P12 reads each pair's own reorder point (its ADR 0057); the other 13 views are identical and no view changed schema (M59). Package format still 1 (M60). Chosen over `v2.2.0`, where the fixed point of 25 units leaves 94% of the pairs below it and P12 separates nothing, and over staying at `v2.1.0`, whose P08 and P11 are known wrong. Taken by the Owner on 2026-11-19, with the recommended answers |
| **N91** | The pin of stages 2.4 to 2.10 and of the metadata package, after `mvp_eng_dados_2` answered UQ-21 to UQ-23 (2026-11-20; §3.5, §3.5.1; revises N90's commit, not N85's rule) | **`b0ef66e` of `mvp_eng_dados_2`, for the views and for the package alike** — the commit its answer of 2026-11-19 says to pin, three commits after `v2.3.0` and on its `origin/main`, with no tag. No file under `dbt/` changed and no warehouse build ran since `2bceb47`, so the 16 views and their data are those M59 captured; the package differs only in what was asked — each audit's `commit` is that of the definition it checked, V5 to V7 left `open_items` — and in a new run of its `checks` (M61). Format still 1. Given by the Owner as an instruction on that answer ("avalie e atue"); kept at `2bceb47` was the alternative, a package whose audit commits and open items the source itself corrected |
| **N92** | Notices between this repository and the Owner's other projects (2026-11-20; §3.5.1; asked by `mvp_eng_dados_2` in its answer of 2026-11-19) | **A mailbox, as asked**: `alinhamento.md` at the root, with the usage note copied verbatim from that answer, in Portuguese, empty after its line "a partir daqui"; `/alinhamento.md` in `.gitignore`, so it never reaches GitHub; and a first line of `CLAUDE.md`, in Portuguese as recorded, that loads it at the start of each session — read, act, delete, the result recorded in this repository's own documents. A notice that asks to delete, change infrastructure, incur a cost or publish goes ahead only if it cites the Owner's approval, with date and session. Keeping the notices in that project's `avisos/` folder, carried by the Owner, was the alternative: nothing foreign would load as an instruction here, at the cost of notices left untranscribed, as those of 2026-11-14 and 2026-11-15 were until 2026-11-17 |
| **N93** | The pin, after `mvp_eng_dados_2` moved on to `2ea212b` (2026-11-20; §3.5.1; keeps N91) | **`b0ef66e` stays.** `8bd62f3` and `2ea212b` only register its V8 — multicloud parity pages and the structured grain for `nl_sql`, nothing implemented — and its Consumidores §5 row: `open_items` goes from 4 to 5, and no relation, view or build changes. The pin follows the next tag or the next change of what the views carry. Moving to `2ea212b`, which its answer names, was the alternative: one more capture and check for a change that reaches no report |
| **N94** | Where the framework candidates of stage 2.3 load the engine from (2026-11-20; [`docs/framework_prototype.md`](docs/framework_prototype.md) §2.4; from FPROTO-3-03) | **jsDelivr, pinned, in both**, as N2 and §3.4 already have it — Evidence too, which bundles DuckDB-WASM and serves it from the page's origin as it comes, through its probe A7; if no arrangement of Evidence does it, that is its measured cost. The engine's 34 MB would count against Hosting's quota at every first load, and its bytes hold almost every short integer, which the gate's value inspection reads as data: round 3 found each row count the plan allowed, 220 to 226, in both of its WASM files. With it, the fixture's integers grow to five digits or more. Keeping the engine on the page's origin with only larger numbers was the alternative, which would hide what real three-digit counts would meet at 2.5; so was a change to the gate's inspection of third-party files, left to 2.5 |
| **N95** | What the oracle of stage 2.3 guards against (2026-11-20; [`docs/framework_prototype.md`](docs/framework_prototype.md) §1; from round 4 of its review) | **The ordinary behaviour of each candidate**: what its framework, its libraries and the browser do on their own — caches, prerendering, storage, workers, history — and the page code this repository writes, which Codex reviews. Code of ours written to deceive the oracle, and a compromised dependency, are outside it and written as a residual risk. The review of the plan goes on until no blocking finding is left. Treating every way the reviewer can find to hide data as blocking, our own code included, was the alternative: a stronger oracle, at the cost of rounds that each found finer cases before anything was built |
| **N96** | What the verdict of stage 2.3 judges, and where the browser's oracle is built (2026-11-20; [`docs/framework_prototype.md`](docs/framework_prototype.md) §1, §2.5.3; from round 7 of its review) | **The finished build output, as the criterion of §6.2 says**: `verify` and the inspection of the builder output and the artifact. What each candidate does in the browser — what it stores and persists, what survives logout, when it decrypts — is measured and reported as part of the comparison, not judged. **The complete browser oracle is built at stage 2.5**, for the chosen framework only, with its own plan and review, starting from what 2.3 observed. Keeping the browser as a gate in 2.3 was the alternative — by hooking each storage API, which seven rounds did not close, or by scanning the profile on disk —, at the cost of an open number of rounds before anything was built |
| **N97** | How the review of stage 2.3's step 1 closes (2026-11-21; [`docs/framework_prototype.md`](docs/framework_prototype.md) §7, §9; from rounds 3 to 5 of the review of its implementation) | **Closed after round 5's corrections, with no round 6**, an exception to N95's "until no blocking finding is left": five rounds found 63 findings on the implementation, 8, 7, 8, 7 and 8 of them blocking, each round's finer than the last, and the oracle is better tested from step 2 on, on the candidates' real output. Out of the review, as recorded limits: the isolation wrapper and its self-check from round 3, and the browser diagnostic of §2.5.3 from round 4 — Codex's provider ended sessions that read them —; round 5's corrections are unreviewed. The complete review of the implementation stays at step 7. Going on to round 6 was the alternative, at the cost of more rounds of edge cases before any candidate is built |
| **N98** | Whether a page may load DuckDB's extensions from `extensions.duckdb.org` (2026-11-22; [`docs/framework_prototype.md`](docs/framework_prototype.md) §4, §9; from the clear mode of Candidate B) | **Yes, pinned by URL and digest, as a second third-party origin beside jsDelivr.** DuckDB-WASM 1.32.0 reads no Parquet without its `parquet` extension, which npm does not publish and which its worker fetches from DuckDB's host, unpinned, as it comes; Candidate B declares it in its `cdn.json` and loads the checked bytes itself, with autoloading off. The alternatives were serving the extension from Hosting — 3 MB against the quota and in the artifact the gate inspects, which N94 avoided for the engine — or a payload the engine reads with no extension, a change to the envelope's format of 2.2a |
| **N99** | Whether the carrier inspection of stage 2.3 changes for Evidence's encrypted builder output, outside N97's review (2026-11-22; [`docs/framework_prototype.md`](docs/framework_prototype.md) §2.5.2, §9; from the first draw against both builder outputs) | **Yes, narrowly, reviewed with the implementation at step 7.** Seven notes left the output inconclusive and stopped the draw for both candidates, none of them data: three SvelteKit fetched-data scripts of `index.html`, read as they are on the page, broken by the speculative layer of string escapes, which turns the `\"` of their nested JSON into `"` — six notes over two layers —; and a 2.5 MB chunk of Evidence's component library that the HTML-entity decoder read again and again past the depth, because `&t;` looks like an entity and decodes to itself. Two rules: a decoding whose output equals its input is no layer; on a layer a flat decoder made — percent, escapes, entities —, a JSON script that does not parse is searched as a data-bearing carrier, every integer needle in any spelling, and recorded, not inconclusive. The alternatives were the same change reviewed by Codex before the draw — a round more —, keeping the inspection and leaving Evidence's verdict not established — an incomplete comparison —, and a build of Evidence that writes neither, which would take a patch of its component library |
| **N100** | How the draw of stage 2.3 goes on once it is measured impossible against Evidence's builder output (2026-11-22; [`docs/framework_prototype.md`](docs/framework_prototype.md) §3, A8; from the first draw against both builder outputs) | **A probe of Evidence's build with its brand icons cut, A8, then the draw against both.** Evidence's `component-utilities/icons` re-exports the whole of `@steeze-ui/simple-icons`, 3,225 icons and 4.8 MB of SVG paths, into one chunk of the build: there every year from 2000 to 2199 is spelled as the gate searches it (`2.024`), so no calendar window of the draw can be clean, and 72.5 % of the five-digit counts are taken — 2.4 % without that chunk, with 15 clean six-year windows. The same chunk would make the gate refuse a release of real data, whose years are 2023 to 2026. A8 is a Vite plugin of ours beside A7's, answering that package with the four icons Evidence's header imports, copied from it as installed; no module of Evidence is patched. The alternatives were recording Evidence as stopped by an exhausted draw and going on with B alone — an incomplete comparison —, or going on with B first and probing A8 after, with B's work redone if A8 succeeded |
| **N101** | Working on from stage 2.3's step 4 (the Owner's mandate, 2026-11-22, ~07:45 UTC) | **Claude Code goes on alone, taking the recommended technical choice at each step and recording it**; consulting Codex is no stop; before stopping on a question or for any other reason it writes down where it stopped, commits with the gate green and turns the computer off. Push, accepted ADRs, the framework of 2.3 and publication stay the Owner's |
| **N102** | Which runs the verdict of stage 2.3 judges once the harness changes (2026-11-22, Claude Code's choice under N101; [`docs/framework_prototype.md`](docs/framework_prototype.md) §2.5.4, §5) | **The runs of the harness that compares the candidates.** A change of the harness already discards the draw, the artifacts and the measures (§5); it now also closes the records made under the old harness into the state's `history`, kept and reported, and the verdict judges the records of the current one. Otherwise every build archived during development and never carried through — Evidence's before A8 among them, whose icon chunk the measured fixture was not drawn against — would hold the verdict open, or fail it on a coincidence the draw never saw. The alternative was carrying every archived builder output of every harness through the measured fixture's stages |
| **N103** | How the review of stage 2.3's comparison closes (2026-11-23, the Owner's decision; [`docs/framework_prototype.md`](docs/framework_prototype.md) §7, §9, §10; from rounds 1 to 3 of its review) | **After a last round of regressions only.** The full run at `a4f333f`, under way when the Owner decided, is the last; round 4 of Codex reviews only regressions of round 3's corrections, failures on the real artifacts and previous findings left open, and no further full run is made unless a regression changes a verdict; whatever else stays open is a declared limit, in the dossier and in §9. In four full runs the verdicts never changed — both candidates pass —, and rounds 1 to 3 found 12, 10 and 9 findings, all in the harness's robustness on paths the real runs never took, each cycle costing about four hours of the machine. The alternatives were closing at once, a faster gate in `src/bi_como_codigo`, and rounds until none blocked |
| **N104** | The chart of the reports (2026-11-24, the Owner's decision; [`evidence/20261124/`](evidence/20261124/README.md#the-charts-interactions-approved-by-the-owner-n104); from the screenshots after ADR-0004) | **A legend that highlights and isolates, and a vertical with every series at the month**: hovering a legend label or a line highlights that series and fades the others; a click on a label or near a line isolates it, shift-click adds another, and a double-click restores all; a vertical follows the pointer to the nearest month and its popup lists every series at that month, by value, in pt-BR — a series with no row there reads "Sem vendas neste recorte." and the partial month carries its notice. The popup is the page's own code: the alternative, the `vega-tooltip` plugin, would be one more library pinned on jsDelivr; Vega's own tooltip is the browser's plain title text. Built at stage 2.5, from the demonstration over B's artifact. With it, the Owner finds B ahead of or equal to Evidence on every point the comparison weighed |
| **N105** | The exporter's PostgreSQL client (2026-11-24, the Owner's decision; [`docs/exporter.md`](docs/exporter.md) §3; from round 1 of its review, EXP-1-13) | **psycopg 3**, a new runtime dependency pinned in `uv.lock`: typed values, one connection under the exporter's control over the published port, no container named. Chosen over the host `psql` client, which this machine does not have and which would carry every value as text into a parser of ours, and over DuckDB's `postgres` extension, downloaded at run time and with connections of its own, so one snapshot for the 16 views would not be the exporter's to guarantee; `psql` inside the container is no longer run from here |
| **N106** | The precision and scale of the views' unconstrained `numeric` columns (2026-11-24, the Owner's decision; [`docs/exporter.md`](docs/exporter.md) §4.2; from round 1 of its review, EXP-1-04) | **Per column, measured**: the scale is the most fractional digits M59 found, the integer part the most integer digits plus three, and the precision at most 18 — 12 at the widest today (`evidence/20261124/m59_profile.out.txt`) —; a value that does not fit refuses, and the contract changes by a PR. Chosen over one wide type for all, which fixes a scale no view declares and leaves N82's domain, and over asking `mvp_eng_dados_2` to declare them, the right owner but a change there and a new pin |
| **N107** | Which columns the control totals sum (2026-11-24, the Owner's decision; [`docs/exporter.md`](docs/exporter.md) §8; from round 1 of its review, EXP-1-06) | **Every column N82 admits**, additive or not: checksums inside the encrypted payload, recomputed by CI and never shown — every view has sums, P16 included. Chosen over the additive columns only, which left P16 with none and narrowed what CI checks; no page adds up a non-additive column (M4, M20) |
| **N108** | Honest report values that also appear in public text (2026-11-24, the Owner's decision; [`docs/exporter.md`](docs/exporter.md) §10; from round 1 of its review, EXP-1-07) | **Approved one by one into `release/public_values.json`**, with the reason, in a protected PR (N81's rule) — the year 2026, in P08 and in `site/releases.md`, the first. An exempted value is not searched in any report, which each entry says. Chosen over removing the years from public text, which every dated page would hit again, and over a change to the protected inspection |
| **N109** | How the trusted declarations move from the fixtures to the 16 reports (2026-11-24, the Owner's decision; [`docs/exporter.md`](docs/exporter.md) §11; from round 1 of its review, EXP-1-08) | **In stage 2.4, in one protected PR**: the view contract, the generated report contract, the profiles — Diretoria 16, Logística P13 — and `site/package/` replaced by invented envelopes of the 16 real shapes, with the tests; the real package enters later in an ordinary PR, with its preview, at 2.5. Chosen over leaving it all to 2.5, where a PR touching `release/` would carry the first real package with no preview |
| **N110** | How the review of the exporter's plan closes (2026-11-24, the Owner's decision; [`docs/exporter.md`](docs/exporter.md); from rounds 1 and 2 of its review) | **After round 3, of regressions only**: it reviews revision 3's changes for regressions and the findings of rounds 1 and 2 still open; whatever else remains is a declared limit, carried to the review of the code, whose mutations test each check. Rounds 1 and 2 found 10 and 8 blocking findings, the second at the level of implementation detail. The alternatives were open rounds until none blocked, and closing with no round 3 |
| **N111** | What check 8 accepts when the warehouse's collation has no version (2026-11-24, the Owner's decision; [`docs/exporter.md`](docs/exporter.md) §3 check 8; from XIMPL-1-03 of the review of its code) | **"No version" accepted, explicitly**: the warehouse's libc `en_US.utf8` on Alpine (musl) reports no version, stored or effective; the accepted build declares that it has none, the receipt records it as unavailable, and a version that appears, or a stored and an effective that differ, refuses. The fingerprint orders the rows by the database's collation, so a change of behaviour that reorders these rows changes it and refuses the run; a library change that reorders none of them passes unseen. The alternative was to refuse until the warehouse has a versioned collation, a change of `mvp_eng_dados_2` |
| **N112** | How the witness binds the rows exported (2026-11-24, the Owner's decision; [`docs/exporter.md`](docs/exporter.md) §3; from XIMPL-1-08 of the review of its code) | **One evaluation**: one statement materializes the view once (`WITH t AS MATERIALIZED`) and returns its rows and M55's fingerprint over them, so the hash attests exactly the rows frozen; the first live run proves it reproduces M59's hashes. The alternative was two statements with the views' determinism declared as a precondition |
| **N113** | How the review of the exporter's code closes (2026-11-24, the Owner's decision; [`docs/exporter.md`](docs/exporter.md) §15 step 4; after round 1 of that review, XIMPL-1-01 to -13, seven blocking) | **Round 2 open; if it still finds a blocking finding, round 3 is the last, of regressions only**, and whatever else remains is a declared limit, as under N103 and N110. The alternatives were rounds until none blocked, and not sending round 2 yet |
| **N114** | The order of the protected PR of stage 2.4 and its live run (2026-11-24, the Owner's decision; [`docs/exporter.md`](docs/exporter.md) §15, steps 4 and 5) | **The live run first, then one PR**: `export collisions` and `export run` run on the branch, locally, in a read window the Owner opens, with no push; the real collisions approved in `release/public_values.json` and the witness's outcome join the same branch, and the Owner reviews a single protected PR, guided by a private page listing what needs the Owner's eye. Both may change protected files (N108, §3), so reviewing and merging before the run would call for a second protected PR. The alternatives were the plan's order, PR then run, and a PR opened now and merged after the run |
| **N115** | How stages 2.5 to 2.10 are reviewed (2026-11-24, the Owner's decision; supersedes, for them, the review rule of [`CLAUDE.md`](CLAUDE.md) §5) | **A return point, then no Codex rounds per stage**: the tag `checkpoint-2.4` marks the commit of `main` where stage 2.4 is merged; each stage from 2.5 to 2.10 begins with a short written plan, its criterion and its decisions, that the Owner approves before the code; Codex reviews only stage 2.6 — the per-profile access and the decryption in the browser, the riskiest — and, at 2.10, everything since the tag, as 2.10's criterion already asks. Everything else stays: `make check` before each commit, the package gate, the protected workflow, the Owner's authorisation of each push and review of each PR. If it goes wrong, the work returns to the tag; what was pushed, previewed or published is not undone by it. The alternatives were one review at 2.10 only, none at all, and code with no written plan |
| **N116** | How `verify` treats a report page's own code (2026-11-25, the Owner's decision; [`docs/report_page.md`](docs/report_page.md) §2, §6 D1; from M62) | **A value counts only where it stands as a token**: no letter, digit or non-ASCII byte touches it, nor, for a number, a separator followed by a digit. Every non-envelope file of `deploy/` is still searched, the page's code included, and the hits inside hashes, longer numbers and identifiers go; the few token hits left leave the code or are approved one by one under N108. A change to the protected gate, in a protected PR with [`package_gate.md` §9](docs/package_gate.md#9-the-mutations-and-their-tests-n76)'s mutations proved again, reviewed by Codex at 2.10 (N115); a value glued to letters, `1234px`, is no longer found, a declared limit. The alternatives were approving each substring hit under N108 — hits that move with every hash, each approval unsearching that value in all 16 reports — and exempting the page's files by a protected list of digests, which would make every edit of the page a protected PR with no preview |
| **N117** | The order of stage 2.5's ordinary PRs (2026-11-25, the Owner's decision; [`docs/report_page.md`](docs/report_page.md) §5, §6 D2) | **The page first, on the invented fixture, then the real package**: the page is proven on a preview with harmless data before real data reaches one. The alternative was one PR with both, a cycle less, with real data on the page's first preview |
| **N118** | Light and dark in the reports (2026-11-25, the Owner's decision; [`docs/report_page.md`](docs/report_page.md) §3.4, §6 D3) | **The system's scheme only, `prefers-color-scheme`**: no toggle and no store, so the page still writes nothing. The alternatives were a toggle that resets at each load, and one remembered in `localStorage`, a store the browser oracle would have to allow |
| **N119** | Where stage 2.5's browser checks run (2026-11-25, the Owner's decision; [`docs/report_page.md`](docs/report_page.md) §4, §6 D4) | **Tables, chart, interactions and accessibility, on the invented fixture, in `make check`**; N96's browser oracle and the checks on the real package in targets of their own, run before each PR and against each preview. `make check` needs Chrome and no real data. The alternatives were everything in `make check`, slower and needing the real package locally, and nothing in it, which would leave a regression of the page to the PR |

### 1.3 Consequences

- N2 settles the former N13: updating the showcase means opening a PR with the new package (§3.4).
  It also replaces the single-file design of revision 1 (RP-10).
- With N23, O7 adds no component: Hosting still serves everything, and the reports go encrypted
  (§3.2). The study content reads the showcase reports by URL and opens them with the password of
  Diretoria (§3.3); the probe of stage 3.1 tests WebCrypto inside the Artifact.
- O6 settles the former N9: the study of the governance lives in the study content; the showcase
  has the reading portal.
- With N2, the showcase lives in a Firebase project of its own; if the probe sends the study content
  to a `*.web.app`, it gets its own as well, for the same reason — no shared quota. The former N19
  needs no question.
- N6 and N20 put Part I at the front of the queue.
- N16 leaves the dimensional model out for now: stage 2.12 exists only if a report asks for detail.
- O8 and N25 moved this plan, the review and the evidence out of eng_dados into this repository.
  eng_dados records only what Part I needs, as it is executed (§5.6).
- N24 sets the language of construction here; the evidence stays as recorded, in Portuguese.
- In the dimensional model, the `personal` fields are name, a document with the `SIN` suffix, date
  of birth and an e-mail at `example.com` — no phone number (M16). The phone caveat (RP-15) only
  comes back if `trusted` or `raw` are published.
- The round-2 review changed how the plan implements the decisions, not the decisions. Encryption
  moves to the export on your machine, so no clear report data ever enters the public repository
  (RV2-01); publication gains three gates and a trusted workflow (RV2-03 to RV2-05); the envelope is
  specified (RV2-02); description inheritance becomes conservative (RV2-08); the recovery package
  follows its full lifecycle (RV2-06).
- Round 3 completed the trust boundary of publishing: the credentialed job runs only reviewed
  code from `main` and treats the candidate as data (RV3-02); promotion goes by version ID
  (RV3-03); the envelope gets a byte-level format (RV3-01); and the stage table puts the workflow
  (2.2) and the complete gate (2.2b) before any real report reaches Hosting (RV3-04).

---

## 2. What was measured

M1–M18 were read in a `default_transaction_read_only=on` session on the running warehouse, between
2026-10-23 00:12Z and 01:22Z (2026-10-22, 21:12 to 22:22 in Brasília), on commit `26b58b3`. The view
was read as `analyst`; the inner layers, by the superuser in the same read-only session; the files,
with no database. M19–M22 reproduce the round-2 review on 2026-10-23 at 03:52Z, and M23 the round-3 probe at 04:23Z,
on the same commit. M24–M26 were taken for the regeneration runbook of stage 1.4 on 2026-10-23,
between 13:54Z and 14:10Z, on eng_dados at `1e197ac`, through read-only targets and tracked files.
M27–M30 reproduce round 1 of the runbook's review, between 14:36Z and 14:44Z, on the same commit,
in read-only sessions and one probe with no database; M31–M33, round 2, between 15:37Z and 15:39Z,
the same way and on a model in a temporary directory; M34–M35, round 3, at 19:50Z and 19:51Z, in
read-only sessions and one listing of Airbyte's jobs; M36, round 4, on 2026-10-28 between 18:12Z
and 18:15Z, in read-only sessions and through `docker inspect`; M37 at 23:45Z, from the process
table; M38 on 2026-11-03 at 16:28Z, in a read-only session; M39 between 16:36Z and 16:55Z, from
the manifest alone; M42 on 2026-11-04 at 03:51Z and 03:55Z, in memory; M43 at 06:06Z, in memory, beside T2's calibration of 2026-11-03 at 21:35Z, read-only; M44 between 04:04Z and 06:12Z, in read-only sessions; M41 at 20:57Z, after a green `make check`; M40 at 18:18Z, after a green `make check` on eng_dados, in a read-only session
and through eng_dados' own modules; M47 on 2026-11-06 at 02:48Z (2026-11-05, 23:48 in Brasília), in Node, with no database; M49 at 03:44Z, in Chrome headless, and M48 at 03:48Z, on the working tree, both with no database; M50 at 04:21Z, from the installed CLI's code; M51 at 06:39Z, from GitHub's log of the run; M53 on 2026-11-13 at 23:47Z (20:47 in Brasília), read-only, from the Cloud Billing API and an HTTP request; M54 at 23:54Z, from the public npm registry; M55 on 2026-11-17 at 14:49Z and 14:52Z (11:49 and 11:52 in Brasília), in two read-only transactions through `consumption_reader`, on the warehouse built from `4137dc7`; M56 and M57 at 14:53Z, from files and Git only; M58 at 15:47Z, in a read-only session as the superuser; M59 on 2026-11-19 at 22:44Z and 22:46Z (19:44 and 19:46 in Brasília), in two read-only transactions through `consumption_reader`, on the warehouse built from `bcc2d5c`, compared at 22:45Z from files only; M60 at 22:46Z, from files and Git only; M61 on 2026-11-20 at 03:06Z, from files and Git only. Literal outputs in the evidence folders.

| # | What | Result | Consequence |
|---|---|---|---|
| M1 | The P01 view | 1,140 rows; 33 months (2024-01 to 2026-09); 3 channels; 4 root categories and 12 leaves; R$ 33,076,529.47 of net revenue; ~96 kB as text | — |
| M2 | P01 recomputed from the fact table, at the same grain | 0 rows diverging in count or revenue | An oracle for the custodian — the exporter never reads the fact table (§3.5) |
| M3 | Order count without `source_system` | 126 `order_id` values exist in both sources. P01 and P02: no group affected today. **P05 and P06 undercount one order in one group each**: P06 2025-07 · Aplicativo · Eletrônicos (11 × 12); P05 2024-T4 · Aplicativo · SP (20 × 21) | A real defect in the datamart, against the rule of the `empilhado` macro — "the source goes into the condition with the key, always". No test catches it |
| M4 | Realised orders with items in more than one category | 2,479 of 3,292 | P01's `order_count` does not add up across categories, and P01 does not even declare it as a measure in the [Glossary](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/glossario_de_negocio/perguntas_de_negocio.md#p01--qual-a-receita-líquida-por-mês-canal-e-categoria-de-produto) |
| M5 | Coverage | first realised sale on 2024-01-02, last on 2026-09-01 (`as_of_date`). 2026-09 has 3 groups, 9 units and R$ 17,795.87; the other months, R$ 0.65 M to R$ 2.07 M | 2026-09 is a one-day month: the monthly chart would show a drop that does not exist |
| M6 | Month × channel × category combinations with no row | 15 in complete months; 33 in 2026-09 | A slice with no sale, distinct from zero |
| M7 | Category tree | most leaves sit under an unrelated root: "Moda › Notebooks", "Moda › Sofás", "Eletrônicos › Panelas", "Eletrônicos › Camisetas", "Casa e Cozinha › Calças". The parent is assigned round-robin (`generator/domains/catalogo.py`) | The main axis of P01 has no business meaning |
| M8 | Price by category, in the retail source | average from R$ 1,970 (Caixas de som) to R$ 2,930 (Organizadores), overlapping ranges from R$ 63 to R$ 6,939. The base price comes from a single range for every product (`geracao.yml`: `faixa_de_preco: [9.90, 4800.00]`) | Contradicts [Data Generation §5](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/geracao_de_dados.md#5-realismo-e-coerência), which states the affinity between product, category and price as implemented |
| M9 | Sale before launch (D65) | 3,130 of 7,500 retail items — the same number as on 2026-10-04 | Still open |
| M10 | `ORD-0000037` | two different orders with the same number: in the legacy source, 2024-12-09, Eletrônicos; in retail, 2025-07-01, Moda and Eletrônicos — the latter is the case cited in D65 | A bad example for the first lesson; a good hook for the lesson on composite identity |
| M11 | Decimal scale in `trusted.order_items` | retail: discount with scale 0 to 2 and price 0 to 4; legacy: always 2 and 4 | Format by the declared scale, never by the text the database returns |
| M12 | Column lineage — a prototype that walks `Lineage.leaves`, reimplementing nothing | `net_revenue_amount`: 15 nodes and 14 edges down to `raw` and `raw_legacy`, 0 problems, complete manifest (192 models), 20 to 30 s. `year_month` ends at `dim_date` (generated); `category_name` reaches the name in `raw.product_categories` without going through the temporal join of the product; the legacy branch jumps from `raw_legacy.order_items` straight to `legado__order_items` | Value lineage answers "where does the value come from". Membership and controls need a small declaration |
| M13 | Size of the warehouse | **588 MB** for the whole database: `raw_legacy` 206 MB, `trusted` 138 MB, `raw` 86 MB, `quarantine` 77 MB, `analytics` 50 MB, `staging` 8 MB, the rest under 1 MB; `consumption` is views | The bulk is what comes before the product: bringing the database makes no sense |
| M14 | The analytical product in Parquet (zstd) | 25 `analytics` tables and 16 views: 162,351 rows, **8.10 MiB**. The views alone: 15,377 rows, 0.23 MiB; the largest, `inventory_turnover_by_sku_and_warehouse`, 77 KiB. The largest table, `fact_cart_event`: 81,199 rows, 3.4 MiB. Exported in 4.0 s | It fits in files on the site itself, encrypted per report |
| M15 | DuckDB-WASM engine 1.32.0, of 2025-12-16 — the latest stable on npm | **6.8 MB** downloaded with brotli, 7.6 MB with gzip and 34.2 MB uncompressed, stable over three reads. The first read gave 5.2 MB, from another CDN node — unexplained | Served by free Firebase, the 360 MB/day quota would hold ~50 first visits a day. That is why the engine comes from jsDelivr |
| M16 | `personal` fields in `analytics` | 9 columns: first name, last name, full name, document and birth date in `dim_customer`; first name, last name, full name and e-mail in `dim_support_agent`. No phone number | The phone caveat does not apply to the dimensional model |
| M17 | Catalogue coverage, in the dbt manifest | Classification, lineage, access and retention complete; 700 data tests. **Column descriptions**: `analytics` 26 of 477, `consumption` 31 of 188, `trusted` 56 of 1,069, `staging` 659 of 1,114, `raw` and `raw_legacy` 0 of 1,161. **`domain` and `owner`**: 0 of the 41 objects in `analytics` and `consumption`, although [Governance §5.1](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#51-padrão-de-metadados) requires them on every model | A reading portal with blank descriptions contradicts what it shows; the rule of §5.1 is not met today |
| M18 | Descriptions inheritable through lineage — an estimate, **superseded by M21** | Without a description and with a single leaf of the same name: 357 in `analytics`, 113 in `consumption`, 198 in `trusted`. Needing text: 94 in `analytics`, 44 in `consumption`; in `trusted`, 815 | It used the single-leaf shortcut that M21 disproves; it bounds nothing |
| M19 | Two channel labels swapped in P01 (`Aplicativo` ↔ `Loja física`) | Still 1,140 rows, R$ 33,076,529.47 and 13,920 units; **761 rows** diverge from the view in a row-level comparison | Counts, sums and hashes prove a package is consistent, not that it is right: the export needs row-level equality with the views (RV2-03) |
| M20 | P13's rounded averages, re-weighted by their counts, against the direct calculation over 313 month × carrier × service groups | 46 groups differ in transit days and 20 in late delay, at the view's four decimals | Those averages cannot be re-aggregated; they stay at the view's native grain (RV2-12) |
| M21 | Lineage leaves of `total_amount`, `sum(…)`, `round(…, 2)`, `… * 100` and `cast(… as numeric(12,2))` | The same single leaf for all five | A single leaf of the same name does not prove that a column only carries a value (RV2-08) |
| M22 | The envelope modelled with WebCrypto and the two public passwords | The Logística password opens P13 and fails on P01; the Diretoria password opens both; its holder can produce ciphertext the site accepts as valid; a flipped bit is rejected | What the encryption demonstrates is access scoped to a key, not authentication or confidentiality (RV2-01) |
| M23 | Authenticated data serialised as JSON, with the same fields in another order | Decryption with the reordered bytes fails | The authenticated data needs one canonical byte serialisation (RV3-01) |
| M24 | The rollback cut: the approved recovery package of 2026-09-25 (cut 12:32:21Z, commit `7b0bea6`) and its second copy, against the warehouse | Both verify — checksums, format, the three dumps listed. Against the databases, 127 differences: the source gained 4,651 stock events (13,700 → 18,351, the producer's accumulated count); three certified legacy captures (49, 52, 55); 9,621 quarantine rows in three slices. Alembic, the warehouse versions and the four SCD snapshots unchanged. 3.0 GB free, with the databases, Airbyte and another project's container up | Restoring the approved package would lose that state (N26); the machine is not yet ready for stage 1.6 |
| M25 | Dependencies on the category names and on the single price range, outside the generator | 0 matches for the 24 category names in tracked code, tests, dbt models, seeds and documents; 0 for the price range and the margin; 24 in the study trail | Only the generator and the trail depend on them — the trail through N7 |
| M26 | A variable given on the command line of `make medir`, against a model of `docker/medir.sh` | `RESET=1` and `FORCE=1` both reach the inner `make` (GNU Make 4.3) | `FORCE=1` never goes through `make medir` |
| M27 | P13's delivered shipments against `trusted.shipments`, by `(source_system, shipment_id)` | Retail 3,166 both sides; legacy 144 in trusted, 132 in the fact; 12 in trusted only, 0 in the fact only. Each of the 12 has no item in trusted and every item in the quarantine of capture 55, `PARENT_REJECTED`. P13: 1,176 rows, unique at its grain; `sum(delivered_count)` 3,298, the fact's distinct delivered shipments | E11 reconciles by key and traces the exclusions (RR-09); whether P13 should count a shipment whose items were all rejected is the Owner's question (runbook O6) |
| M28 | The stock ledger's count and `max(event_sequence)` | 18,351 and 18,351 in the source and in both warehouse paths: no gap today | The runbook compares counts, and the cut only bounds a wait (RR-11) |
| M29 | eng_dados' producer loop with every database, file and sleep replaced and the draw forced to a transfer pair | `LIMITE` 1 emits 2, 3 emits 4, 2,199 emits 2,200, 2,200 emits 2,200 | `LIMITE` is not the count emitted: the runbook records N (RR-11) |
| M30 | The retained legacy memory | 31 captures in `raw_legacy`, 17 of them without a complete certificate; 206 MB in 40 tables; 600 certificate rows in `governance.legacy_captures` | What the memory baseline T4 records before B1 (RR-06) |
| M31 | The provenance of today's `source_db` | No `data/source/geracao.json`: B5's restore set aside the record of its 12:49Z load — seed 20260904, `as_of` 2026-09-01, `dev`, `7b0bea6`, 252,955 rows — and brought back the 12:32Z cut, whose manifest says `source_db: null`. Against that cut, by count, only `inventory_movements` (13,700 → 18,351) and `inventory_balances` (2,911 → 2,919) differ; 252,955 rows then, 257,614 now. Counts, not content | No file records the main source's generation: the runbook's calibration in stage 1.5 is the first test that only the producer changed it, by content, on its subset (runbook P9, O7) |
| M32 | P13's excluded legacy shipments, item by item | 12 shipments, 17 raw items of capture 55, all rejected and in the quarantine, `parent_rejected`; 0 unaccounted; P13's five grain columns unique over 1,176 rows. One synthetic unclassified item gives `unaccounted_items 1` | E1 and E11 account for every item, not one per shipment (RR-20) |
| M33 | `cp -a` of a package directory over an existing one, on a model | The stray file stays; into an absent path it does not | A promotion's recovery copies into an absent path only (RR-19) |
| M34 | P13's reconciliation item by item, and its negative cases on CTE models | Today: 290 items of delivered legacy shipments, each resolved — 205 eligible, each its own trusted and fact item; 85 rejected, each in the quarantine under the current treatment, with its origin and findings —; the 12 excluded shipments explained by rejected items only; every trusted item of a delivered shipment in the fact, both sources. The previous predicate accepts a shipment missing from the fact whole, an accepted sibling hiding a missing item and a stale treatment; the new one flags each | E1 and E11 resolve every item to its own row (RR-23) |
| M35 | Airbyte's job records, against the warehouse | 18 jobs since B5's reinstall, each with `connectionId`, `jobType`, `status` and `startTime`; the legacy connection's 2, 3, 46, 49, 52 and 55, all succeeded; no certificate or raw row for 2, 3 or 46, which B5's restores replaced | An attempt with no job id is reconciled against these records from A8 on (RR-24, runbook O8) |
| M36 | P13's reconciliation counted, not only found; and the state of Airflow | `q14` on today's warehouse gives every value of `q11` (M34), digest included, and both multiplicity counters 0. On CTE models, a classification repeated by `UNION ALL` gives 291 items and 206 eligible with every loss counter 0 — which `q11` accepts — and `nonunique_classification_identities 1`; a raw row repeated, `nonunique_raw_identities 1`. Airflow up, brought up on 2026-10-25 at 20:06Z and back with the databases at 18:11Z; no capture since M30 | E1 and E11 count each item's classification (RR-30); A1 records the state it finds (runbook O9) |
| M37 | P8's host-process check | As written, `ps -eo pid,pgid,args \| grep -E 'mvp_ed1\.streaming\|prism\|beam'` lists its own `grep` and exits 0, so it can never come back empty; `pgrep -af 'mvp_ed1[.](streaming\|airbyte)\|[p]rism\|[b]eam'` lists nothing and exits 1 | P8's check, and the rule of one caller alive at a time before each capture, use the bracketed `pgrep` (runbook P8, §4) |
| M38 | The rejection cascade behind P13's 12 excluded legacy shipments (runbook O6), followed through each `PARENT_REJECTED` finding's parent | 17 shipment items ← 17 order items ← 6 product variants, all `parent_rejected` ← 4 legacy products rejected for their own defects (`own_invalid`: missing time zone, disguised and required nulls, delimiter, ambiguous encoding, truncation). The 12 shipments and their 12 orders are in `trusted`; 8 of those orders have no item there | The shipments' delivery is valid; only their content was rejected, three levels up (N43; D66 in eng_dados) |
| M39 | Description inheritance prototyped on eng_dados' manifest of 2026-10-23 (192 models), in three variants | Root texts to write so that `analytics` and `consumption` reach zero: **307** with N41 taken literally — `source_system` and `is_deleted` among them, the same sentence 20 and 19 times —, **268** with the conventions, **249** with constant branches neutral: 98 in `trusted`, 77 in `analytics`, 72 in `consumption`, 2 in `staging`. P01's summed revenue does not inherit; `sales_channel_name` crosses the union with the bridge, the dimension with its unknown member and the view; an undeclared bridge does not; 15 hand texts sit on carrying columns, 14 of them saying what the inherited one does not — additivity, the role in the model, the constraint a test enforces | N44, N45; stage 1.8 writes text roots, not columns |
| M40 | Stage 1.7 as implemented in eng_dados (`ff868a9`, `1e7de44`, `eeae9d1`) | Materialised columns with no description: `raw` and `raw_legacy` 0 (from 1,161), `staging` 7, `trusted` 232, `snapshots` 23, `analytics` 215 (from 451), `consumption` 123 (from 157), `quarantine` 5, `governance` 0 — the ratchet's ceilings; objects without `domain` or `owner`: `staging` 37, `trusted` 32, `analytics` 25, `consumption` 16, `snapshots` 4, `quarantine` 1. The text reaches the database's column comments on the models only (`staging` 1,107, `trusted` 836, `analytics` 262, `consumption` 65), not on the sources or the snapshots, which `persist_docs` does not cover. Text roots left so that `analytics` and `consumption` reach zero: 250. `make check` green — PASS=905, 699 passed — in **411.44 s against 409.35 s** before, under the same conditions: dbt build +14 s for the comments, the derivations −13 s, one instead of two, pytest +1.3 s with 16 more tests. A first measurement, 734.67 s, ran while a system upgrade restarted containerd and with it Airbyte's node, and is discarded | The ceilings of N42; 1.8's volume; comments on sources and snapshots are open |
| M42 | M7–M9 redone on the in-memory generation (runbook H3; eng_dados `c272104`) | Before the fixes (`9705aaf`), in memory, exactly the warehouse's M7–M9: averages from R$ 1,970.28 to R$ 2,929.85, prices from R$ 63.34 to R$ 6,938.57, 3,130 of 7,500 items sold before launch. With the fixes: 16 leaves, 0 off the declared tree; 0 of 7,500 items outside their leaf's range, averages from R$ 96.02 (Organizadores) to R$ 5,530.82 (Notebooks); 0 sold before launch, with 641 items and 27 products of unknown launch (716 and 30 before). The fixed legacy generation, before its injector: 0, 0 and 0, over 10 leaves and 375 items |
| M43 | Both sources before and after the fixes (runbook H1, H2; `9705aaf` against `27deb9f`) | T2's calibration of today's source against `PRE`'s generation: `oltp` 39 tables equal, `inventory_balances` excluded, the ledger up to `event_sequence` 13,700; `legacy` 40 equal. With the fixes 17 tables change in each source; `oltp` rows 252,955 → 252,987 (`product_categories` 24 → 28, `inventory_movements` 13,700 → 13,725, `inventory_balances` 2,911 → 2,914); the legacy batch `3f9e5088…` → `060c3fc9…`, 108 findings as before, none moving a fact item's date or price; legacy key transitions: `product_categories` +4, `inventory_balances` −2 (`145`, `146`), `inventory_movements` −8 |
| M44 | Stage 1.5's checks on today's data (runbook H4, H5; T3; eng_dados `27deb9f`) | Invariant 14 fails on 3,130 rows of 240 products; P09's reconciliation passes with the new view, R$ 36,719,765.95 on both sides. D5's probes: M3 met; M7, M8 and M9 fail on the v1.0.0 defects — 11 of 12 retail leaves and 7 of 8 legacy ones elsewhere, 4,794 of 7,500 retail and 106 of 231 legacy items out of range, 3,130 retail and 55 legacy, all unexplained, sold before launch. Against a baseline taken in memory: the recovery barrier finds nothing (15 attempts, 31 `sync_id`s; the job listing not exercised), T3 finds nothing, its (1b) matching the 14 certified captures over 560 tables in 61 s and 885 MB; the baseline itself 24 s, 587 KB, 677 MB. The treatment record: capture 55, catalogue 9, 3,207 rejected in 33 tables |
| M45 | Stage 1.6, the regeneration in eng_dados (runbook §4; its diary `data/medicoes/diario_v1_1_0.md`, outside Git; eng_dados `61b9f4a` to `6d93d72`) | The cut packed under `PRE` at 06:30:16Z (`~/mvp_ed1-recovery-pre-v1.1.0`), verified against the databases; the ledger's first epoch: 31 captures, 600 certificate rows, 6 legacy jobs, equal to the cut. Both sources reloaded equal in content to T1, 40 of 40 tables each; 252,987 rows; `inventory_movements` 13,725, `event_sequence` 1 to n. The four zeros at K0 13,725 and at K 15,925 (N 2,200, R 250 all already present). Capture J = 59 certified; `dbt-build RESET=1` PASS=907, invariant 14 green; T3 failed at D4 on three reappearing keys (N56), then contained after `1ae0b11` and `59f1384`. M3: 0 differing groups in P01, P02, P05, P06; M7–M9 all met (16 retail and 9 legacy leaves on the tree, 0 of 7,500 and 0 of 238 items out of range or before launch). P13 identical before and after the producer. `make check` PASS=907 and 885 passed, 3 skipped. The first DAG run failed at `dbt_analytics`: P09's reconciliation test (D67) lacked the `fronteira` tag, ran before its consumption view, and the run left `consumption` empty (the `cascade` of the rebuilt tables) — fixed in `6d93d72`, with a guard on the manifest; its capture 62 was certified and recorded by its gate. The second run: 15 tasks on their first try, capture 64. F6: T3 contained. The candidate (cut 14:21:05Z, commit `6d93d72`, manifest `3b93d594…`) restored through the nine steps in 19 min 51 s — the restore's own epoch opened, capture 67 —, then promoted; its copy in `~/mvp_ed1-recovery-v1.1.0`; both v1.0.0 packages verified outside the checkout. The operating state given back, container by container | Stage 1.6's criterion met. The results go to eng_dados' documents at stage 1.9 (runbook §8) |
| M46 | Stage 1.9, the review of the whole v1.1.0 by Codex (N57; eng_dados `13f1e69` to `4cf41ff`) | Stage 1.9's documents: 3 rounds, 9 findings (6, 2, 1; 4 blocking). Batch 1: 3 rounds, 14 findings (10, 3, 1; 4 blocking), closed in `28044c7`. Batch 2: 7 rounds, 33 findings (7, 5, 7, 4, 3, 6, 1; 2 blocking), closed in `20ea4f3`. Batch 3: 12 rounds, 49 findings (10, 9, 5, 4, 3, 4, 3, 2, 3, 3, 3, 0; 22 blocking), closed in `4cf41ff`. Every finding answered in its round's "Situação". `make check` at `7e12874`, the last code: PASS=907 WARN=0 ERROR=0, 1079 passed, 3 skipped, 0 derived files out of date; `make check-offline` 894 passed at the tip. Codex ran `check-offline`, `secrets-history` and probes on copies, never the full `make check` — that number is the author's (eng_dados' V1) | Stage 1.9's review criterion met; the Owner's acceptance on 2026-11-05 |
| M47 | The cost of the key derivation of stage 2.2a (N67; `evidence/20261105/m47_pbkdf2_latency.mjs`) | PBKDF2-HMAC-SHA-256 deriving an AES-KW key through Node's WebCrypto, five runs each, on an Intel Core i5-7200U with Node v24.18.0: 100,000 iterations median 49.9 ms; **600,000 median 306.4 ms** (294.1 to 328.0); 1,000,000 median 496.6 ms. The browser's figure is not measured | 600,000 stands for now; the ceiling of 2,000,000 the reader accepts costs about a second here. The browser is measured when the reader exists ([envelope §7](docs/encryption_envelope.md#7-where-it-is-implemented)) |
| M48 | The counter-proof of every predicate of the envelope's two readers (envelope §6.5; `evidence/20261106/m48_counter_proof.py`) | 45 predicates in the Python module and 41 in the JavaScript one — the four left out are CI's duplicate keys and the package checks, Python's only —, each taken as true in a copy: **236 dedicated case runs, 0 surviving**; after round 4's cases, **264, 0 surviving**. The ends of the mutants include later refusals, openings and broken parses (`IndexError`, `struct.error`) | Every refusing condition is proved by a case that dies without it, in both languages |
| M49 | The cost of the key derivation in Chrome (N67, N71; `evidence/20261106/m49_browser_latency.mjs`) | Chrome 156, headless, same machine as M47, five runs each: 100,000 median 102.6 ms; **600,000 median 377.7 ms** (367.9 to 406.8); 1,000,000 median 607.9 ms; 2,000,000 median 1,237.2 ms | 600,000 stays: below N67's second. A phone is not measured |
| M50 | How `hosting:clone` names a version (stage 2.2's plan; `evidence/20261106/m50_hosting_clone_source.sh`) | firebase-tools 15.28.2's own code: the source is split on `:` into site and channel, and only when that fails, on `@` into site and version (`sites/{site}/versions/{version}`); its `--help` shows only `<site>:<channel>`. The form `SITE:@VERSION` this plan wrote is read as a channel named `@VERSION` and fails, finding no such channel | §3.4 corrected to `SITE@VERSION`; the pipeline uses it ([`docs/publishing_pipeline.md`](docs/publishing_pipeline.md) §4.4) |
| M51 | The first preview through the pipeline (T1's first run, PR #1, publish run 42175769408; `evidence/20261106/m51_first_preview.out.txt`) | `admit` and `verify` passed; the preview job's federated exchange as `hosting-preview` succeeded and `firebase-tools` deployed channel `pr-1` with it — no key; the channel served version `30f06cd0acd531ca`, expiring in 30 days. The exact check then refused: Hosting adds `__/firebase/init.js` and `__/firebase/init.json` to every version | The check allows exactly those two reserved files, and `verify` refuses any artifact file under `__/` ([pipeline §4.3](docs/publishing_pipeline.md#43-job-preview--environment-preview-credentials)) |
| M52 | The counter-proof of the package gate (stage 2.2b; `evidence/20261106/m52_package_gate_counter_proof.py`) | For each check of [`docs/package_gate.md`](docs/package_gate.md) — the contract's, the totals', the Parquet's, the value inspection's, the live predicates, `bind-live`, `promote`'s predecessor and the record's `live_version` —, a copy of the package with that one check made to pass, and its mutation's tests run against it: **35 mutants, 35 killed**, the unmodified copy passing the same tests | Each check refuses a case only it catches; the log's protection has two layers, and only removing both lets a value through |
| M53 | The billing link of the showcase project, after eng_dados recorded that the end of the account's free trial reaches every project on it (2026-11-13; `evidence/20261113/m53_billing_off.sh`) | `gcloud billing projects describe bi-como-codigo`: billing **off**, no billing account; live answers 200 | The project is on Spark with no billing account (ADR-0002), so the trial's end — resources stopped, then deleted after 30 days — does not reach it; what Google does to a Spark project of a closed trial account is not measured |
| M54 | The versions stage 2.3 pins, on the npm registry (2026-11-13; `evidence/20261113/m54_candidate_versions.sh`) | Evidence 40.1.8 and its components 5.4.2, both last changed on 2026-02-06, on SvelteKit 2.8.4 and ECharts 5.6.0, its browser engine asking DuckDB-WASM `^1.30.0`; DuckDB-WASM's last stable release 1.32.0, of 2025-12-16, while `latest` points to `1.33.1-dev57.0`; Vega 6.4.0, Vega-Lite 6.5.0, vega-embed 7.3.0 | The pins of [`docs/framework_prototype.md`](docs/framework_prototype.md) §2.4, §3 and §4; Evidence without a release for nine months is a measure of upkeep (§6 there) |
| M55 | The 16 views at eng_dados `v2.1.0`, through the exporter's own login (2026-11-17; `evidence/20261117/capture.sh`) | One `REPEATABLE READ READ ONLY` transaction as `consumption_reader`: 16 views; `governance.warehouse_provenance` **`verified`**, built by `04d4af3f-…` from `4137dc7` on 2026-11-17 at 04:50Z — the commit whose models and data `eb11709` carries; one row count and one fingerprint per view, from 25 rows (P03) to 6,626 (P11). Read twice, three minutes apart: the same 16 fingerprints, and the same provenance row after them. The rows stay on this machine, outside Git | The state stage 2.4 exports while the provenance still says this row; the baseline the next pin is compared with, by fingerprint — the view contract sees schema, not values (§3.5.1) |
| M56 | M55 against what survives of the old pin `4da9e60` (2026-11-17; `evidence/20261117/compare.py`, `views_sql_diff.sh`) | This repository never captured the views at `4da9e60`, and the warehouse no longer holds that state. Four views have "before" rows, measured by `mvp_eng_dados_2` on 2026-11-14: by the package's grain, almost every row changed — P13 1,180 → 1,177 rows, 969 of the 970 keys in common with a changed value, delivered shipments 3,313 → 3,374; P04 560 → 534 rows, first purchases 1,389 → 1,283; P14 1,867 → 1,858 rows, orders 2,774 → 2,791; P15 117 → 108 rows, tickets 402 → 405, and F1's case (Jan/2024, Aplicativo, Conta) has no row now. P11: 6,990 → 6,626 rows, undefined turnover 1,216 → 3, median turnover 0.02 per quarter (V5). Each view has the set of columns the package declares; between `4da9e60` and `eb11709` no view's SQL changed, only `consumption`'s YAML | The data was regenerated, not corrected at the margin: no number read before carries over, and each report's oracle is redone on this state (2.5, 2.11). The other twelve views have no before → after (§7) |
| M57 | The metadata package at `eb11709` against `19c0e80` (2026-11-17; `evidence/20261117/package_check.py`) | Format 1 → 1; `metrics`, `filters` and `view_rules` added; `on_zero_denominator` `returns_null` on 7 of 44 metrics, the old `zero_denominator` kept; `open_items` D43, D63, D64, V1–V3, V5–V7, V4 closed, `objects` null in all; `provenance.warehouse` `verified` from `4137dc7`, as M55 read it; `gateway_response_code` with its seven meanings; 16 `view_audits` `audited` at `0471f6a`, and the 32 reference checks of the audit `pass` in the run of 2026-11-17 04:51Z, on the regenerated data | What the notice of 2026-11-17 says, confirmed; 2.7 reads `on_zero_denominator`; the audit that opens each report cites `view_audits` and that run (§3.2) |
| M58 | What P08's cost of November 2026 is made of (2026-11-17; `evidence/20261117/q_p08_november.sql`) | P08's November 2026 has R$ 6,604,745.09 of cost and no revenue — sale outflows run at R$ 52–189 thousand a month from June to September. All of it is 984 retail movements of type `sale`, 17,555 units, `movement_date` 2026-11-16, occurred on 2026-11-17 between 02:42Z and 02:57Z and recorded by 02:57:55Z, with no order behind any of them; the last realised order is of 2026-09-01. The time is step E4 of `mvp_eng_dados_2`'s cycle, its streaming exercise (`stream-produce LIMITE=2200`), which the batch path then synced into the warehouse. The same units are P11's 2026-T4 outflow, 17,555 against about 1,000 a quarter | P08 and P11 would publish a loss and a turnover no operation had; asked as UQ-16 ([`docs/upstream_questions.md`](docs/upstream_questions.md)). Neither is in the first publication: P01 and P13 read no stock movement |
| M59 | The 16 views at eng_dados `v2.3.0` against M55 (2026-11-19; `evidence/20261119/compare.py`, the capture by `evidence/20261117/capture.sh`) | One `REPEATABLE READ READ ONLY` transaction as `consumption_reader`, read twice, at 22:44Z and 22:46Z, with the same fingerprints and provenance row: `verified`, built by `1cb3cd4e-…` from `bcc2d5c` at 17:07Z. Against M55, **13 views identical** by fingerprint; P08 542 → 526 rows, P11 6,626 → 5,775, P12 571 → 213; every view's columns and types the same. P08 sums to the R$ 10,634,340.76 net revenue, R$ 5,030,135.71 of COGS and R$ 5,604,205.05 of gross profit that its Consumidores §5 publishes, its last month 2026-09; P11's median quarterly turnover is 0.46, p90 1.28, one undefined, its last quarter 2026-T3; P12's 213 rows all have reorder point 1 and zero available, all `is_stockout` | What the notices of 2026-11-18 and 2026-11-19 announced, confirmed by an oracle of this repository; M59 replaces M55 as the baseline. With this data, P12's "below the reorder point" is "out of stock among the pairs that sold in the year" (§7) |
| M60 | The metadata package at `2bceb47` against `eb11709` (2026-11-19; `evidence/20261119/package_check.py`) | Format 1 → 1, no top-level key added; 281 → 283 relations, `analytics.dim_sku_location` and `trusted.f31_legacy_sale_exceptions` added; `relations.*.primary_key` and `foreign_keys` added — 27 keys and 60 foreign keys in `analytics` —; no view's columns changed; 16 `view_audits` `audited` at `0471f6a`, their 26 checks `pass` on 2026-11-19 17:52Z and P13's one dbt test in `data_tests`; `open_items` D43, V1–V3, V5–V7, all `deferred`, D63 and D64 gone; `provenance.warehouse` `verified` from `bcc2d5c` | The notices confirmed, but for three things asked as UQ-21 to UQ-23: P12's audit still names `0471f6a`, though its definition changed at `edf564a`; V5 is still open although announced fixed; the second relation added is in neither notice |
| M61 | `b0ef66e` against `2bceb47`, the package and the source (2026-11-20; `evidence/20261120/package_diff.py`, `source_diff.sh`) | `b0ef66e` on its `origin/main`; 8 files changed, none under `dbt/` — the package's generator, its spec, Pendências, Consumidores §5 and the audit's tests. In the package, outside `checks`, only `provenance.inputs_sha256`, `open_items` — D43, V1–V3, V5–V7 → D43, V1–V3 — and `view_audits`: the `commit` of P02 and P03 `0471f6a` → `504271a`, of P12 → `edf564a`, of P15 → `4da9e60`, and P12's `findings` [] → [F36]. In `checks`, a new run of 2026-11-20 02:20Z, one check added (UQ-21's), no status changed: 1,871 `pass` and 19 `skipped` | The answer confirmed, but for the new run of `checks`, which it does not name and which changes nothing here; the views M59 read stand for `b0ef66e` |
| M62 | How the package gate's value inspection meets a report page's own code (2026-11-25; `evidence/20261125/collision_surface.py`) | The gate's needles, its functions unchanged, from M59's capture of the 16 views: 57,506, and 186 of the 900 three-digit integers are a value in some view. Searched by substring, as `verify` searches, in Candidate B's artifact of 2.3's last full run: **8 of its 9 code files hold a value, 21 hits**; most inside integrity hashes, longer numbers or identifiers, **6 standing as tokens** — a constant of the envelope's reader, a channel type that is also a word of `cache: "no-store"`, a CSS value, a number of the declaration, an amount in a comment, another five-letter text. `site/releases.md` holds the year, N108's first case; no value is printed | The real page as 2.3 built it would be refused by `verify`: 2.3's five-digit fixture (N94) never met it. Shapes [`docs/report_page.md`](docs/report_page.md) §2 and N116 |
| M63 | How the Vega-Lite the page pins draws a null (2026-11-25; `evidence/20261125/vega_invalid.html`) | Vega 6.4.0 and Vega-Lite 6.5.0, invented points: with a null row, the default mode, `break-paths-filter-domains`, `break-paths-show-domains` and `break-paths-show-path-domains` break the line there; a month whose values are all null stays on the x axis in the default and both `show` modes; `filter` draws across the null and drops that month | 2.3's two chart defects came from rows that were absent, not null: the grid of months by categories, with nulls, fixes both; the declaration names its mode ([`docs/report_page.md`](docs/report_page.md) §3.2, §8) |
| M41 | Stage 1.8 as implemented in eng_dados (`d4c2885`..`33d6451`) | Materialised columns with no description: `analytics` **0** and `consumption` **0**; `trusted` 125, `snapshots` 6, `staging` 5, `quarantine` 5, `raw`, `raw_legacy` and `governance` 0. Objects without `domain` or `owner`: 0 in every layer. 247 written text roots and 45 written domains; 39 primary-key texts; 86 of the snapshots' 109 columns commented in the database. Writing the text found D67: P09's `captured_amount` is zero in all 538 rows, the view reading authorisation transactions only (R$ 36.7 M captured in the fact) | The criterion of 1.8 met; D67 is the Owner's |

**Read from official sources on 2026-10-22 and 2026-10-23 — not measured:**

| Source | What it says |
|---|---|
| [Firebase](https://firebase.google.com/pricing), Spark plan | Hosting: 10 GB of storage and 360 MB/day of transfer; on Blaze, US$ 0.026/GB and US$ 0.15/GB beyond that. What happens when Spark runs over the quota, the page does not say |
| [Firebase Hosting, managing versions](https://firebase.google.com/docs/hosting/manage-hosting-resources) | `firebase hosting:clone SITE:CHANNEL SITE:live` deploys a version to another channel; within the same site, the release points to the exact same version |
| [Firebase CLI](https://firebase.google.com/docs/cli) | Recommends Application Default Credentials for CI and no longer recommends tokens. That it accepts a federated credential from GitHub is described only by community guides |
| [Firestore](https://firebase.google.com/docs/firestore/quotas), free quota | 1 GiB stored; 50 thousand reads, 20 thousand writes and 20 thousand deletes a day; 10 GiB/month of egress; documents up to 1 MiB |
| [Cloud Storage for Firebase](https://firebase.google.com/docs/storage/faqs-storage-changes-announced-sept-2024) | Requires the Blaze plan, including the default bucket; on Spark, calls answer 402 or 403 |
| [Firebase Authentication](https://firebase.google.com/docs/auth/flutter/manage-users) | A signed-in user can change their own password and delete their own account through the client SDK; those actions require a recent sign-in |
| [Neon](https://neon.com/pricing), Free plan | 1 GB per project; 100 CU-hours; suspends after 5 idle minutes; 5 GB/month of public transfer — once exceeded, compute stays suspended until the next period |
| [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) | Published site up to 1 GB; 100 GB/month of bandwidth, a soft limit |
| GitHub API | Evidence: release of 2026-02-06 and last push on 2026-10-22, MIT. Observable Framework: release of 2026-03-02 and last push on 2026-05-15, ISC. DuckDB-WASM: last push on 2026-10-22, MIT |

**Not measured:** site build time; how any framework behaves with this data; DuckDB and WebCrypto
inside the claude.ai Artifact; the time to derive the keys in the browser; usability; the effect of
the fixes on the tests of eng_dados.

---

## 3. What gets built

### 3.1 The two pieces of content

| | **Showcase — `bi-como-codigo`** | **Study — `caderno-de-dados`** |
|---|---|---|
| For whom | Whoever evaluates your work, in minutes, without you there | You |
| Tone | A self-sufficient executive presentation | Exploration, lab, questions |
| Content | Overview; reports for the 16 questions, with per-profile access; reading portal of the data governance; governance of the project | Lessons from the view to the source; study of the governance; SQL explorations; link to the study trail |
| Data | Parquet of the 16 views, encrypted per report on your machine before it enters Git; public governance metadata, generated from eng_dados | The showcase reports, read by URL and opened with the password of Diretoria; its own capture for the lessons |
| Where | Firebase Hosting, in a project of its own (N2) | A private claude.ai Artifact or a `*.web.app`, by the probe of stage 3.1 (N18) |

### 3.2 The showcase

**Principles.** Every page explains itself, with no presenter and no jargon that does not lead to
the glossary. Every number comes from a record of eng_dados at a pinned commit, with its date —
none is typed (P5). Narrative first, reference after: whoever has two minutes reads the story;
whoever has twenty goes down into the catalogue. Navigation by tabs and links, always with a way
back; search in the catalogue; accessibility and narrow screens.

- **Overview.** The project on one page: what it is, the architecture in one picture, the numbers
  that prove its robustness and three doors — reports, data governance, how it was done.
- **Reports — BI as code.** The 16 questions, each a reviewable text file with the query and the
  presentation; filters, cross-filtering, charts and table in the browser. P01 first. Rules set by
  the reviews: partial month flagged (M5); a slice with no sale said as such (M6); `order_count`
  never added up across categories (M4); ratios re-aggregated only through numerator and
  denominator; an average published without its sufficient statistics stays at the view's native
  grain — P13's transit and late-delay averages among them (M20); no filter the view does not
  offer; no metric redefined in the report. Each report starts with an audit of its view for
  non-additivity, balances that depend on time and truncated populations.
- **Per-profile access (O7, N23).** Hiding a report in JavaScript is not access control: the file
  could still be downloaded by URL, and an evaluator sees that in the network tab. And an account in
  Firebase Authentication does not make the password immutable: a signed-in visitor can change it
  or delete the account (§2). Hence **the password becomes the key**. Because both passwords are
  public (N22), what this demonstrates is **access scoped to the key supplied**: each password opens
  exactly its profile's reports and no other. It is not the authentication of a person, and it is
  not confidentiality from the public — whoever reads the Diretoria password on the login screen
  can open every report, with or without the site (M22):
  - two profiles, declared once in the code: **Diretoria**, which opens the 16 reports, and
    **Logística**, which opens only **P13** — on-time delivery by carrier. Whoever handles carriers
    needs no revenue, margin or payment data;
  - encryption happens **on your machine, at export**, before anything enters Git: the public
    repository only ever receives ciphertext and a manifest with no clear figure. The envelope is
    specified in §3.6;
  - in the browser, WebCrypto derives the key from the password, unwraps the keys the profile is
    entitled to and decrypts only those reports. A wrong password opens nothing. Switching profile
    or logging out clears the decrypted tables, buffers and caches: no Diretoria data stays visible
    after switching to Logística;
  - the password is truly immutable: there is no account to change or delete, and it only changes in
    a new publication, through a PR of yours. A later change does not revoke ciphertext already
    downloaded with the former password;
  - the login screen has, **above** the box, an explanation of what the page and the product are
    and, **below** it, the credentials (N22), generated from the same declaration of the profiles:

    ```text
    Para acessar, use:
    Login: Diretoria
    Senha: senha_complexa_123
    ou
    Login: Logística
    Senha: complexa_senha_321
    ```

  - the overview, the portal and the governance of the project stay open, with no login;
  - the proof is by execution, like `test_acesso` in eng_dados: the whole profile × report matrix
    through actual unwrap and decrypt calls, at build and in the browser against the preview, plus
    the negative cases of §3.6. In the showcase, Logística is invited to open another report and sees
    that its key does not open it.
- **Reading portal of the data governance.** Generated from the declarations of eng_dados — through
  its metadata package, and its documents, ADRs and glossary by commit (§3.5, N87) —, with the
  narrative curated into chapters:

  | Chapter | What it answers |
  |---|---|
  | 1. Start here | What database this is, the two sources, the nine layers in one picture, where to go next |
  | 2. The map | Each layer: why it exists, who writes, who reads, how long it keeps data, how many objects |
  | 3. The catalogue | Each object and column: description, domain, owner, grain, type, classification, the tests that guard it, incoming and outgoing lineage, the questions that use it |
  | 4. The business questions | Question → view → measures and additivity → fact and dimensions → report |
  | 5. The vocabulary | Business and technical glossary |
  | 6. Who sees what | Classification by layer, roles × layers in the warehouse, the proof by execution, classifying is not exposing — and the same least privilege applied in the showcase itself |
  | 7. Where each number comes from | Column lineage down to the source, with the crossings outside dbt — one hop at a time, never the whole graph |
  | 8. Why trust it | Tests by layer, reconciliation at every boundary, invariants, quarantine with a reason, capture certification |
  | 9. How this is maintained | Catalogue as code: everything here is generated from the declarations, and `make check` keeps them from diverging |

  From chapter 1, a short route — question → report → column — lets a newcomer reach an answer
  without walking through the catalogue first. Missing metadata is labelled as missing, never filled
  in. Tests appear in three distinct states: declared, executed successfully on a stated date, and
  open issues today — a past review with no finding left does not mean D62 to D64 are solved.
- **Governance of the project.** Principles P1–P10; the decisions as ADRs, on a timeline and
  searchable; the review by a second agent, round by round, until no finding was left; the
  definition of done; the documentation map with one owner per subject; risks and their
  treatments; milestones; the from-scratch cycle as measured and the recovery point. Generated from
  the documents and the history of eng_dados.

### 3.3 The study content

- **Lessons, starting with P01.** An item chosen by a declared criterion — retail, realised, with a
  discount, quantity above one and visible rounding —, captured in a single snapshot: `raw`,
  `staging`, `trusted`, `analytics` and `consumption` all live in `warehouse_db`, and one
  `REPEATABLE READ READ ONLY` transaction gives the same picture across all of them. The lesson
  starts at `raw`. The three questions of
  [`REVIEW.md` §3.2](REVIEW.md#32-a-didactic-path-with-progressive-disclosure) organise the path, with
  the item's value, the other items and the group total.
- **Study of the governance (O4).** For each mechanism of eng_dados: how it is built, what value it
  has — with the real incident it caught or prevents —, how to use it and what it does not cover,
  with labs actually executed. Three incidents already checked by reading: the grant given by hand
  to `analyst` on `trusted`, revoked on the next run
  ([Governance §7](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#7-regras-de-acesso-por-camada));
  P11, which passed `dbt build` and failed on its first read (`tests/test_consumo.py`); the `unique`
  of `dim_customer`, broken on the first load with the legacy source
  (`dbt/tests/legado_nao_colide_com_a_origem_principal.sql`).
- **Explorations.** Free SQL, with DuckDB in the browser, over the showcase reports opened with the
  password of Diretoria; and the next candidate lessons — composite identity (M10) and one rejection
  all the way to quarantine.
- **The study trail** stays in eng_dados, as it is; the study content points to it.

### 3.4 The architecture

> The hosting is decided in [ADR-0002](docs/adr/0002-host-on-firebase-hosting-through-identity-federation.md) and the trusted
> workflow in [ADR-0003](docs/adr/0003-publish-through-a-trusted-workflow-on-main.md) (2026-11-06); the pipeline as built is owned by
> [`docs/publishing_pipeline.md`](docs/publishing_pipeline.md).

```text
1. Export, on your machine — eng_dados databases up, the read-only login of N4:
   one consistent read of the 16 views → contract, grain, nulls and decimals checked
   → typed rows equal to the views after the Parquet round trip → encryption per report
   → package with oracle results, and a public manifest with no clear figure
2. PR in bi-como-codigo — branches of this repository only:
   CI checks the package, decrypts the whole matrix with the public passwords, builds a fresh
   deploy directory from an explicit inclusion list, inspects the finished output
   and deploys it to a preview channel
3. Merge, behind a protected environment:
   the approved preview version is cloned to live — the same bytes, no rebuild
4. Browser: password → key → only that profile's reports, opened by DuckDB-WASM (engine from jsDelivr)

study (GitHub) ── lessons and its own capture ──▶ Artifact or *.web.app ◀── URL + password of Diretoria
```

- The exporters run only on your machine: the warehouse is never reachable from the internet, and
  CI never reads it.
- **Three gates, each where it can actually be checked** (RV2-03 to RV2-05):
  - **source to package**, local, by the exporter: a single read-only `REPEATABLE READ`
    transaction; the explicit inventory of the 16 views; the accepted schema and version of each
    view, pinned in this repository — not whichever dbt manifest comes along; grain and uniqueness;
    nulls, decimal precision and scale, dates and time zones, including empty and all-null cases;
    and typed rows compared after writing and reading back the Parquet. The oracle results travel
    with the package. The exporter stays a consumption reader: oracles over the inner layers, like
    M2, belong to the custodian (§3.5);
  - **package to artifact**, in CI, before any upload — previews included: the package against its
    manifest, the whole decryption matrix with the public passwords, a fresh deploy directory built
    only from an explicit inclusion list, and the finished output inspected for clear report data
    and unwrapped keys — in HTML, JSON, JavaScript, caches and source maps, by content and not by
    file extension;
  - **artifact to live**: approval records the candidate revision, the package and artifact
    digests and the Hosting **version ID** of the preview. The merge promotes exactly that version
    with `firebase hosting:clone SITE_ID@VERSION_ID SITE_ID:live` — the CLI's form for a version, `<site>@<version>` (M50) —, which within the same site
    points live at the same version — never with the channel-name form, which takes whatever the
    channel deployed last (RV3-03). Promotions run one at a time, and each first rejects a
    superseded candidate, so neither a preview advanced after approval nor a rerun of an older job
    can replace the current release. A changed candidate needs a new preview and a new approval.
- **Mutation tests prove the gates**: swapped row labels (M19), missing and extra views, changed
  types, duplicated rows, injected clear data, a tampered manifest and a reused key/IV pair.
- **A trusted workflow** (RV2-05, RV3-02). A branch of this repository does not make a PR's code
  trustworthy: a PR can change the checker, the build or `firebase.json`. So the work splits in two:
  - the **candidate workflow** (`pull_request`) builds and checks the candidate with no deploy
    credentials and uploads the result as an artifact. Its `permissions` are part of the PR's own
    code, so a same-repository PR can obtain a GitHub OIDC token; what holds is that it obtains
    **no credential Google accepts**, since the federation trusts only the publishing workflows on
    `main` (N74, proved by a test of 2.2);
  - the **publishing workflow** (`workflow_run`) runs only what is on `main` — its checker,
    inclusion list and Hosting configuration, changed only through a separately reviewed PR —,
    downloads the candidate as data, never executes its scripts or hooks, revalidates the exact
    artifact against every gate and only then deploys, to a preview or, after approval, to live;
  - federation (N15) trusts only that workflow file at `refs/heads/main`, in this repository and
    its protected environment: the GitHub OIDC token carries `workflow_ref`, `ref` and
    `environment` for that binding (RV4-01). The publishing workflow is called directly, not as a
    reusable workflow, so the binding uses `workflow_ref`; `job_workflow_ref` identifies a called
    reusable workflow, which this design does not have. Firebase's default GitHub setup stores a service-account key,
    contrary to N15: stage 2.2 proves the Firebase CLI with Application Default Credentials obtained
    from the federation instead;
  - code from forks never runs with deploy credentials, and a same-repository PR that changes the
    checker or the configuration gets neither a preview nor a live update — one of the rejection
    tests of 2.2.
- **Versions are bound**: content-hashed names for the application, the manifest, the wrapped keys
  and the ciphertext, so that a page left open never fetches incompatible new files at reused URLs.
- **Updating means opening a PR** with the new package: the preview shows the result, the diff of
  the manifest shows what changed, and the merge publishes.
- **The public manifest carries no clear figure**: the control totals travel encrypted with each
  report, and CI checks them after decrypting with the public passwords. This applies to the report
  packages and their control totals; the governance metadata is public by design, and the evidence
  already in Git stays as recorded.

### 3.5 The contract with eng_dados

Every crossing between the repositories is explicit and versioned.

| What is used | How | Why |
|---|---|---|
| The 16 views | Read by a login that is a member of `analyst` (N4), tested through an actual non-superuser connection: it reads `consumption`, is refused elsewhere, cannot write and cannot escalate its role | The database itself guarantees the exporter only reads consumption |
| The contract of the views | The accepted schema and version of each view, pinned in this repository and checked at every export; a change upstream fails the export until it is accepted here | A contract change in eng_dados fails loudly instead of becoming a wrong number |
| Oracles over the inner layers | Run by the custodian, separately, never with the exporter's login | The exporter stays a consumption reader |
| The dimensional model | Out for now (N16); if a report asks for detail, through a consumption contract, with an ADR in eng_dados | [Governance §7](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#7-regras-de-acesso-por-camada) and [ADR-0008](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/adr/0008-schemas-do-armazem.md) do not let a consumer read `analytics`, and [ADR-0018](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/adr/0018-fatos-e-views-a-partir-de-perguntas-de-negocio.md) rejected "one view per fact" |
| Governance metadata | **The metadata package** of `mvp_eng_dados_2` (its D91; `docs/pacote_de_metadados.json`, format 1) at the pinned commit, for what it covers — relations with descriptions, sensitivity and `meta`, lineage, crossings, questions, description gaps, the tests with their results, the view audits, the environments' sources (N87) —; documents, ADRs and the glossary's text are still read by commit. No access to the data. Pinned at `b0ef66e` (N91): format 1, with the fields UQ-12 to UQ-15 asked — `grants_select`, `checks`, `grain`, `open_items` — and those added since — `metrics`, whose `on_zero_denominator` is read instead of the outgoing `zero_denominator`, `filters` and `view_rules`, which carries each view's grain and, with the role `identity`, its key (UQ-18) (M57), the keys and foreign keys of `analytics` and the ids of each view audit's checks (UQ-19) (M60), and each audit's `commit` as the commit of the definition it checked (UQ-21) (M61); what it still lacks is asked as a new field ([`docs/upstream_questions.md`](docs/upstream_questions.md)) | The portal is derived, not written; what changes in eng_dados changes in the portal at the next export; one contract for both portals, so the part they share cannot diverge (N87) |
| Column lineage | The package's `lineage`: the output of `python -m mvp_ed1.models.lineage --json`, format 1 (stage 1.3), carried unchanged, not the command — no project command runs in that checkout (UQ-10). A path that ends at `generated` — a column computed from no column's value, as eng_dados' Data Dictionary §3 defines it, such as a count — is a complete lineage, not a broken one: the exporter accepts it and the portal shows it as generated (RVL2-06 of eng_dados' v1.1.0 review) | No second declaration of the lineage, and no dependency on internal code |
| SQL excerpts and documents | A text anchor per file, read with `git show <commit>:<path>` at a pinned commit; a GitHub link at that commit | An excerpt that disappeared breaks the build; links do not rot |
| Capture for the lessons | By the custodian: superuser, read-only `REPEATABLE READ` transaction, an explicit and rare command | It is the study-reading pattern eng_dados already uses (`make pgcli-*`); no new role |
| Version | eng_dados commit, `generated_at` of the dbt manifest, time of the read, and the warehouse's own provenance | Since 2026-11-15 the warehouse says which commit built it: `governance.warehouse_provenance` (its ADR 0054, in `mvp_eng_dados_2`), the one relation of `governance` the exporter's login reads, in the same transaction as the views — `verified` only after a full clean build; on 2026-11-19, `verified` from `bcc2d5c`, whose models and data `2bceb47` and `b0ef66e` carry (M59, M61). The export records that row; how it checks that the building commit and the pin carry the same models is stage 2.4's. The package's `provenance.warehouse` describes where the package was generated, not the warehouse being read. Its Consumidores §5 still logs every build that changes what a consumer reads, and 2.4 exports inside a read window the Owner opens (UQ-04, UQ-05) |

**The pin.** Stages 2.4 onwards read `mvp_eng_dados_2` at **`b0ef66e`** (N91) — the views and the
metadata package alike —, the commit its answer to UQ-21 to UQ-23 says to pin, three commits after
`2bceb47`, tag `v2.3.0` (N90), with the same models and data; `v2.3.0` had replaced `eb11709`, tag
`v2.1.0` (N89), which had replaced `4da9e60`, the row "Fim da auditoria das 16 views" N85 named. A
later pin comes only with a commit that source announces to pin — a tag in its §6, or a notice —;
when its models or data change, it is captured as M59 was and compared with it by fingerprint
before it is accepted here, and when they do not (M61), the package is checked and M59 stands.

#### 3.5.1 The source moved to `mvp_eng_dados_2` (2026-11-13)

On 2026-11-13 the Owner archived mvp_eng_dados_1 at `v2.0.0` (`f86b9fb`) and continued eng_dados in
`mvp_eng_dados_2`, created from it with no history; its consumers — this showcase among them — read
from there by a pinned commit (D92 in its `docs/pendencias.md`, recorded at `040a796`, not yet on
GitHub when this was written). The facts below are what its notice to this repository states; none
is measured here. The notice is `data/medicoes/base_consumidores/avisos/aviso_bi_como_codigo.md` of
that checkout, outside its Git, read on 2026-11-13; this repository only reads that checkout, as it
reads mvp_eng_dados_1.

- **Three things that do not move together.** The **warehouse** is the same: `mvp_eng_dados_2`
  inherited the containers, volumes and ports, so `evidence/20261022/ro.sh` and the
  `consumption_reader` login reach the same `mvp_ed1_warehouse_db` whatever checkout
  `ENG_DADOS_DIR` names, and a rebuild there changes the next read here. The **new artefacts** —
  SQL, YAML, glossary, `lineage --json`, the metadata package — exist only in `mvp_eng_dados_2`. The
  **historical references** of this repository — the commits pinned in this plan, in `REVIEW.md`
  and in `evidence/` — exist only in mvp_eng_dados_1.
- **Values change, the schema does not.** It announces corrections to views this showcase reads:
  `support_tickets_per_hundred_orders` (its F1 — January 2024, Conta, Aplicativo, 4.5455 → 4.3478),
  `inventory_turnover_by_sku_and_warehouse` (its F2, the period's average stock instead of the
  current balance), perhaps `on_time_delivery_rate_by_carrier` — P13, by its D66: 16 delivered
  legacy shipments left out —, and whatever its audit of the 16 views finds. The view contract of
  §3.4 checks schema and version, not values, so **no gate here would notice**: an export from
  stage 2.4 on would read corrected values while declaring `f86b9fb`. Stage 2.3 reads invented data
  only and is not affected. 2.4–2.10 pin a commit of `mvp_eng_dados_2` after that audit (N85).
- **What it announces for this showcase**, none delivered on 2026-11-13; on 2026-11-14 the package's
  format was specified, at `32397cc`:

  | It offers | Where it serves here | What it does not do |
  |---|---|---|
  | An audit of the 16 views by the three criteria of stage 2.11 — non-additivity, time-dependent balances, truncated populations —, each view against an independent computation written from the glossary, with counter-proofs on known defects | The per-report audit that opens each report (§3.2), in 2.5, 2.6 and 2.11 | It does not close 2.11: equality with the views, the re-aggregations, the presentation and the access matrix stay here; the exporter's login does not change |
  | The result of the tests per object in its metadata package: state, date and run, with "no result" explicit | The three states of tests of the portal (§3.2), in 2.7 | — |
  | The warehouse's provenance — the commit that built it | The Version row above, today "not verified" | Until it arrives, the row stays as it is |
  | Text: the glossary with the rule of the realised order, the rules that today live only in `consumption`'s SQL, corrected descriptions and the grain of the dimensions | The portal (2.7) and the report texts (2.5, 2.11) | — |
  | One contract — its metadata package (its D91) — for any reading portal of the governance | The Governance metadata row above | Stage 2.7 reads it (N87); format 1 is specified at `32397cc` and generated at its Bloco 4 (Q13 there) |

- **What this repository asks of it** — the pinned commit, the dates, the warehouse window, schema
  changes, the channel for value changes, the package's content — is in
  [`docs/upstream_questions.md`](docs/upstream_questions.md), which also keeps the answers: UQ-01 to
  UQ-11 answered on 2026-11-14 at `32397cc`, UQ-12 to UQ-15 the same day at `8742a59`.
- **2026-11-17: `v2.1.0`, the phase closed.** `mvp_eng_dados_2` closed its consumer-base phase with
  the tag `v2.1.0` (`eb11709`, on its `origin/main`). Its notice of that day —
  `aviso_bi_como_codigo_20261117.md` in the same folder, read on 2026-11-17 with the two before it,
  of 2026-11-14 and 2026-11-15, which had not been transcribed here — says what follows; M55 to M57
  measured it. Both sources were regenerated on 2026-11-17 with its corrected generator, so every
  one of the 16 views reads new data and none changed schema (M56); the warehouse says which commit
  built it, `verified` from `4137dc7` (M55); the package gained `on_zero_denominator`, the gateway
  code's meanings and an updated `open_items` (M57). What changed, view by view, is its Consumidores
  §5 at that commit. The pin of 2.4–2.10 and of the package moves to `eb11709` (N89). The phase is
  closed and eng_dados plans no further work: the batch DAG paused, Airbyte and streaming stopped,
  the databases up. Its open items do not change what is read here, except V5 — P11's very low
  stock turnover, median 0.02 per quarter (M56) —, which waits for a later regeneration and a new
  pin (§7).
  Its notice asks that `ENG_DADOS_DIR` name a checkout of `mvp_eng_dados_2`: so it does for the
  reads of M55 to M57, while the gate's `ENG_DADOS_DIR` keeps naming mvp_eng_dados_1, for the
  historical links, until N86 adds the second variable. What the capture found that only
  `mvp_eng_dados_2` can correct — the streaming exercise in P08 and P11 (M58) above all — is asked as
  UQ-16 to UQ-20 of [`docs/upstream_questions.md`](docs/upstream_questions.md).
- **2026-11-18 and 2026-11-19: `v2.2.0` and `v2.3.0`.** `mvp_eng_dados_2` reopened its base and closed
  it with the tag `v2.2.0` (`f5a5173`), then closed a phase on the reorder point with `v2.3.0`
  (`2bceb47`), both on its `origin/main`. Its notices — `aviso_bi_como_codigo_20261117b.md`,
  `_20261118.md` and `_20261119.md` in the same folder, read on 2026-11-19; the first, planned
  answers that the other two replace — say what follows; M59 and M60 measured it. The data was
  regenerated with the streaming exercise out of the published state and purchases sized by demand,
  which answers UQ-16 and corrects P08 and P11; P12 reads each pair's reorder point, from 365 days
  of sales, in the new `analytics.dim_sku_location` (its ADR 0057); the package gained keys, foreign
  keys and the ids of each audit's checks, and a file beside it, `docs/amostras_de_registros.json`,
  with up to five masked rows per relation (its ADR 0058, asked by `gdados`), which this repository
  does not read. The pin moves to `2bceb47` (N90). Its streaming alert now uses the same per-pair
  point on the physical balance, while P12 compares the available one: the two are not presented as
  equivalent. Live delivery and the alert's transitions are still proven only on the discarded base;
  the views read here come from the batch path. UQ-16 to UQ-20 are answered, and what M60 found is
  asked as UQ-21 to UQ-23 of [`docs/upstream_questions.md`](docs/upstream_questions.md).
- **2026-11-19: UQ-21 to UQ-23 answered, at `b0ef66e`.** Its answer —
  `resposta_bi_como_codigo_20261119.md` in the same folder, read on 2026-11-20 — came in three
  commits on top of `v2.3.0`, no tag, no warehouse build: each view audit names the commit of the
  definition it checked (four had been stale, P12's among them), V5 to V7 are closed, and the seed
  `trusted.f31_legacy_sale_exceptions` has its row in Consumidores §5 (M61). The pin moves to
  `b0ef66e` (N91). It also asks this repository for a cross-project mailbox, an `alinhamento.md` at
  the root, outside Git, that the `CLAUDE.md` loads at the start of each session, as in
  `mvp_eng_dados_2` and `gdados`. Created on 2026-11-20 as asked, by the Owner's N92. The same
  answer names `2ea212b`, two commits later, which only adds its V8 to `open_items`: the pin stays at
  `b0ef66e` (N93).

### 3.6 The encryption envelope — a proposal to review before stage 2.3

> Decided in [ADR-0001](docs/adr/0001-encrypt-each-report-under-the-profile-password.md) (2026-11-06);
> the format, frozen, is owned by [`docs/encryption_envelope.md`](docs/encryption_envelope.md). What follows is the proposal
> as reviewed before stage 2.2a.

Standard WebCrypto primitives only (PBKDF2, AES-KW and AES-GCM, all in the
[Web Cryptography API](https://www.w3.org/TR/2017/REC-WebCryptoAPI-20170126/)), in a versioned
envelope that fixes every parameter instead of relying on library defaults (RV2-02). **Proposed
parameters**, to be reviewed by Codex together with the reference implementation of stage 2.2a:

| Element | Proposal |
|---|---|
| Password | The UTF-8 bytes of the password exactly as declared |
| Key derivation | PBKDF2-HMAC-SHA-256 with a random 128-bit salt per profile, public, rotated with a declared scope. The iteration count is set from the browser latency measured in 2.2a, following [NIST SP 800-132 §5](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-132.pdf) |
| Wrapping | AES-KW with a 256-bit key-encryption key per profile. AES-KW uses its own fixed initial value: the random-IV rule of GCM does not apply to it |
| Data keys | A 256-bit AES-GCM key, **fresh for every encryption of a file** — retries and new publications included. An unchanged encrypted artifact is promoted, never encrypted again |
| Encryption | AES-GCM with a random 96-bit IV and a 128-bit tag. With a fresh key per encryption, no key/IV pair repeats — [NIST SP 800-38D §8](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf) requires uniqueness per key |
| Authenticated data | Envelope version, package identity, report identity and the expected mapping in the manifest |
| Envelope fields | Version, password encoding, KDF, hash, iterations, salt, wrapping algorithm, report identity, the wrapped key per profile, IV, tag length and package identity — every length stated |

**The byte-level format is frozen in stage 2.2a** (RV3-01), in [`docs/encryption_envelope.md`](docs/encryption_envelope.md), which owns it from then on (N66), because equal fields are not equal
bytes (M23): the binary encoding and the format of the wrapped key; the layout of ciphertext and
tag; the layout of the encrypted payload — the Parquet and its control totals; the authenticated
data as one canonical serialisation, with fixed field order and lengths; the scope of salt rotation;
and the accepted versions, algorithms, lengths and iteration bounds, outside which the reader
refuses. Package identity is minted independently of any ciphertext hash, so nothing is defined in
terms of itself. The reader takes the identities it expects from the validated manifest, never from
the envelope it is checking. All randomness comes from a cryptographic generator, and the generation
and retry path is reviewed: fresh random keys make accidental reuse negligible, not impossible —
hence the injected-reuse test.

**What it guarantees, and what it does not.** Binding identities to the authenticated data — and
checking them against the identities the validated manifest expects — catches the substitution of
one report or package for another. It does not authenticate the publisher
against someone who knows a public password, who can produce ciphertext the site accepts (M22):
authenticity comes from the trusted release path and the HTTPS origin. A password changed in a later
release does not revoke what was already downloaded with the former one.

**Oracles:** known-answer vectors; a fixed, complete envelope vector consumed by an independently
implemented reader; producer and browser round trips through independent implementations; the whole profile × report matrix through actual unwrap and decrypt calls; wrong
passwords; altered wrapped keys, salts, IVs, tags and ciphertext; swapped report and package
identities; malformed envelopes; an injected reused key/IV pair; the finished deploy artifact
inspected for raw data and keys; and profile switching and logout clearing DuckDB tables, buffers
and caches.

---

## 4. Impacts of the separation

| Aspect | Impact | Treatment |
|---|---|---|
| Scope of eng_dados | None: it stays complete, and BI stays out of it | Objective, scope and out of scope in the README of each new repository |
| Fixes and refinements in eng_dados | The separation does not spare them: the generator, the views and the governance declarations live there. The completed project reopens for a **maintenance release, v1.1.0**, with its own acceptance and tag | Part I |
| Access to the warehouse | The only login today is the superuser (Governance §7). Copying that password into another repository is what no real environment would do | A dedicated login, member of `analyst` (N4) — the "next step" that §7 itself already states |
| Access to the showcase | No new component: encryption at the export, opened in the browser by WebCrypto (N23, §3.6). Firebase Authentication and Firestore were left out | Stages 2.2a and 2.6; an ADR in `bi-como-codigo` |
| Environment | Exporting needs only the eng_dados databases up (`make up`) | — |
| Governance | The policy of eng_dados still owns the published data; each new repository states what it publishes and cites the ADR | Stage 1.2 |
| CI/CD | Out of scope for eng_dados (Charter §4); part of the product in the showcase | Stage 2.2: a trusted workflow — same-repository previews, protected environment, federation restricted to this repository, promotion by clone (§3.4; N15) |
| Hosting | Showcase decided (N2), with a 360 MB/day quota. Study content by the probe of stage 3.1 | Engine from jsDelivr; each page loads only its own files; separate Firebase projects |
| Secrets | Each new repository needs its own guard. The `secrets_review` of eng_dados knows the keys of its own `.env`. The two demo passwords are public by design (N22) and are not secrets: they go into a register with the reason, like `segredos_tratados.yml` in eng_dados, so that the guard does not flag them | Stages 2.1 and 3.2 |
| Conventions and skills | `CLAUDE.md` and `AGENTS.md` do not come by themselves. The `revisao` skill was written to be portable — only `comandos.txt` changes —; the `adr` skill points at eng_dados paths | Stages 2.1 and 3.2 |
| Claude Code memory | It is per folder: each new repository starts with none | Conventions in the `CLAUDE.md` of each; working preferences in new memories |
| Study clock | The bash hook only records commands inside eng_dados; in the Artifact, the clock already works through the database capability | The hook and the collector extend to `caderno-de-dados` (N10; stage 3.8) |
| Study trail | Stays in eng_dados. With N6, its real outputs come to describe the v1.0.0 data | A notice at the top (N7), with the next update of the trail — local and Artifact —, never on its own |
| Portfolio | The showcase is the portfolio piece | A link on the page of project A (N12), at stage 2.10 |
| This plan and `REVIEW.md` | Moved from the root of eng_dados into this repository | Part III moves to `caderno-de-dados` at stage 3.2 |

---

## 5. Part I — maintenance release v1.1.0 of eng_dados

First in the queue (N6, N20).

### 5.1 Order count with the source

`count(distinct (source_system, order_id))` in the P01, P02, P05 and P06 views, a sweep of the other
counts and joins by identifier without the source, and a test that fails when consumption counts an
identifier without it. **Value:** fixes today's two wrong groups (M3) and closes the class of
defect. **Cost:** small; the contract types do not change. It is a fix — the behaviour becomes what
the rule already written says.

### 5.2 The ADR for O2, lineage as JSON and the exporter's login

The ADR that separates classifying from exposing (N8). `--json` in the lineage module: immediate
leaves and terminal origins per column. With N4, `governance.garantir()` comes to create a login that
is a member of `analyst`, with its password in `.env`; the proof goes through an actual connection
with that login — it reads `consumption`, is refused on the other layers, cannot write and cannot
escalate its role —, not through `SET ROLE` from the superuser (RV2-11).

### 5.3 Realism of the synthetic data (O3, N6)

| Fix, in the generator | Value | What changes |
|---|---|---|
| A declared category tree — leaf, middle and root coherent, still balanced | P01's axis gains business meaning (M7) | Names and parents of the categories |
| A price range per category | Comparing revenue across categories starts to mean something; closes the divergence between Generation §5 and the code (M8) | Every monetary value in the warehouse |
| Launch before sale, with invariant 14 | Closes D65 (M9) | Launch or sale dates; the SCD history of the product |

How each fix is done: the tree in N37, the price in N38, the launch in N39.

**The regeneration**, under [Local Execution §3.2](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/execucao_local.md#32-regerar-uma-origem-que-já-alimenta-streaming)
— destructive maintenance, with the `FORCE=1` of the procedure itself, which never overrides a
refusal for memory. [The runbook of stage 1.4](docs/regeneration_runbook.md) maps every checkpoint of that procedure to a command, an
expected oracle and a restart or rollback point (RV2-07): host producers, Beam/Prism and active jobs
stopped; CDC and the hot sink reset; the retail ingestion reset; keys and every business column
compared across both paths, and the balance by warehouse and SKU; SCD snapshots and the incremental
fact rebuilt together, with `run_results.json` kept; when the stock ledger is affected, the producer,
duplicates and alerts exercised again, with `LIMITE`, `SEED` and the offset of
`.stream/producer_state.json` recorded, and the increment checked against the full rebuild, the
invariants and P13 on the common cut; the triggered DAG run followed to its end; the recorded
operating state restored. Both sources: the legacy source regenerated by the same engine
and captured again, with a new certified capture and the retained history preserved. D62, D63 and
D64 stay declared limitations in the release evidence (N14): the sink converging does not prove the
alert right, and the Fernet key affects Airflow Connections and Variables, not the current DAG.
Current measured records are updated afterwards; accepted ADRs and historical measurements are not
rewritten.

**The recovery package follows its own rules**
([Capacity and Recovery §§3.3–3.4](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/capacidade_e_recuperacao.md#33-regras);
RV2-06). Before anything destructive: the approved package verified, and the rollback cut
identified — what state it preserves, with which code and configuration, and what would be lost
after it. The maintenance code is committed before packing, because `pack` refuses a dirty tree.
After the regeneration, a candidate is packed, restored through the nine-step sequence with its
oracles — a second destructive window, under `RESTAURAR=1` and with your authorisation —, and only
then promoted. The previous approved package stays until the promotion. A rollback follows the
recovery procedure, which rebuilds around the restored SCD memory, and never the regeneration step
that drops it.

**Side effects:** the real outputs of the study trail come to describe the v1.0.0 data, and the
notice at the top goes in with its next update (N7); `ORD-0000037` changes content; so does the copy
of the trail in the Artifact.

### 5.4 Refining the data governance (O6, N20)

- **Descriptions inherited only through transport** (RV2-08). The lineage graph is reused as
  infrastructure, not as proof of meaning: copy, sum, rounding, multiplication and cast share the
  same leaf (M21), and P01's aggregated revenue has a single immediate leaf of the same name.
  Inheritance therefore requires a conservative classification of the expression at every hop — a
  bare column reference, an alias or a value-preserving cast carries the value; aggregation,
  arithmetic, functions, generated fields and ambiguous unions require text. The existing leaf sets
  are not repurposed as that classifier, and a cast carries the value only when its types and domain
  prove it — an unknown or narrowing cast requires text. The legacy bridges
  inherit only through an explicit, reviewed declaration, because their `meta.lineage` skips the
  cleaning. The semantics of `sensitivity` do not change. A reasoned override written by hand
  survives regeneration. Counter-proofs: a same-name computed column — P01's revenue sum — that must
  not inherit, and a legacy bridge that inherits only with its declaration. Where the inherited text
  is written is N40; how it crosses the retail–legacy union, N41; the project's conventions, N44;
  constant branches, N45.
- **Written text for the computed columns** — keys, measures, flags and renamed columns —, starting
  with `analytics` and `consumption`. It is a declaration: reviewed in full by you. Its volume is not
  bounded by M18, which used the shortcut M21 disproves.
- **`domain` and `owner`** on the 41 objects that lack them, as §5.1 already requires (M17).
- **A ratchet per layer** (RV2-09, N42), over the inventory of materialised columns like the
  classification ratchet of `test_classificacao.py`, so that an omitted column cannot pass
  vacuously: a ceiling of undescribed columns, set at what stage 1.7 measures on delivery; stage 1.8
  brings `analytics` and `consumption` to zero only after you approve the text. Portal coverage
  is stated as such, apart from project-wide completeness.
- **Cost measured, not assumed** (RV2-10). One complete derivation takes about 21.6 s, and
  `make catalog` and the lineage test already derive separately. The new check shares one derivation
  with the classification and lineage checks and their test fixtures; any cache is invalidated by its
  actual inputs; and the added end-to-end cost of `make check` is measured in stage 1.7.
- Adjustments the portal reveals go in here, in the declaration — never in the generated output.

### 5.5 Out of v1.1.0

D62, D63 and D64 (N14). The consumption contract of the dimensional model (N16). Where v1.1.0 gets
recorded in eng_dados — its plan ends at Stage 13 — was left to stage 1.4, and is N27.

### 5.6 What eng_dados records (O8)

Only the references it needs, each in the document that owns the subject there:

- the ADR for O2 (stage 1.2);
- a short entry for v1.1.0, with the justification for changing the database — M3, M7 to M9 and
  M17 — and a link to this plan (stage 1.9);
- the registration, in `docs/segredos_tratados.yml`, of a false positive the history sweep has
  flagged since 2026-10-13: the Makefile line of commit `e3c226c` that sets `PGPASSWORD` from the
  variable `$(1)_DB_PASSWORD` is a reference to a variable, not a value. The fix of `ba8244a`
  cleaned the current file, but the old blob stays in history, and `make secrets-history` has
  exited with an error ever since (measured on 2026-10-22: one untreated finding, that one). Stage
  1.9 brings it back to green.

---

## 6. Stages and effort

### 6.1 How to read the effort

**Effort** is the `/effort` level recommended for Claude Code at each stage — switch at the boundary
between stages. **Size** is an estimate, not a measurement: it serves to order the work, not to
promise a deadline.

| Effort | When |
|---|---|
| `low` | No stage of this plan: all of them touch data, governance, access or publishing |
| `medium` | A closed specification and contained risk: founding a repository, probing, publishing |
| `high` | Development with tests and moderate semantic or security risk |
| `xhigh` | Subtle semantics, where an error looks right, or text that will represent the project: the regeneration runbook, the encryption envelope and access, description inheritance, the descriptions, the overview, the portal, the lesson, the writing of the governance study |
| `max` | A long, destructive operation on the machine, with many failure modes. The comparable cycle, B5, found eight deviations |

| Size | Estimate |
|---|---|
| S | One session |
| M | One to two full sessions |
| L | Several sessions, with pauses for decisions or review |

### 6.2 The stages

**Part I — eng_dados v1.1.0**

| Stage | Deliverable | Effort | Size | Depends on | Criterion to move on |
|---|---|---|---|---|---|
| **1.1** | Order count with the source (§5.1) | `high` | S | — | The new test fails before the fix and passes after; M3 redone gives zero; `make check` green |
| **1.2** | The ADR for O2 (N8) | `high` | S | — | `verificar.py` with no orphan pending item; `make check-offline` green |
| **1.3** | Lineage as JSON and the exporter's read-only login (N4) | `high` | S | — | The output contains the 14 edges of M12; the login, through an actual non-superuser connection, reads `consumption`, is refused on the other layers, cannot write and cannot escalate; `make check` green |
| **1.4** | Runbook for the data fix: every checkpoint of Local Execution §3.2 mapped to a command, an oracle and a restart point; the rollback cut; the recovery-package lifecycle (§5.3) — reviewed by Codex | `xhigh` | M | — | Codex with no blocking finding |
| **1.5** | The three fixes in the generator, invariant 14 and the tests that need no database | `high` | M | 1.4 | In-memory generation deterministic; M7–M9 redone on it; `make check-offline` green |
| **1.6** | Regeneration, the full cycle and the new recovery package | `max` | L | 1.5, the maintenance code committed and your authorisation — twice: the regeneration and the restore window | `make check` green, with the count differences explained; legacy capture certified and history preserved; event content and balances equal across both paths; the triggered DAG run finished; the candidate package restored through the nine steps with their oracles, then promoted, with the previous one kept until then; M3 and M7–M9 redone in the warehouse; the operating state restored |
| **1.7** | Description inheritance through transport, the per-layer ratchet and its measured cost (§5.4) | `xhigh` | M–L, pending a prototype of the conservative inheritance | — | Counter-proofs: a carried column inherits; a same-name computed column and an undeclared legacy bridge do not; ceilings at the coverage stage 1.7 delivers (N42); the added `make check` cost measured; `make check` green |
| **1.8** | Text for the computed columns; `domain` and `owner` on the 41 objects | `xhigh` | M–L, not bounded by M18 | 1.7 | The ceilings of `analytics` and `consumption` at zero, after your full review of the text |
| **1.9** | Documents — including the references of §5.6 —, review by Codex, acceptance and tag `v1.1.0` | `high` | M | 1.1–1.8 | `make secrets-history` green; the Owner's acceptance; push authorised |

**Part II — the `bi-como-codigo` showcase**

| Stage | Deliverable | Effort | Size | Depends on | Criterion to move on |
|---|---|---|---|---|---|
| **2.1** | Complete the foundation: the full conventions, skills, the secret guard, README with objective and map — the repository already exists, with this plan, the review and the evidence (N25) | `medium` | S | — | Secret guard green, with the two demo passwords registered as public by design |
| **2.2** | A Firebase project of its own and the trusted workflow of §3.4 — candidate and publishing workflows, federation bound to the publishing workflow on `main`, previews, promotion by version ID, one promotion at a time —, on harmless fixtures only | `high` | M–L | 2.1 | A test PR gets a preview, and its promotion is the same version ID; a fork's PR gets no credentials; a same-repository PR that changes the checker or `firebase.json` gets no preview and no live update; a preview advanced after approval and a rerun of an older job do not replace the current release; a tampered manifest and a planted clear file are rejected and nothing is uploaded; federation accepts the publishing workflow on `main` in its environment and rejects another workflow, another ref and another environment; no stored key |
| **2.2a** | The encryption envelope (§3.6): the byte-level format frozen, a reference implementation, the browser latency measured to set the iterations, and the negative tests — design reviewed by Codex | `xhigh` | M | 2.1 | An independently implemented reader consumes a fixed, complete envelope vector; known-answer vectors pass in both implementations; every negative case of §3.6 rejected; Codex with no blocking finding on the design |
| **2.2b** | The complete package-to-artifact gate of §3.4 in the publishing workflow, on encrypted fixtures: the decryption matrix, the control totals and the mutation tests | `high` | S–M | 2.2, 2.2a | Every mutation of §3.4 that the package-to-artifact gate can see — all but M19, which is 2.4's (N76) — rejected by the publishing workflow before any upload ([`docs/package_gate.md`](docs/package_gate.md) §8) |
| **2.3** | Comparative prototype of the framework on P01, opening a report encrypted with the envelope | `high` | M | 2.2a | The same page in each candidate, with what each cost and what was missing; the finished build output of each inspected — a candidate that runs report queries over clear data at build time fails; you choose |
| **2.4** | Exporters: the 16 views through the source-to-package gate (§3.4), encrypted on your machine; the governance metadata as JSON | `high` | M | 1.3, 1.9, 2.2b | One consistent read; contract, grain, nulls and decimals checked; typed rows equal to the views after the round trip — which catches M19 (N76); the mutation tests of §3.4 caught; no clear report data in Git |
| **2.5** | The complete P01 report | `high` | M | 2.3, 2.4 | Filter, chart and table agree with the package, checked in a headless browser — the chart by an oracle of its own, its interactions those of N104, a cell with no row (G) and the partial month shown as such —; keyboard and focus; 360 px; light and dark; partial month and empty slice; the browser oracle of N96 — no clear report data in the browser's stores or after logout —, planned and reviewed for the chosen framework |
| **2.6** | Per-profile access in the product (O7, N23): the login screen with the explanation and the credentials, profile switching and logout, and the P13 report at its native grain | `xhigh` | M | 2.2b, 2.5 | The whole matrix through actual unwrap and decrypt in the browser, against the preview; switching to Logística leaves no Diretoria data visible; P13's averages never re-aggregated (M20); Codex with no blocking finding (N115) |
| **2.7** | Reading portal of the data governance (§3.2) | `xhigh` | L | 1.8, 2.4 | The nine chapters and the short route from question to report to column; every number with its source and date; every warehouse object reachable through search; missing metadata labelled; declared, executed and open kept apart; no text that contradicts the declaration |
| **2.8** | Governance of the project | `high` | M | 2.4 | Every statement points to a document, ADR or history entry at the pinned commit |
| **2.9** | Executive overview | `xhigh` | M | 2.5–2.8 | Read on its own by an outsider, with no presenter; every number generated |
| **2.10** | Validation, review by Codex, the first publication by promotion of the approved preview, and the portfolio link (N12) | `high` | M | 2.2b, 2.9 and authorisation | Codex with no blocking finding; live is the approved preview version, promoted by its ID; the link on project A, with your push to the portfolio |
| **2.11** | The other fourteen reports, in batches by domain | `high` | L | 2.10 | Per report: the audit of its view for non-additivity, time-dependent balances and truncated populations; an oracle against the view; ratios only through numerator and denominator; the access matrix still proven |
| **2.12** | The dimensional model for exploration and detail, only when a report asks for it (N16) | `xhigh` | L | An ADR in eng_dados | Consumption contract applied; each published table reproduces its source |

**Part III — the study content**

| Stage | Deliverable | Effort | Size | Depends on | Criterion to move on |
|---|---|---|---|---|---|
| **3.1** | Probe on claude.ai: a private Artifact with DuckDB-WASM and its worker from jsDelivr, a report encrypted with the agreed envelope, and the read of a file published by URL with its cross-origin headers | `medium` | S | 2.2, 2.2a | Everything works → study content in the Artifact; any item fails → `*.web.app` (N18) |
| **3.2** | The `caderno-de-dados` repository and the study site | `medium` | S | 3.1, 2.10 | Secret guard green; the site reads the published showcase reports |
| **3.3** | The P01 lesson, from the view to the source | `xhigh` | L | 1.3, 1.9, 3.2 | The five proofs of [`REVIEW.md` §3.4](REVIEW.md#34-a-small-example-that-actually-takes-part-in-the-result), each with its checking query kept; no statement without evidence |
| **3.4** | Study of the governance: inventory and outline, reviewed by Codex | `high` | S | 1.9 | Each mechanism with its source, incident and planned lab |
| **3.5** | Study of the governance: writing, mechanism by mechanism | `xhigh` | L | 3.2, 3.4 | Every statement points to code or an ADR at a pinned commit; every "value" points to a recorded incident |
| **3.6** | Study of the governance: labs actually executed | `high` | M | 3.5 | Every pasted output comes from a recorded run, with its date; the state of the machine handed back |
| **3.7** | SQL explorations and the link to the study trail | `high` | M | 3.2 | Queries over the showcase reports working on the study site |
| **3.8** | Study clock on `caderno-de-dados` (N10) | `medium` | S | 3.2 | Minutes recorded with the same rule as the study trail |

### 6.3 Recommended order

1. **1.1, 1.2 and 1.4**, done. Then, by N36: settle the inheritance semantics and the ratchet
   bootstrap of §5.4 and run **1.7**, then **1.8**; then **1.5**, its code in parallel with your
   full review of 1.8's text; then **1.6** — the critical path, with its two destructive windows. **1.3** at any point; **1.9** last, for the final review,
   the acceptance and the tag.
2. In parallel with Part I, on disposable fixtures only: **2.1, 2.2a, 2.2, 2.2b, 2.3 and 3.1**. No real
   report data reaches Hosting before the gates of §3.4 exist.
3. After 2.2b, by N84 (which supersedes N73's order): **stage 13 of eng_dados** — the replication
   on Google Cloud, in a session opened there, ending with its resources destroyed —; then **2.3
   to 2.10**, pinned to the eng_dados commit accepted after stage 13 — `f86b9fb`, tag `v2.0.0`, accepted on 2026-11-13; replaced by N85 with a commit of `mvp_eng_dados_2` after its audit of the views, by N89 with `eb11709`, tag `v2.1.0`, by N90 with `2bceb47`, tag `v2.3.0`, and by N91 with `b0ef66e` — the first publication
   carries the overview, P01 and P13 with the per-profile access, the portal and the governance of
   the project, promoted from its approved preview —; then **2.11** in batches.

   **Replanned on 2026-11-17, with the pin set (N89), and on 2026-11-19 and 2026-11-20, with it
   moved to `2bceb47` (N90) and `b0ef66e` (N91):**
   1. **2.3**: its plan, [`docs/framework_prototype.md`](docs/framework_prototype.md), closed in
      round 8 of Codex's review on 2026-11-20 — 55 findings in rounds 1 to 8, 23 blocking, all
      answered, shaped by N94 to N96 —; its step 1 is built and its review closed (N97); steps 2 to 6
      ran and their review closed (N103); done on 2026-11-24 with the Owner's choice, ADR-0004. It reads invented data, so the
      pin does not reach it: the twelve columns its fixture copies from P01 at `f86b9fb` are, in the
      same order, the ones M55 read at `eb11709` and M59 at `2bceb47`, the views of `b0ef66e`.
   2. **N86**, the gate with two checkouts, in its PR of its own — before any document links
      `mvp_eng_dados_2` at `b0ef66e`, as 2.4, 2.7 and 2.8 will. Implemented on 2026-11-20:
      `ENG_DADOS_2_DIR` names the checkout of `mvp_eng_dados_2`, `make check` requires both
      variables, and `docs-check` reads each link only in the checkout of the repository its URL
      names. Merged into `main` on 2026-11-24 (PR #31, `85cab80`), the Owner having authorised it.
   3. **2.4** no longer waits for the source: its dependencies are done and its pin is set. It
      waits for its written plan, [`docs/exporter.md`](docs/exporter.md), reviewed by Codex, and for a
      read window from the Owner (N86 is in `main` since 2026-11-24); it starts from the 16 views as M59 read
      them, each view's key by the roles `grain` and `identity` of the package's `view_rules`
      (UQ-18), and the provenance read in the same transaction. It does not wait for 2.3: the two
      meet only at 2.5. **Done on 2026-11-25**: merged as PR #32 at `e9f3007`, the tag `checkpoint-2.4`
      there.
   4. **2.5 to 2.10** as above, by N115: from the tag `checkpoint-2.4`, each with a short plan the Owner approves, and Codex only at 2.6 and 2.10. 2.5's is [`docs/report_page.md`](docs/report_page.md), with N116 to N119. Each report's audit cites the package's `view_audits`, the result
      of the checks its ids name (UQ-19; M60), and redoes its oracle on this state: nothing measured
      before the regeneration carries over (M56).
   5. **2.11** in batches, as above; P11 and P12 are weighed at their batch (§7).
4. After 2.10 and 3.1: **3.2 to 3.8**.

---

## 7. What is still decided, at the right moment

Every design question is answered (§1.2). Two kinds of decision remain.

**Choices that stand unless you object:** the restricted profile is **Logística, with P13 only** —
you delegated the choice, and it is the one the story explains best; lineage arrives through the
`--json` of eng_dados, carried in its metadata package (the former N11; N87); the lesson reads the inner layers through the custodian, in
a read-only transaction, with no new role (the former N5).

**Decisions that only fit during execution** — work stops until you answer:

- the framework, after the prototype of stage 2.3 — decided on 2026-11-24: the build of our own
  ([ADR-0004](docs/adr/0004-build-the-reports-and-the-portal-on-a-page-of-our-own.md));
- the authorisation of the regeneration and of the restore window, in 1.6 — both destructive;
- the full review of the written descriptions, at 1.8;
- the acceptance of v1.1.0 and every push, from 1.9 onwards;
- the creation of `caderno-de-dados` and of the Firebase project, at 3.2 and 2.2 — done by you or
  with your authorisation; `bi-como-codigo` already exists (N25);
- the ADRs for the new components of each repository — hosting, CI pipeline and per-profile
  encryption —, recorded as each one is born;
- if federated credentials with the Firebase CLI prove infeasible in 2.2, the way forward comes
  back to you; N15 stands until then;
- if a report needs averages re-aggregated beyond the grain of its view, the sufficient statistics
  require an upstream contract change, with an ADR in eng_dados — yours to decide (M20);
- the result of the probe of stage 3.1 needs no decision: the rule of N18 already says what to do;
- **raised on 2026-11-13 by eng_dados' move to `mvp_eng_dados_2` (§3.5.1)** — all decided: the pin
  of 2.4–2.10 and the two sources of the gate the same day (N85, N86), and on 2026-11-14 the two
  portals, which read the one package (N87);
- **raised on 2026-11-14 by N88**, no new Google Cloud resource: if the probe of stage 3.1 fails, N18
  sends the study content to a `*.web.app` of its own — a new Firebase project, which N88 rules
  out. Where the study content lives then is yours, at 3.1; until then nothing changes.
- **raised on 2026-11-17 by `v2.1.0` (§3.5.1)**:
  - the before → after of the twelve views with no "before" here (M56): `mvp_eng_dados_2` offers to
    rebuild the state before its cycle from its recovery cut, in an ephemeral database, if asked — work
    of that session, at your request. Recommended: not to ask; the showcase publishes only the state
    of its pin, and M55 was the baseline, M59 since 2026-11-19;
  - V5, P11's median stock turnover of 0.02 per quarter (M56): **corrected at `v2.2.0`** — 0.46 at
    `2bceb47` (M59) — and closed in the source's records at `070314f` (UQ-22). P11 has no limitation
    to declare; what is left is its ordinary audit at its batch of 2.11;
- **raised on 2026-11-19 by `v2.3.0` (§3.5.1)**: P12, `skus_below_reorder_point`, reads each pair's
  reorder point, which is 0, 1 or 2 units with this sparse demand; its 213 rows are all at zero
  available (M59), so "below the reorder point" is "out of stock among the pairs that sold in the
  year" — consistent with the rule, a cost its ADR 0057 accepted, and not a replenishment signal
  beyond that. P12 published at its batch of 2.11 saying so, or held until the data separates the
  two. Decided at that batch; P12 is not in the first publication.
- **raised on 2026-11-20 by `mvp_eng_dados_2`'s answer (§3.5.1)**: the cross-project mailbox —
  decided the same day, created as asked (N92).

---

## 8. Risks

| Risk | Treatment |
|---|---|
| The regeneration breaks what no test covers | A reviewed runbook (1.4) with every checkpoint mapped, the approved package verified beforehand, one step at a time with an oracle, a written rollback cut |
| The recovery package stops representing the state | Candidate packed after the regeneration, restored through the nine steps, then promoted; the previous one kept until then (§5.3) |
| Machine memory (R11) | Only the guarded targets; a refusal for memory stops and asks the Owner, never `FORCE=1` on our own |
| An inherited description with the wrong meaning | Inheritance only through transport at every hop; legacy bridges only by declaration; disagreement written by hand with a reason; inherited text reviewed by sample and written text in full |
| The showcase states what the record does not support | Every number generated from a record at a pinned commit; Codex reviews the showcase before the first publication |
| Clear report data reaching the public repository or Hosting | Encryption at the export on your machine; an explicit inclusion list; the finished output inspected by content, previews included (§3.4) |
| Untrusted code deploying | Candidate code builds without credentials; the publishing workflow runs only reviewed code from `main` and treats the candidate as data; federation bound to that workflow; promotion by version ID, one at a time, superseded candidates rejected (§3.4) |
| Equal fields read as equal bytes | One canonical serialisation of the authenticated data, and expected identities taken from the validated manifest (§3.6; M23) |
| A framework that prerenders report rows | The prototype inspects the finished output of each candidate (2.3) |
| Federated credentials do not work with the Firebase CLI | Proved in 2.2 on fixtures; if not, the way forward comes back to you (§7) |
| A wrong package passing as consistent | Row-level equality with the views and mutation tests (§3.4; M19) |
| The encryption built wrong — a repeated key/IV pair, weak derivation, a key or a Parquet in the clear | The envelope of §3.6, fixed parameters, a fresh data key per encryption, the negative tests and the artifact inspection; Codex reviews the design before the prototype |
| A public password flagged by the secret guard | Both credentials registered as public by design, with the reason (N22) |
| The portal becomes the whole graph again | Lineage one hop at a time; narrative by chapters before the reference; the short route from question to column |
| The daily quota of free Firebase | Engine from jsDelivr; each page loads only its own files; separate projects |
| jsDelivr being down turns off interactivity | Accepted in N2; the page shows the error instead of stale or empty numbers |
| claude.ai limits the study content | The probe of stage 3.1 decides before building; the rule of N18 sends it to a `*.web.app` |
| An average or ratio re-aggregated wrongly | Native grain without sufficient statistics (M20); numerator and denominator otherwise; the per-report audit |
| eng_dados changes and a site diverges silently | The accepted contract pinned here and anchors at a pinned commit: export and build fail loudly. Values are not in the contract: each new pin is captured and compared by fingerprint with the last capture (M55, M59, §3.5) |
| A partial dbt manifest after a `dbt --select` | The exporter rejects lineage with problems, as `lineage.main` already does |
| Volume nobody reviews (R14) | Reports, portal chapters, access rules and the lesson path are declarations in text, reviewed in full; what is generated, by oracle |

---

## 9. Not verified, and assumptions

**Not verified:**

- whether DuckDB-WASM, its worker, WebCrypto and a cross-origin read work inside the claude.ai
  Artifact — 3.1 measures it;
- how long the key derivation takes in the browser, with the chosen iterations — measured on the desktop, Node's M47 and Chrome's M49; a phone's is not;
- whether the Firebase CLI accepts federated credentials from GitHub in practice — only community
  guides describe it —, and whether deploy and clone run inside a `workflow_run` job bound to
  `workflow_ref` — 2.2 proves both;
- whether each framework candidate can keep report queries away from build time — 2.3 inspects it;
- whether the chosen framework bundles DuckDB-WASM into the site itself or accepts jsDelivr — answered by
  N94 and ADR-0004: jsDelivr, pinned;
- what Firebase does when the Spark plan runs over its quota;
- the volume of description text to write — measured by 1.7: 250 text roots (M40);
- the time and memory of the regeneration and of the restore window with the new data;
- whether the change to §4 of Governance affects any classification or access test;
- accessibility and usability of the sites.

**Assumptions:**

- eng_dados remains the single source of the data, the rules and the governance; the new
  repositories neither recompute metrics nor rewrite metadata;
- the data only changes through a deliberate regeneration, so updating is rare;
- reports, chapters, access rules and the lesson path stay small enough, as text, for a full review.

---

## 10. Review by Codex

The review of this plan is closed: round 5 closed RV4-01, RV3-02 and RV2-05 at the plan level, with
no new finding. Closure means that the plan requires the work and its exit evidence, not that any
gate has passed — the acceptance and rejection tests of stage 2.2 and every other exit criterion
of §6.2 remain to be proved. The next reviews by Codex are the ones the stages of §6.2 call for,
starting with the [runbook of 1.4](docs/regeneration_runbook.md#10-review-by-codex), whose findings
are recorded in the runbook itself.

The probes re-run with the eng_dados databases up (`make up`) and nothing else:
`evidence/20261022/ro.sh <file.sql>`, with `ENG_DADOS_DIR` pointing at the eng_dados checkout,
always in a read-only session. The Python probes need only the `.venv` of eng_dados and a complete
dbt manifest; the Parquet export, `uv`. See [`evidence/20261022/README.md`](evidence/20261022/README.md)
and [`evidence/20261023/README.md`](evidence/20261023/README.md).
