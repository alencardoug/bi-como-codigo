# bi-como-codigo

A showcase of **BI as code** over the synthetic retail warehouse built in
[mvp_eng_dados_1](https://github.com/alencardoug/mvp_eng_dados_1): reports for its sixteen business
questions, a reading portal for its data governance, the governance of the project itself, and
least-privilege access by profile — with no BI licence and no database server.

## Objective

Show that the analytical layer of a data project can be built, reviewed and published like code: the
reports read the consumption views of mvp_eng_dados_1 and never recompute a metric; the governance
that visitors read is generated from the declarations of that project; and access by profile is
demonstrated by encryption in a static site — access scoped to the key supplied, not authentication
([PLAN.md §3.2](PLAN.md#32-the-showcase)) —, with every change going through a reviewed pull request.
The plan says what gets built, in what order and why ([PLAN.md](PLAN.md)).

**Status: stage 2.2a of the plan — the encryption envelope.** Part I, the maintenance release of
mvp_eng_dados_1, is done; here, the envelope that gives each profile its reports is implemented and
in review; no report, portal or publication exists yet. The data is synthetic end to end, and all of it comes from mvp_eng_dados_1.

## Map

| Where | What it is |
|---|---|
| [`PLAN.md`](PLAN.md) | The development plan: what gets built, the architecture, the stages with the effort of each, and the Owner's decisions |
| [`REVIEW.md`](REVIEW.md) | The record of the plan review: Codex's original proposal, Claude Code's review of it, and Codex's rounds 2 to 5 over the plan |
| [`CLAUDE.md`](CLAUDE.md) | How this repository is worked on — language, commits, the gate, assisted development and the rules never broken |
| [`AGENTS.md`](AGENTS.md) | The entry point for any agent, pointing at `CLAUDE.md` |
| [`docs/adr/`](docs/adr/README.md) | The decision record: 1 accepted, 2 pending |
| [`docs/encryption_envelope.md`](docs/encryption_envelope.md) | The encryption envelope of the per-profile access, format version 1: the bytes, the reader and the producer, the bounds and the oracles (stage 2.2a) |
| [`docs/publishing_pipeline.md`](docs/publishing_pipeline.md) | The publishing pipeline of stage 2.2: the candidate, publishing and promotion workflows, the federation to Google Cloud, the environments and the tests of each criterion — a plan in review |
| [`docs/public_by_design.yml`](docs/public_by_design.yml) | The two demo passwords, public by design (N22), registered for the secrets review |
| [`docs/regeneration_runbook.md`](docs/regeneration_runbook.md) | The runbook of stage 1.4: how stage 1.6 regenerates eng_dados v1.1.0 — every checkpoint with a command, an oracle and a restart point, the rollback cut and the recovery package —, and the record of its review by Codex |
| [`evidence/`](evidence/20261022/README.md) | The read-only probes behind every measurement in the plan, with their literal outputs — [M1–M18](evidence/20261022/README.md) and [M19–M26](evidence/20261023/README.md) |
| [`.claude/skills/`](.claude/skills/review/SKILL.md) | The `review` and `adr` skills: the hand-off between agents, and the decision record as one transaction |
| [`web/envelope.mjs`](web/envelope.mjs) | The envelope's reader for the browser: WebCrypto only, the same file in the tests and in the site |
| `src/`, `tests/`, `Makefile` | The checks of this repository, the envelope's producer and Python reader, their tests and the envelope's vectors and cases, run by `make check` |

## Checking the repository

`make check` is the gate before every commit. It needs [uv](https://docs.astral.sh/uv/), Node 20 or
later for the envelope's JavaScript reader, and a local checkout of mvp_eng_dados_1, named by
`ENG_DADOS_DIR`, to verify the pinned links into it.

```bash
make sync
ENG_DADOS_DIR=/path/to/mvp_eng_dados_1 make check
```

`make help` lists the other targets.
