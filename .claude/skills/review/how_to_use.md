# How to use the `review` skill

> **What lives here:** the Owner's operating questions — what runs by itself, what to type, how to
> undo, how to take it to another project.
>
> **What does not:** the procedure the agents follow, in the [`SKILL.md`](SKILL.md) next to this
> file. One is for a person, the other for an agent.

## 1. What it is for

The project is worked by **two** agents with different effort budgets: one writes, the other
reviews. The skill makes the hand-off between them stop depending on the memory of either.

It produces a `DOSSIER.md` at the root with five things `git` does **not** give:

- where the reviewer should spend effort — what is declaration and what is derived;
- what was run, with the **literal** output of the commands;
- what was **not** verified;
- which premises about the environment the author assumed without confirming;
- what must be up for the review, and how to bring it up without touching data.

The diff is not repeated: the reviewer reads `git`.

`DOSSIER.md` is not `REVIEW.md`. `REVIEW.md` is the permanent record of the plan review; the dossier
is transient and leaves with the commit that closes it.

## 2. What happens if you do nothing

**Nothing.** No hook is configured, nothing runs in the background, and the tool uses only the
Python standard library. The files stay inert until someone invokes the skill.

A skill is not installed: it is discovered from the `.claude/skills/` directory, and exists the
moment the file is written.

**One exception:** Codex reads `AGENTS.md` by default, and it has a section on this hand-off. Those
are instructions, not execution. Claude Code reads `CLAUDE.md`, not `AGENTS.md`.

### A dossier left at the root does not make anyone a reviewer

A `DOSSIER.md` at the root is a strong signal, because it looks like a task addressed to whoever
opens the project. So both files say explicitly that **the role is not fixed**: it comes from your
request, and the dossier is an open invitation, not an order.

## 3. How to use it

### Hand a delivery over for review

Ask the agent that wrote the code: **"prepare the review"**, or type `/review`. It runs the tool,
which collects the mechanical part, and fills in the sections only the author knows:

```bash
uv run python .claude/skills/review/dossier.py --since origin/main
uv run python .claude/skills/review/dossier.py --verify
```

`--verify` refuses the dossier while any author section is blank, or while any verification command
fails with no explanation.

### Receive the review

The reviewer writes the findings in the table at the end of `DOSSIER.md`, one per line, with a
verdict: `blocking`, `adjustment` or `observation`.

### Close

Ask the agent that wrote: **"apply the findings"**. It fills in the *Status* column of each finding —
what was done, or why not — and deletes `DOSSIER.md` in the delivering commit. A refused finding
needs a written reason.

## 4. How to revert

Revert the commits of the skill, newest first:

```bash
git log --oneline -- .claude/skills/review AGENTS.md DOSSIER.md
```

Or remove the places explicitly — there is no other:

```bash
rm -rf .claude/skills/review DOSSIER.md
```

and take the hand-off section out of `AGENTS.md`. There is no state outside the repository.

## 5. How to install it in another project

Copy **one directory** and edit **one file**: `commands.txt`, with the verification commands of that
project. Two caveats:

**The path matters.** `dossier.py` finds the repository root by counting three levels above itself,
so it must stay exactly in `.claude/skills/review/`.

**The environment table is this project's.** Section 6 of the dossier names this repository's
environment — the eng_dados checkout and databases. Another project rewrites that table in
`dossier.py`.
