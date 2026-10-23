---
name: review
description: Prepares the hand-off of a delivery for review by another agent, or applies the findings of a review received. Use when finishing work another agent will review, when receiving review findings, or when the Owner asks to hand off or close a review.
---

# Hand a delivery over for review

> The Owner's operating questions — what runs by itself, how to revert, how to take it to another
> project — are in [`how_to_use.md`](how_to_use.md).

This project is worked by two agents: one **writes** and the other **reviews**, with different effort
budgets. This skill exists so that the hand-off between them does not depend on the memory of
either.

Ported from the `revisao` skill of
[mvp_eng_dados_1](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/.claude/skills/revisao/SKILL.md).
The dossier is `DOSSIER.md`: `REVIEW.md` at the root is the permanent record of the plan review, a
different thing.

## The rule that holds it all up

**A claim of measurement needs pasted command output.** What has no output is not a measurement — it
is an assumption, and it goes into the assumptions section. This is not rigour for its own sake: the
costliest defects of mvp_eng_dados_1 were not in the code but in premises about tools — PostgreSQL
16's `to_date` failing where leniency was assumed, Airbyte delivering an empty string as null, a
Makefile target printing "removed" when removal failed. None could be found by reading a diff.

## What the reviewer needs, and what they do not

They **do not need** you to redescribe the diff. `git` already gives it, and a second description
diverges from the code at the first change.

They **need** five things `git` does not give:

1. where to spend effort — what is declaration and what is derived;
2. what was actually run, with its literal output;
3. **what was not verified**;
4. which premises about the environment you assumed without confirming;
5. what must be up for their probes, and how to bring it up — otherwise the reviewer finds the
   databases down and does not know whether they may start them.

The third is the most valuable and the one you least want to write. If it comes out empty, the
dossier is wrong — no delivery verifies everything.

## Hand off

```bash
uv run python .claude/skills/review/dossier.py --since origin/main
```

When the delivery under review is **not** the tip — because later work has landed and is out of
scope —, pin the top:

```bash
uv run python .claude/skills/review/dossier.py --since <base> --until <sha of the delivery>
```

It collects what is mechanical — commits, files, and the output of the commands declared in
`commands.txt` — and leaves marked with `<<FILL IN>>` what only you know. Fill in the five marks:

| Section | What goes in |
|---|---|
| Review map | Which files are the **declaration** the others come from |
| Not verified | Every path you did not exercise, and every number you did not measure |
| Assumptions | What you assumed about a tool, database or service without confirming it in this delivery |
| Environment | What this review needs to find up, beyond the minimum, and in what state |
| Where I hesitated | Decisions that could have gone the other way, and why they went this one |

Then:

```bash
uv run python .claude/skills/review/dossier.py --verify
```

It refuses a dossier with a pending mark or with a failing check. A command that failed and is
expected to fail needs a written explanation, not an omission.

**Prefer an oracle to an argument.** Where a number can be delivered instead of an explanation,
deliver the number. A reviewer checks an oracle in seconds and argues over an argument for hours.

## Receive

The findings come back in the table at the end of `DOSSIER.md`, with a verdict per line: `blocking`,
`adjustment` or `observation`.

- **Blocking** stops everything else.
- **Adjustment** goes into the delivery.
- **Observation** becomes a note in the owning document of the subject, or a pending item if it
  needs a decision by the Owner (`CLAUDE.md` §4).

Fill in the *Status* column of each finding: what was done, or why not. A refused finding needs a
reason — silence is not an answer.

**An error in a generated file is fixed in the declaration**, never in the file. If the reviewer
pointed at the derived output, the fix is upstream and regeneration propagates it.

## Close

Delete `DOSSIER.md` in the commit that delivers what the review asked for, and say in the message
what came from it. The file is transient: it does not enter the documentation map of the README, and
its history is already in `git`.

## In another project

Only `commands.txt` is specific. The first time the skill runs in a new project, it creates the file
empty and says so — declare there the verification commands of that project, one per line. Without
them nothing is measured, and the dossier says so instead of pretending otherwise.
