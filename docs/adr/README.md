# Decision record

> **What lives here:** the index of the architecture decisions of this repository — the accepted
> ADRs and the ones still to be written — and how they are numbered.
>
> **What does not:** the decisions as taken by the Owner during planning (see
> [PLAN.md §1](../../PLAN.md#1-what-is-already-decided)); the decisions of mvp_eng_dados_1, which
> live in its own record; how an ADR is written and the index kept, which is the `adr` skill
> ([`.claude/skills/adr/SKILL.md`](../../.claude/skills/adr/SKILL.md)).

## 1. How it works

- One ADR per subject, numbered in sequence from `0001`, in `NNNN-title-in-kebab-case.md`, from the
  [template](0000-template.md). A number is never reused; a decision that changes is a new ADR that
  supersedes the old one.
- An ADR records a decision **of the Owner**. No agent decides what calls for an ADR (`CLAUDE.md`
  §4): the agent stops, lists it in §3 and asks.
- Many decisions were already taken in the plan (N1–N25, O1–O8). An ADR records one of them when the
  component it chose is born, with the alternatives and the cost accepted — the plan says what was
  chosen, the ADR keeps why.

## 2. Accepted

| ADR | Title | Date | Resolves |
|---|---|---|---|

None yet.

## 3. Pending

Each row is an ADR the plan already calls for ([PLAN.md §7](../../PLAN.md#7-what-is-still-decided-at-the-right-moment)),
written when its component is born.

| Pending | Decision in the plan | Written at |
|---|---|---|
| **Hosting and publication** | N2, N15 — Firebase Hosting in a project of its own; identity federation, no stored key | Stage 2.2 |
| **CI pipeline** | N2, N15 — the candidate and publishing workflows of §3.4 | Stage 2.2 |
| **Per-profile encryption** | N23 — the password becomes the key; the envelope of §3.6 | Stage 2.2a |
