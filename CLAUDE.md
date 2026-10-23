# Working conventions

> **What lives here:** how this repository is worked on — language, commits, assisted development
> and the rules that are never broken.
>
> **What does not:** what the project is (see the [README](README.md)); what gets built and in what
> order (see the [plan](PLAN.md)).

---

## 1. Context

`bi-como-codigo` is the showcase of [mvp_eng_dados_1](https://github.com/alencardoug/mvp_eng_dados_1):
reports, a data-governance reading portal and least-privilege access over its synthetic retail
warehouse. It is in the planning stage. Until stage 2.1 of the plan settles the full conventions of
this repository, the [conventions of mvp_eng_dados_1](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/CLAUDE.md)
are the baseline; where they differ, this file wins.

## 2. Language

Decided by the Owner on 22/10/2026.

| Content | Language |
|---|---|
| Code, comments, identifiers, commit messages, technical documents — README, plan, reviews, ADRs — and the communication between Claude Code and Codex | English |
| What visitors of the showcase read — report text, portal narrative, labels — and everything derived from the declarations of mvp_eng_dados_1, which are in Portuguese | Portuguese |
| The conversation with the Owner | Portuguese |
| Evidence recorded in Portuguese | Kept as recorded |

The study content lives in its own repository, `caderno-de-dados`, in Portuguese.

## 3. Commits

[Conventional Commits](https://www.conventionalcommits.org/), with the description in English. One
subject per commit: a message that needs "and" is probably two commits.

## 4. Assisted development

- Claude Code is a development tool, with no power of approval. The Owner decides.
- Decisions are asked in rounds of up to four questions, each with real alternatives, what each one
  protects and costs, and the recommended one first, with the reason.
- Large work is planned in writing and reviewed by Codex before it is executed.
- A number that was not measured is marked as pending: "planned" and "measured" never mix.
- Declarations are reviewed in full; what is generated from them, by sample and by oracle. An error
  in generated output is fixed in the declaration, never in the output.
- Nothing that calls for an ADR is decided by an agent alone.

## 5. Rules that are never broken

1. No secret in the repository. The two showcase passwords are public by design (decision N22 of the
   plan) and will be registered as such when the secret guard is set up.
2. Synthetic data only, all of it produced by mvp_eng_dados_1.
3. No metric is redefined here: reports read the views of mvp_eng_dados_1 and never recompute them.
