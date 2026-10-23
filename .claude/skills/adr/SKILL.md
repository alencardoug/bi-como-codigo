---
name: adr
description: Records a decision of the Owner as an accepted ADR and closes the transaction in the index — docs/adr/README.md, the README and the documents the decision affects. Use when the Owner settles a decision, when a component the plan calls an ADR for is born, or when a change needs an ADR and the work must stop.
---

# Record a decision in an ADR

An ADR is a **transaction across several files**. Writing only the ADR file leaves the index and the
count diverging.

Ported from the `adr` skill of
[mvp_eng_dados_1](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/.claude/skills/adr/SKILL.md),
with this repository's paths.

## First of all: who decides

Claude Code **does not decide what calls for an ADR** (`CLAUDE.md` §4). If you got here because you
ran into a choice of tool, component or data treatment that nobody decided, the procedure is the
reverse of this one: **stop**, add the question as a pending row in §3 of
[`docs/adr/README.md`](../../../docs/adr/README.md), and take it to the Owner. Do not implement.

Go on only when the Owner has said **which** option they chose — or when the plan already records
the decision (N1–N25, O1–O8) and the ADR is the one §3 says is written at this stage.

## 1. Gather

- Which pending row of §3 is being resolved, and which decision of the plan it records, if any.
- The choice, in the Owner's words or the plan's.
- The next free number: `ls docs/adr/ | grep -E '^[0-9]{4}-' | tail -1`.

## 2. Write the ADR

`docs/adr/NNNN-title-in-kebab-case.md`, from [`0000-template.md`](../../../docs/adr/0000-template.md).
Every section is mandatory, in English (`CLAUDE.md` §2).

Three content rules worth keeping:

- The **Context** records what was wrong or open before — including the vocabulary and proposals
  that were replaced. That is the ADR doing its job, not inconsistency.
- The **Alternatives** record why the refused ones were refused. An empty "Against" cell is a sign
  the alternative was invented to fill the table.
- The **negative consequences** are what separate an ADR from an announcement. If no cost was
  accepted, there was probably no decision.

## 3. Close the transaction

In the same delivery, with no exception:

| File | What changes |
|---|---|
| `docs/adr/README.md` | A new row in §2 (and "None yet." leaves with the first); the resolved row **leaves** §3 |
| `README.md` | The count on the line of `docs/adr/`: `N accepted, M pending` |
| `PLAN.md` | Where the plan states the decision, a link to the ADR |
| Each document in the ADR's **Documents to update** | The content |

Prefer a verified replacement — one that fails if the target is not unique — to a loose `sed`. A
target that matches zero or two times is a silent defect.

## 4. Verify

```bash
make check
```

It runs `.claude/skills/adr/verify.py` — numbering, the index against the files, resolved rows still
pending and the README count — and the documentation check, which owns links and anchors.

## 5. Commit

One ADR per subject, in English:

```
docs: record ADR-NNNN — <title>
```
