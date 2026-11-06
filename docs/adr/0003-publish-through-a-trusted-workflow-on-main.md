# ADR-0003 — Publish through a trusted workflow on main, promoting the approved version ID

| Field | Information |
|---|---|
| Status | Accepted |
| Date | 2026-11-06 |
| Decider | The Owner |
| Resolves | The pending row "CI pipeline" of the [record](README.md#3-pending), and the plan's N2 (publishing on merge, a preview per PR), with N74 |
| Supersedes / superseded by | — |

## Context

"Updating means opening a PR" (N2, [PLAN §3.4](../../PLAN.md#34-the-architecture)): a PR shows its
result in a preview, and the merge publishes. But a PR's code is not trustworthy merely because its
branch is in this repository — it can change the checker, the build, `firebase.json` or the
workflows themselves (RV2-05, RV3-02) —, and in a personal repository a same-repository PR can grant
its own workflow `id-token: write` and obtain a GitHub OIDC token, which no setting forbids (N74).
What reaches live must be the bytes that were previewed and approved, not a rebuild nor whatever a
channel holds by then (RV3-03); and an obsolete run must never replace, nor crowd out, the current
one (PIPE-1-04).

The design was reviewed by Codex in four rounds on the plan and three on the code — 27 findings, six
blocking, among them a path traversal in the pinned artifact downloader and a token forwarded to
storage on a redirect, all applied —, and every one of its tests, T1 to T11, passed on GitHub and
Firebase on 2026-11-06 ([`docs/publishing_pipeline.md` §7](../publishing_pipeline.md#7-the-tests-of-the-stage),
`evidence/20261106/`).

## Alternatives considered

| Alternative | For | Against |
|---|---|---|
| **Three workflows: an untrusted candidate, a publisher that re-judges it with `main`'s code, and a promotion by version ID behind the Owner's approval** | The PR's code never holds a credential Google accepts; what is deployed is checked by `main`'s checker; live gets exactly the approved version; every rule is proved by a test | Three files and a release module to keep; a PR that touches the protected set gets no preview; the Owner approves every release |
| One workflow on `pull_request` that builds and deploys | The simplest | The PR controls the very code that holds the deploy credentials |
| `pull_request_target`, running the base's workflow with credentials on the PR | Credentials without trusting the PR's workflow | Checking out and building the PR's head under credentials is the known injection: its scripts and hooks run with them |
| Previews only of the Owner's own branches, by manual dispatch | No PR ever runs near a token | Ends "updating means opening a PR"; the narrower guarantee was chosen instead (N74) |
| Promotion by channel name, or a rebuild on merge | Fewer steps | The channel form takes whatever the channel deployed last, and a rebuild is not the approved bytes (RV3-03) |
| Serialisation by workflow-level concurrency | One line | A group holds one pending run, so an obsolete rerun could evict the current merge (PIPE-1-04); the queue is on the cloning job, behind `decide` |

## Decision

Publication runs through the three workflows of
[`docs/publishing_pipeline.md`](../publishing_pipeline.md) — `candidate` on `pull_request` with no
permission at all; `publish` on `workflow_run`, which runs only `main`'s code, admits only open
same-repository PRs outside the protected set, verifies the candidate as data and deploys it to the
PR's channel as `preview`; and `promote` on a push to `main`, whose `decide` binds the merge to its
authenticated preview record and whose `promote`, after the Owner's approval of `production`,
re-checks the tip, the channel and its margin and clones that `VERSION_ID` to live, one at a time
in a queue —, with a ruleset on `main` that requires the candidate's check and keeps the Owner's
bypass.

## Consequences

- **Positive:** a PR, from a fork or from this repository, cannot reach a credential Google accepts
  (T2, T3, T11); a tampered manifest or a planted clear file never leaves CI (T6); live is exactly
  the approved version, read back after the clone (T1); a preview advanced, a channel deleted or
  expired, a rerun or a late `decide` all stop with their reason and leave live unchanged (T4,
  T5, T10).
- **Negative:** a change to the pipeline itself — anything under `.github/`, `release/`,
  `src/bi_como_codigo/`, `firebase.json`, `Makefile`, `pyproject.toml`, `uv.lock` — is never
  previewed: it merges on its review alone, its `decide` ends red with the reason, and it is first
  exercised by the next content PR; every release waits for the Owner, the only reviewer, and only
  the newest merge can go live — an older one approved later refuses; an approval lasts less than
  its channel's 30 days; documents pushed directly use the Owner's bypass of the required check;
  past the 100 pending jobs GitHub's queue holds, a merge waits for a later one.
- **Continued operation on Google Cloud:** environment names, service accounts, provider, project
  and site come from repository variables (PIPE-1-07); another environment is another pair of
  GitHub environments, another set of variables and its own federation, with the same workflows.
- **Documents to update:** PLAN's N2 and §3.4, which point to this ADR;
  [`docs/publishing_pipeline.md`](../publishing_pipeline.md), which owns the pipeline, its tests and
  its removal; the record's index and the README's count.
