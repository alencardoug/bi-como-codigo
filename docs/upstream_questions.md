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
| Date | 2026-11-13 — revision 1: written after its notice to this repository (`data/medicoes/base_consumidores/avisos/aviso_bi_como_codigo.md` there, outside its Git) and its `PLANO_base_dos_consumidores.md` at `35abb03`, both read on 2026-11-13 |
| Author | Claude Code, in the `bi-como-codigo` session |
| Status | **Open**: 11 questions, none answered |

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

## Answers

None yet.
