# Working conventions

> **What lives here:** how this repository is worked on — language, naming, commits and the gate,
> assisted development, the rules that are never broken and the definition of done.
>
> **What does not:** what the project is and the map of its documents (see the [README](README.md));
> what gets built and in what order (see the [plan](PLAN.md)); how a decision is recorded (see the
> [decision record](docs/adr/README.md)).

---

## 1. Context

`bi-como-codigo` is the showcase of [mvp_eng_dados_1](https://github.com/alencardoug/mvp_eng_dados_1):
reports, a data-governance reading portal and least-privilege access over its synthetic retail
warehouse. These conventions are complete since stage 2.1 of the plan: the
[conventions of mvp_eng_dados_1](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/CLAUDE.md)
were their baseline, and apply here only where this file adopts them.

## 2. Language

Decided by the Owner on 22/10/2026.

| Content | Language |
|---|---|
| Code, comments, identifiers, commit messages, technical documents — README, plan, reviews, ADRs, skills — and the communication between Claude Code and Codex | English |
| What visitors of the showcase read — report text, portal narrative, labels — and everything derived from the declarations of mvp_eng_dados_1, which are in Portuguese | Portuguese |
| The conversation with the Owner | Portuguese |
| Evidence recorded in Portuguese | Kept as recorded |

The study content lives in its own repository, `caderno-de-dados`, in Portuguese.

## 3. Naming

- Python: `snake_case` for modules, functions and variables; one package, `bi_como_codigo`.
- Files of technical documents and data: English, `snake_case` (`public_by_design.yml`); ADRs in
  `NNNN-title-in-kebab-case.md` ([decision record §1](docs/adr/README.md#1-how-it-works)).
- Names that come from mvp_eng_dados_1 — schemas, views, columns, the codes of its business
  questions (P01–P16) — are used as they are there, never renamed here.

## 4. Commits and the gate

[Conventional Commits](https://www.conventionalcommits.org/), with the description in English. One
subject per commit: a message that needs "and" is probably two commits.

**`make check` is the gate before every commit** — secrets in the tracked files and in the history,
the documents, the decision record and the tests. Commit only when it exits 0, read from its own exit
code: never through a pipe, where the exit code is the last command's. It needs `ENG_DADOS_DIR`
naming a checkout of mvp_eng_dados_1 (see the [README](README.md#checking-the-repository)).

**Push only with the Owner's authorisation**, given for that push.

## 5. Assisted development

- Claude Code is a development tool, with no power of approval. The Owner decides.
- Decisions are asked in rounds of up to four questions, each with real alternatives, what each one
  protects and costs, and the recommended one first, with the reason.
- Large work is planned in writing and reviewed by Codex before it is executed; the hand-off between
  the two agents uses the `review` skill ([`.claude/skills/review/`](.claude/skills/review/SKILL.md)).
- A number that was not measured is marked as pending: "planned" and "measured" never mix.
- Declarations are reviewed in full; what is generated from them, by sample and by oracle. An error
  in generated output is fixed in the declaration, never in the output.
- Nothing that calls for an ADR is decided by an agent alone: stop, list it in the
  [decision record](docs/adr/README.md#3-pending) and ask (`adr` skill).
- **Each subject has one owning document.** Every document opens with what lives in it and what
  does not; the others point at it by link and identifier (Nn, On, Mn, RP-nn, RVn-nn, ADR-nnnn,
  stages) instead of repeating it. A fact of mvp_eng_dados_1 is cited by a link pinned to a commit,
  never copied — `make check` refuses an unpinned one.
- **mvp_eng_dados_1 is read, never written, from here.** Probes run in a read-only session
  (`evidence/20261022/ro.sh`); no target of that project that rewrites data — reset, seed, a load or
  fact test, anything with `FORCE=1` — is run from this repository. Its own changes are made in
  sessions opened there.
- Nothing fixes a path, a credential or an environment name in the code: configuration comes from
  environment variables, so that sandbox, qa and prod on Google Cloud stay possible.

## 6. Rules that are never broken

1. No secret in the repository. The two showcase passwords are public by design (decision N22 of the
   plan) and are registered as such, with the reason, in
   [`docs/public_by_design.yml`](docs/public_by_design.yml); any other credential shape fails the gate.
2. Synthetic data only, all of it produced by mvp_eng_dados_1.
3. No metric is redefined here: reports read the views of mvp_eng_dados_1 and never recompute them.

## 7. Definition of done

Before a delivery is considered finished:

- [ ] `make check` green, with its output in hand;
- [ ] the exit criterion of the stage, in the [plan §6.2](PLAN.md#62-the-stages), met — and what it
      could not measure marked as pending, not as done;
- [ ] declarations reviewed in full, generated output by sample and by oracle (§5);
- [ ] documents updated in their owning place, with no duplication;
- [ ] relevant decisions recorded in an ADR, by the Owner;
- [ ] for work Codex reviews, the dossier of the `review` skill complete.
