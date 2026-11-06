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
| [ADR-0001](0001-encrypt-each-report-under-the-profile-password.md) | Encrypt each report under the password of the profiles it belongs to | 2026-11-06 | Per-profile encryption; N23, N64–N67 |
| [ADR-0002](0002-host-on-firebase-hosting-through-identity-federation.md) | Host the showcase on Firebase Hosting, reached only through identity federation | 2026-11-06 | Hosting and publication; N2 (hosting), N15 |
| [ADR-0003](0003-publish-through-a-trusted-workflow-on-main.md) | Publish through a trusted workflow on main, promoting the approved version ID | 2026-11-06 | CI pipeline; N2 (publishing), N74 |

## 3. Pending

Each row is an ADR the plan already calls for ([PLAN.md §7](../../PLAN.md#7-what-is-still-decided-at-the-right-moment)),
written when its component is born.

None at present: the three the plan called for so far are accepted. The next is added here when a
component the plan calls an ADR for comes near, or when a change needs one (§1).
