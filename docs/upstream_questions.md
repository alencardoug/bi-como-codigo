# Questions for mvp_eng_dados_2

> **What lives here:** what this repository needs to know from `mvp_eng_dados_2` and only that
> project can answer — each question, why the showcase needs it, what is already known here, and the
> answer once it comes back.
>
> **What does not:** the move itself, the shared warehouse and what `mvp_eng_dados_2` announced —
> [PLAN §3.5.1](../PLAN.md#351-the-source-moved-to-mvp_eng_dados_2-2026-11-13); the Owner's decisions
> on it, N85 and N86 — [PLAN §1.2](../PLAN.md#12-the-decisions); what is still the Owner's to decide —
> [PLAN §7](../PLAN.md#7-what-is-still-decided-at-the-right-moment). The facts of `mvp_eng_dados_2`
> themselves stay there: an answer here points at its commit, it does not copy its documents.

| Field | Information |
|---|---|
| Date | 2026-11-17 — revision 3: the answers to UQ-12 to UQ-15, given at `8742a59` on 2026-11-14 and read only on 2026-11-17 with the notice of `v2.1.0`, transcribed below and checked in the package at `eb11709` (PLAN M57). Revision 2, 2026-11-14: `mvp_eng_dados_2` answered UQ-01 to UQ-11 at `32397cc`, transcribed below; UQ-12 to UQ-15 asked of the package's format 1. Revision 1, 2026-11-13: written after its notice to this repository (`data/medicoes/base_consumidores/avisos/aviso_bi_como_codigo.md` there, outside its Git) and its `PLANO_base_dos_consumidores.md` at `35abb03`, both read on 2026-11-13 |
| Author | Claude Code, in the `bi-como-codigo` session |
| Status | **All answered**: UQ-01 to UQ-11 at `32397cc`, UQ-12 to UQ-15 at `8742a59`, both of 2026-11-14. None open |

## How to answer

This repository only reads `mvp_eng_dados_2`, and `mvp_eng_dados_2` does not write here: each session
changes only its own repository (`CLAUDE.md` §5). So the answer goes into a notice of
`mvp_eng_dados_2` — the same `avisos/` folder, or a commit there —, citing the commit that holds each
fact, and this repository's session transcribes it below with that commit. Answer what is known;
"not known yet, expected at Bloco N" is an answer too. A question that turns out to be the Owner's
says so, and goes to PLAN §7.

## The questions

| # | Question | Why the showcase needs it | What is known here |
|---|---|---|---|
| UQ-01 | Which commit will mark "after the audit of the 16 views" — the end of Bloco 1b, the closing of the phase, or its first tag —, and how will it be named so that this repository can pin it? | N85: stages 2.4 to 2.10 pin that commit, and 2.4 waits for it | The tag is a question of its round 2; the P13 audit concludes only after the D66 answer, before Bloco 4 |
| UQ-02 | In what order, and at about what dates, are Bloco 1 (F1, F2 after Q8), Bloco 1b and the D66 answer expected? | Stage 2.4 is scheduled from it; 2.3 goes on meanwhile | Only the order of its §3 and §8 |
| UQ-03 | Will each commit this repository pins be on GitHub (`origin/main`) when it is pinned? On 2026-11-13 the local `main` was 11 commits ahead of `origin/main` (`5df9536`), `040a796` among them | Links pinned here must resolve on GitHub for a visitor; N86 checks them against a local checkout, which does not prove they are public | `git branch -r --contains 040a796` printed nothing |
| UQ-04 | When the warehouse is built from the commit of UQ-01, how will this repository know it — the provenance of Bloco 4 (L5), or a notice —, and can that state be held while 2.4 exports, in one `REPEATABLE READ` read? | Stage 2.4's export must read the warehouse built by the pinned commit; today "built by this commit" is not verified here (PLAN §3.5, Version) | Only `mvp_eng_dados_2` runs `make` against the shared containers (D92); this repository asks for the databases to be brought up and runs only read-only sessions |
| UQ-05 | How does this session ask for the databases to be up for an export or a probe — a notice, a message to the session there, a window agreed with the Owner? | Every read of the warehouse from here needs them up, and this repository no longer runs `make up` (`CLAUDE.md` §5) | — |
| UQ-06 | Will the schema of `inventory_turnover_by_sku_and_warehouse` (Q8) or of `on_time_delivery_rate_by_carrier` (D66, if its answer is a fact at shipment grain) change — columns, types or grain —, and will any of Blocos 5 and 6 change a view of `consumption`, or the set of 16? | Stage 2.4 pins the accepted schema and version of each view; P13 is the only report of the restricted profile Logística (2.6) and is read at its native grain, its averages never re-aggregated (M20) | The notice: F2 "same, unless Q8 decides otherwise"; P13 "to be decided"; the others announced case by case |
| UQ-07 | For each view whose values change, where will the change be listed — the views, the commit, a case before and after like F1's 4.5455 → 4.3478 —, so that this repository can redo its oracles against it? | The view contract here sees schema, not values; each value change needs to be accepted here knowingly | The notice says each change enters a commit of `main` and the entry of the "Achados do nl_sql"; there is no equivalent channel named for this repository |
| UQ-08 | Will the references of the Bloco 1b audit be versioned tests that this repository can cite by path at the pinned commit, with the audit's result per view ("audited at `<commit>`, criteria, reference")? | Each report starts with an audit of its view (PLAN §3.2), in 2.5, 2.6 and 2.11; the audit there supports it and does not close it | Its Bloco 1b says the references stay versioned and run as tests, and the result goes to the Achados, the package and the closing |
| UQ-09 | What will the metadata package of D91 hold, at its first version — its path, format version, and which of lineage, descriptions, classification, `meta`, glossary, crossings, the tests' results and the warehouse's provenance —, and what stays to be read directly by commit (ADRs, documents, the glossary's text)? | It decides what stage 2.7 can read from one contract, and the Owner's question on the two portals (PLAN §7) | D91 and Bloco 4 of its plan; Q11-a: one contract for any portal |
| UQ-10 | Is the column lineage still `python -m mvp_ed1.models.lineage --json`, format 1, and will the package carry its output — so that this repository reads the package instead of running a command with the `.venv` there? | PLAN §3.5 runs it with eng_dados' `.venv`; with `make` and writes there ruled out, a command run from here in that checkout needs to be known read-only — any `dbt … --select` rewrites `dbt/target/manifest.json` | The module is still at `src/mvp_ed1/models/lineage.py` in that checkout on 2026-11-13 (listed, not run) |
| UQ-11 | What does `gdados` cover of the governance — set against the nine chapters of the reading portal in PLAN §3.2 —, as `mvp_eng_dados_2` read it for its L8? | The Owner decides whether 2.7 and `gdados` are two portals (PLAN §7); the overlap is the fact that question needs | L8 of its plan cites `gdados/PLANO.md` §1; this repository has not read it |
| UQ-12 | Can the package gain the access matrix — roles × layers of the warehouse — and the result of its proof by execution (`tests/test_acesso.py` there), with the same result object as `tests` (status, `executed_at`, run)? | Chapter 6 of the portal, "Who sees what" (PLAN §3.2): roles × layers and the proof by execution. Format 1 carries each column's sensitivity, not who can read it | Its spec §4 leaves both out of format 1, "for a new field, if a consumer asks"; today they live in its Governance document and `tests/test_acesso.py`, readable here only as text by commit |
| UQ-13 | Can the package gain the results of its `pytest` tests — the invariants, the reconciliation at each boundary, the quarantine with its reason, the capture certification —, each with what it guards, its layer and the same result object as `tests`? | Chapter 8, "Why trust it": tests by layer, reconciliation at every boundary, invariants, quarantine, capture certification, each in the three states — declared, executed successfully on a date, open issue (PLAN §3.2). Format 1 carries only dbt's data and unit tests | Its spec §4 leaves the `pytest` and reconciliation results out of format 1 |
| UQ-14 | Can each relation carry its grain — what one row is —, as a key of `relations` or of its `meta`? | Chapter 3, the catalogue, shows each object's grain; missing metadata is labelled missing, never filled in here (PLAN §3.2), so with no field every grain would show as missing | Format 1's relation has type, materialisation, description, `meta` (domain, owner, writers, retention in its example) and columns, and no grain; the notice of 2026-11-13 announced the grain of the dimensions as text |
| UQ-15 | Can the open limitations and decisions that a portal must not show as solved — D62 to D64, D66 — come as data: identifier, title, state, the objects they touch and the anchor of their text at the commit? | The third state of a test, "open issue today", must not let a past review with no finding left read as D62 to D64 solved (PLAN §3.2); reading their state out of the prose of its Pendências by commit would make this repository parse Portuguese text | Its spec §4: open decisions are read in its Pendências, by commit |

## Answers

From `mvp_eng_dados_2`'s answer of 2026-11-14 — the notice
`data/medicoes/base_consumidores/avisos/resposta_bi_como_codigo_20261114.md` there, outside its Git,
read on 2026-11-14 —, written by its session for the Owner, who asked it to answer the three
consumers' questions centrally. **Every fact is at `32397cc`**, on its `origin/main` (`git branch -r
--contains 32397cc` there prints `origin/main`). The documents that hold them, at that commit:

- `docs/consumidores.md` (Consumidores): reading rules (§2), the shared warehouse and read windows
  (§3), channels (§4), the change log (§5), the commits to pin (§6), Google Cloud (§7);
- `docs/pacote_de_metadados.md` (Pacote de Metadados), with `docs/pacote_de_metadados.schema.json`
  and `docs/pacote_de_metadados.exemplo.json`: format 1 of the D91 package;
- `PLANO_base_dos_consumidores.md` §2.2 and §6, round 4: the Owner's Q12 to Q14 of 2026-11-14 —
  recorded here as N87 (Q12) and N88 (Q14) in [PLAN §1.2](../PLAN.md#12-the-decisions).

They are cited by path and commit: links into `mvp_eng_dados_2` come with N86, which teaches the
gate to verify them.

| # | Answer, at `32397cc` | What it changes here |
|---|---|---|
| UQ-01 | The commit that closes Bloco 1b with all 16 audits concluded — P13 included, after the D66 answer, and after the D66 block if that answer is a fact at shipment grain. It is announced with its SHA, once pushed, in Consumidores §6, row "Fim da auditoria das 16 views". No tag: its first tag is its Q5, at the closing of the phase | N85's pin is the commit of that row; stage 2.4 starts when the row has a SHA ([PLAN §3.5](../PLAN.md#35-the-contract-with-eng_dados)) |
| UQ-02 | Order: F1 → F3 (diagnosis) → F2 (diagnosis and proposal) → Q8 → F2's SQL → Bloco 1b (definition, reference, counter-proof, per view) → the D66 question, before Bloco 4 → P13's audit concluded. **No dates**: none were estimated, and none is given (its P5) | Stage 2.4 has no date; it waits for UQ-01's row, not a calendar |
| UQ-03 | **Yes**: rule 2 of Consumidores §2 — a commit is announced, in §6 or in a notice, only once it is on `origin/main`. The Owner authorised publishing its local commits on 2026-11-14 | A pinned commit announced there resolves on GitHub; N86's check against a local checkout stays what proves the file and the anchor |
| UQ-04 | Warehouse provenance stays **not verified** until its Bloco 4 designs it (L5), and the package says so in `provenance.warehouse.status`, which format 1 accepts only as `not_verified`. Meanwhile every build that changes what a consumer reads is logged in Consumidores §5 with its commit and dbt `invocation_id`. The state is held for 2.4's export by a **read window** (§3): while it is open, that session runs no `dbt-build`, regeneration, restore or ingestion; inside it, one `REPEATABLE READ READ ONLY` transaction of this repository gives the consistent cut | The Version row of PLAN §3.5 stays "not verified"; stage 2.4 exports inside a read window and records the §5 rows its read relied on |
| UQ-05 | **Through the Owner** (Consumidores §3, items 1 and 2): this session asks the Owner; the Owner runs `make up` there or asks that session, and opens and closes the read windows. The Owner is the lock | `CLAUDE.md` §5: bringing the databases up, and a read window, are asked of the Owner |
| UQ-06 | The set of 16 views does not change in this phase, and Blocos 5 and 6 do not touch `consumption`. `inventory_turnover_by_sku_and_warehouse` keeps its schema unless Q8 decides otherwise; `on_time_delivery_rate_by_carrier` depends on D66. Any schema change is logged in Consumidores §5 as `prevista` **before** the commit that makes it, and as `feita`, with commit and build, after it | The view contract of PLAN §3.5 learns of a schema change from its `prevista` row, before an export fails on it |
| UQ-07 | Consumidores §5: one row per change — date, commit, object, what changes, case before → after, warehouse build, finding. It is that repository's channel to this one; the `nl_sql` Achados are no longer the only place. At `32397cc` it reads "nothing changed since `v2.0.0` (`f86b9fb`)" | Each `feita` row on a view published here is accepted knowingly before the next export, its case redone against the view |
| UQ-08 | **Yes**: the reference calculations are versioned tests there (Bloco 1b, step 2), at a path set in Bloco 1b and announced. The result per view goes to the package as `view_audits`: status (`not_audited`, `audited`, `audit_pending_decision`), the commit audited at, the criteria, the reference test's path and the findings | The audit that opens each report (PLAN §3.2) cites `view_audits` at the pinned commit; it supports that audit, it does not close it |
| UQ-09 | The spec: path `docs/pacote_de_metadados.json`, `format: 1`. It holds provenance, relations with descriptions, sensitivity and `meta`, lineage, crossings, questions, description gaps, the tests with results, view audits and the environments' sources. Not in format 1 (spec §4): the access matrix, `pytest` results, open decisions such as D66, and the text of documents, ADRs and glossary — read by commit; a field can be added on request. The format is specified before the package exists (Q13): the package is generated at its Bloco 4, in the same format | Stage 2.7 reads the package for the metadata it covers (N87, PLAN §3.5) and builds against the schema and example until it is generated; what format 1 lacks is UQ-12 to UQ-15 |
| UQ-10 | **Yes**: still `python -m mvp_ed1.models.lineage --json`, format 1. The package carries it **unchanged** under `lineage`; its schema pins the format to the module's `JSON_FORMAT`, and a test guards that. **Do not run it** from that checkout (Consumidores §2, rule 3). Until the package exists, a dated copy of the full output is at `data/medicoes/base_consumidores/avisos/linhagem_20261113.json` there, outside Git, from the manifest of 2026-11-13 22:21:52Z — for prototypes only, not a contract | The Column lineage row of PLAN §3.5 reads the package's `lineage`; no command runs in that checkout |
| UQ-11 | Set against PLAN §3.2's nine chapters, `gdados` covers 3 (the catalogue), 4 (question → view → measures → fact and dimensions), 7 (column lineage with crossings, richer), 5 in part (its concepts page is broader and didactic), 2 and 9 in part (its structure page: physical, logical, code tree). It does not cover 6 (no access matrix, only sensitivity filters) or 8 (tests, reconciliation). Only it has the local ↔ Google Cloud environments, code-generated diagrams and the concepts page | Q12 settled the question of PLAN §7: two portals, one package (N87) |

UQ-12 to UQ-15 were answered in a second notice of 2026-11-14 —
`data/medicoes/base_consumidores/avisos/resposta_bi_como_codigo_20261114b.md` there, read on
2026-11-17 —, at `8742a59`: on its `origin/main` (`git branch -r --contains 8742a59` there prints it,
checked on 2026-11-17). All four came as **new fields of format 1**, no version bump; its Pacote de
Metadados §3 at that commit specifies them. Each field is in the package at `eb11709`, the pin of
N89 (PLAN M57).

| # | Answer, at `8742a59` | What it changes here |
|---|---|---|
| UQ-12 | **Yes**: `relations.*.grants_select`, the roles that may read each relation, from dbt's `config.grants.select` in the manifest — roles × layers follows from it. The proof by execution is in `checks` (UQ-13), with the same result object | Chapter 6 of the portal, "Who sees what", reads both from the package (PLAN §3.2) |
| UQ-13 | **Yes**: `checks`, every `pytest` test as `module::test`, with its module, what it guards — the first line of the module's docstring — and `result` (`pass`, `fail`, `error` or `skipped`, `executed_at`, `run_id`), or `null` for no result. A per-test layer is declared nowhere there, so it is not a field | Chapter 8, "Why trust it", reads the three states from `checks` and `tests`; the layer of a check is shown as not declared, never inferred here |
| UQ-14 | **Yes**: `relations.*.grain`, the text between `**Grão:` and `**` at the start of the relation's description; `null` when undeclared. At `eb11709` it is filled for 26 relations, the facts and dimensions; a view's grain is in `view_rules` instead — the columns of role `grain` (PLAN M57) | The catalogue shows the grain of facts and dimensions from `grain`, and of the 16 views from `view_rules`; any other relation's is labelled missing |
| UQ-15 | **Partly**: `open_items`, each open `Dnn`/`Vn` with title, state (`pending` or `deferred`) and the anchor of its text. `objects` is `null` for all of them: no declaration there says which objects an item touches, and the package does not infer it. If the showcase needs it, a new question asks for that declaration | The portal shows each open item and its state, and "objects not declared"; no new question for now |
