# The publishing pipeline — stage 2.2

> **What lives here:** how stage 2.2 builds the trusted path from a pull request to the live site —
> the files it adds to this repository, the resources it creates in Google Cloud and in GitHub, the
> candidate, publishing and promotion workflows job by job, the federation and its binding, how an
> approved preview becomes live by its version ID, the tests that prove each criterion of the
> stage, and how every resource is removed.
>
> **What does not:** why the path is shaped this way — the three gates and the trusted workflow are
> [PLAN §3.4](../PLAN.md#34-the-architecture), with N2 and N15 in
> [§1.2](../PLAN.md#12-the-decisions) —; the complete package-to-artifact gate with the decryption
> matrix and the mutation tests, which is stage 2.2b; the envelope (see
> [`encryption_envelope.md`](encryption_envelope.md)); the decision records of hosting and of the
> pipeline, born with this stage (pending in the [decision record](adr/README.md#3-pending)).

| Field | Information |
|---|---|
| Date | 2026-11-06 — revision 1 |
| Author | Claude Code, under the Owner's mandate for the night (N68) |
| Status | **Plan for review by Codex, before execution.** Nothing in it exists yet but the Firebase project `bi-como-codigo` and its default Hosting site, created on 2026-11-06 at the Owner's request. Its resources are created only after the review finds no blocking item (N70) |

**[measured]** has output behind it; **[planned]** is intent; **[assumed]** is a premise about a
tool or service that the stage proves or refutes (§9).

---

## 1. What exists, and what the stage adds

| Where | Today [measured, 2026-11-06] | What 2.2 adds [planned] |
|---|---|---|
| Firebase / Google Cloud | Project `bi-como-codigo`, Spark plan (billing off), default Hosting site `bi-como-codigo` → `bi-como-codigo.web.app`, nothing deployed | A workload identity pool and provider for GitHub, two service accounts with Hosting rights only, their bindings (§5) |
| GitHub repository | Public, `main` with no protection, no environments, Actions with default settings | Environments `preview` and `production`, a ruleset on `main`, Actions permissions read-only by default (§6) |
| This repository | No site, no workflow | `firebase.json`, the inclusion list, a fixture site, the release checker, three workflows (§2) |

The Google Cloud CLI's default project on this machine is another one (`analisador-de-risco`):
every command of this plan names `--project` explicitly, and none relies on the default.

---

## 2. The files

| Path | What it is | Changed only by |
|---|---|---|
| `.github/workflows/candidate.yml` | The candidate workflow (§3) | A reviewed PR; while it is in a PR, that PR gets no preview (§4.1) |
| `.github/workflows/publish.yml` | The publishing workflow (§4) | The same |
| `.github/workflows/promote.yml` | The promotion workflow (§4.4) | The same |
| `firebase.json` | Hosting configuration: the `deploy/` directory as public root, headers, no rewrites to functions | The same |
| `release/include.txt` | The inclusion list: the only paths that may enter `deploy/`, one glob per line | The same |
| `src/bi_como_codigo/release.py` | The release checker: builds `deploy/` from the inclusion list, writes the release record, and inspects the result (§4.2) | The same |
| `site/` | The fixture site of 2.2: one page and a package of harmless encrypted fixtures, sealed with the envelope over synthetic stand-ins | Any PR — it is the content under test |

The protected set — the three workflows, `firebase.json`, `release/`, `src/bi_como_codigo/` and the
`Makefile` — is declared once, in `release/protected.txt`, which is itself in it. Configuration —
project, site, pool, provider, service accounts — comes from repository **variables** of GitHub
(`FIREBASE_PROJECT`, `FIREBASE_SITE`, `WIF_PROVIDER`, `SA_PREVIEW`, `SA_LIVE`), never from the
workflow text, so that sandbox, qa and prod stay possible with other values (CLAUDE.md §5). No
secret is stored anywhere: federation needs none (N15).

Every third-party action is pinned to a full commit SHA, resolved at execution and written next
to its version tag in a comment; `firebase-tools` is pinned to an exact version with its
integrity hash through a lock file, and run through `npx --no-install` from that lock.

---

## 3. The candidate workflow (`pull_request`)

Runs the PR's own code, so it is given nothing:

```yaml
on: pull_request            # never pull_request_target
permissions: {}             # no token scope at all; no id-token
```

One job, no environment, no secret, no OIDC:

1. check out the PR head;
2. `make secrets test test-js docs-check` — the PR's own checks, as information. Not `make check`,
   which needs a checkout of eng_dados and the whole history; `docs-check` without `ENG_DADOS_DIR`
   lists the pinned links as not verified;
3. `python -m bi_como_codigo.release build` **at the PR's revision**: builds `deploy/` from the
   inclusion list and writes `candidate.json` — PR number, head SHA, base SHA;
4. upload `deploy/` and `candidate.json` as the artifact `candidate`, retention 7 days.

Nothing it produces is trusted: the publishing workflow rebuilds its judgement from scratch, with
`main`'s code, treating the artifact as data (§4.2). Step 3 exists so the PR's author sees the
result; the publishing workflow re-checks it, it does not believe it.

---

## 4. The publishing workflow (`workflow_run`)

```yaml
on:
  workflow_run:
    workflows: [candidate]
    types: [completed]
permissions: {}             # granted per job below
concurrency: { group: preview-${{ github.event.workflow_run.head_branch }}, cancel-in-progress: true }
```

`workflow_run` always runs the workflow file **as it is on the default branch**, with
`github.ref` = `refs/heads/main` [assumed, §9]: a PR cannot change what this workflow does.

### 4.1 Job `admit` — no credentials

`permissions: { actions: read, pull-requests: read }`. Stops the run, with a reason in the job
summary, unless every condition holds:

- the candidate run's `conclusion` is `success` and its `event` is `pull_request`;
- `head_repository.full_name` equals `github.repository` — **a fork's PR stops here**;
- the PR is open, its head SHA equals `workflow_run.head_sha`;
- the PR's changed files, read from the API, touch no path of `release/protected.txt` — **a PR that
  changes the checker, the workflows or `firebase.json` stops here**, and is merged, if at all,
  without a preview and without a live update; the next PR, built on the merged `main`, previews.

### 4.2 Job `verify` — no credentials

`permissions: { actions: read }`. With `main`'s checkout and `main`'s checker:

1. download the artifact `candidate` of that run **as data** — no script of it is executed, no
   hook, no `npm install`;
2. `python -m bi_como_codigo.release verify`: every file under the inclusion list and none outside
   it; only the media types the list allows; the fixture package validated by the envelope's
   strict manifest validator and opened for every profile through the whole matrix with the
   public passwords (the envelope's §6.4); and the **inspection by content** of PLAN §3.4 —
   every file, whatever its extension, searched for a Parquet magic outside an envelope, for the
   payload magic `BICP` outside an envelope, for raw key material from the package's own DEKs,
   and for source maps. In 2.2 the package is the fixture one; 2.2b completes the gate;
3. write `release.json`: PR, head SHA, the SHA-256 of every file of `deploy/` and of the whole
   (a canonical listing: sorted paths, one `sha256  path` line each), the package's `package_id`;
4. upload `deploy/` and `release.json` as the artifact `verified`.

A failure here uploads nothing to Hosting: the deploying job depends on this one.

### 4.3 Job `preview` — environment `preview`, credentials

`permissions: { id-token: write, checks: write, actions: read }`, `environment: preview`.

1. download `verified`; recompute its digests and compare with `release.json`;
2. authenticate through federation (`google-github-actions/auth`, with `workload_identity_provider`
   and `service_account: SA_PREVIEW`, `create_credentials_file: true`), which leaves Application
   Default Credentials for `firebase-tools` [assumed, §9];
3. `firebase hosting:channel:deploy pr-<n> --expires 7d --project … --json`;
4. read the channel back through the Hosting REST API (`sites/{site}/channels/pr-<n>`): its
   current release's version name, `sites/{site}/versions/{VERSION_ID}`;
5. list that version's files (`versions/{VERSION_ID}/files`) and compare their hashes with what
   was uploaded [assumed: the API gives the hash of the gzipped content, the CLI's upload hash],
   so the version is the verified artifact and nothing else;
6. record the result as a **check run** named `preview-release` on the PR's head SHA, created by
   this workflow's token: version ID, channel, the canonical digest of `release.json`, the
   preview URL. A check run is written only by GitHub Apps with `checks: write` — a PR comment,
   which anyone can edit, is not the record.

### 4.4 The promotion workflow (`push` to `main`)

```yaml
on: { push: { branches: [main] } }
permissions: {}
concurrency: { group: promote, cancel-in-progress: false }   # one promotion at a time
```

Job `decide`, no credentials, `permissions: { contents: read, checks: read, pull-requests: read }`.
It promotes nothing unless every condition holds; otherwise it ends green with "nothing to
promote", or red with the reason:

1. `github.sha` is **the current tip of `main`** (`git ls-remote`): a rerun of an older run, or a
   run overtaken by a later merge, stops — the later merge is the one that may promote;
2. the push is the merge of exactly one PR (`commits/{sha}/pulls`), merged, from this repository;
3. that PR's head SHA has a `preview-release` check run created by **this repository's
   `github-actions` app** and by the `publish` workflow (the check run's `app` and its
   `details_url` naming the run), concluded `success`;
4. the tree of the merge, restricted to the inclusion list, equals the tree of the PR's head for
   the same paths (`git diff --quiet <head> <merge> -- <included paths>`): what was previewed is
   what was merged. A merge that changed included content — a conflict resolution, a squash of a
   later commit — needs a new preview and a new approval;
5. the channel `pr-<n>` still points at the recorded `VERSION_ID`: **a preview advanced after
   approval** — a new push to the PR, re-deployed — no longer matches the recorded version and
   stops here;
6. the live channel does not already point at that version (idempotent: a rerun after success
   promotes nothing).

Job `promote`, `environment: production` — the Owner approves it in GitHub's interface, seeing the
version ID and the digest in the summary `decide` wrote — `permissions: { id-token: write }`:

1. authenticate as `SA_LIVE`;
2. re-check conditions 1 and 5 (time passed while waiting for the approval);
3. `firebase hosting:clone {site}@{VERSION_ID} {site}:live` — the CLI reads `<site>@<version>`; the `<site>:@<version>` of PLAN §3.4 would be read as a channel named `@<version>` and fail (M50) — within one site, live then points at
   that same version, the same bytes, with no rebuild;
4. read `sites/{site}/channels/live` back: its release's version is `VERSION_ID`, or the job fails.

---

## 5. The federation

```text
gcloud iam workload-identity-pools create github --project=bi-como-codigo --location=global
gcloud iam workload-identity-pools providers create-oidc github-actions \
  --project=bi-como-codigo --location=global --workload-identity-pool=github \
  --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping=google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.workflow_ref=assertion.workflow_ref,attribute.ref=assertion.ref,attribute.environment=assertion.environment \
  --attribute-condition="assertion.repository=='alencardoug/bi-como-codigo' && assertion.ref=='refs/heads/main' && (assertion.workflow_ref=='alencardoug/bi-como-codigo/.github/workflows/publish.yml@refs/heads/main' || assertion.workflow_ref=='alencardoug/bi-como-codigo/.github/workflows/promote.yml@refs/heads/main')"
```

The condition is evaluated by Google's token exchange before anything else: a token from another
repository, another ref or another workflow file is refused there (RV4-01: `workflow_ref`, since
the publishing workflow is called directly, not as a reusable one).

Two service accounts, one per environment, each with **Firebase Hosting Admin** on the project and
nothing else, each impersonable only by the identities of its own environment:

| Service account | Role on the project | Who may impersonate it (`roles/iam.workloadIdentityUser`) |
|---|---|---|
| `hosting-preview@bi-como-codigo.iam.gserviceaccount.com` | `roles/firebasehosting.admin` | `principalSet://iam.googleapis.com/projects/<number>/locations/global/workloadIdentityPools/github/attribute.environment/preview` |
| `hosting-live@bi-como-codigo.iam.gserviceaccount.com` | `roles/firebasehosting.admin` | `principalSet://…/attribute.environment/production` |

So the preview job cannot promote to live with its own identity unless Hosting Admin allows it —
it does: the role covers every channel. The separation that holds is the environment's: the live
identity is reachable only from a job in `production`, which only the Owner's approval starts. A
narrower custom role for previews — channel deploys without `releases.create` on `live` — is not
offered by Hosting's permissions [assumed, §9]; if it is, 2.2 uses it.

APIs enabled, all free: `iam`, `iamcredentials`, `sts`, `firebasehosting`.

---

## 6. GitHub settings

- **Environment `preview`**: deployment branches limited to `main` — the `workflow_run` and `push`
  jobs run on `main`; no reviewer.
- **Environment `production`**: deployment branches limited to `main`; required reviewer, the Owner;
  "prevent self-review" off, since the Owner is the only reviewer and approves runs a workflow
  started by their own merge.
- **Actions**: default `GITHUB_TOKEN` permissions read-only; "allow GitHub Actions to create and
  approve pull requests" off; workflows from fork PRs need approval for first-time contributors
  (the default) — they would get no credentials anyway (§4.1).
- **A ruleset on `main`**: no deletion, no force push; PRs must pass the candidate's job. The Owner
  keeps the bypass, so that documents still reach `main` directly as today: a direct push carries no
  previewed PR, so promotion finds nothing to promote (§4.4, condition 2). Claude Code's choice under
  N68 — the alternative, PRs required for everything, changes how the Owner works and is the
  Owner's to take.

---

## 7. The tests of the stage

Each criterion of [PLAN §6.2](../PLAN.md#62-the-stages), stage 2.2, with how it is executed and
what counts as passing. All of them run on the fixture site; none touches report data.

| # | Criterion | How | Passes when |
|---|---|---|---|
| T1 | A test PR gets a preview, and its promotion is the same version ID | A PR changing `site/index.html`; merge; approve `production` | The check run's `VERSION_ID` equals the live channel's version after promotion, read from the API |
| T2 | A fork's PR gets no credentials | A PR from a fork — of an organisation of the Owner's, created on the web (N70); without it, a `workflow_run` payload with another `head_repository` replayed against `admit` locally, the limit declared | `admit` stops; `preview` never starts; the run's log has no token request |
| T3 | A same-repository PR changing the checker or `firebase.json` gets no preview and no live update | Two PRs: one touching `src/bi_como_codigo/release.py`, one `firebase.json`; merge one of them | `admit` stops on both; after the merge, `decide` finds no `preview-release` and promotes nothing |
| T4 | A preview advanced after approval does not replace the release | A PR previewed and merged; while `promote` waits for the Owner's approval, the channel `pr-<n>` is re-deployed by hand from the Owner's machine with other content — no workflow can do it once the PR is closed (§4.1) —; then the Owner approves | `promote` stops at its step 2: the channel's version is no longer the recorded one; live unchanged |
| T5 | A rerun of an older job does not replace the current release | Two PRs merged one after the other, both promoted; then "re-run" the first one's promotion | `decide` stops on condition 1: its SHA is not the tip |
| T6 | A tampered manifest and a planted clear file are rejected, and nothing is uploaded | Two PRs: one with a manifest whose `sha256` of one envelope is wrong; one with a `.txt` holding a Parquet's bytes under the inclusion list | `verify` fails; `preview` never starts; the channel does not exist |
| T7 | Federation accepts the publishing workflow on `main` in its environment | T1 itself | The token exchange succeeds |
| T8 | … and rejects another workflow, another ref and another environment | A throwaway `federation-probe.yml` with `workflow_dispatch`, run (a) on `main` in `preview`, (b) from a branch, (c) with `environment: production` but `SA_PREVIEW`; then deleted | (a) and (b) refused by the provider's condition; (c) refused by the binding; each error text kept as evidence |
| T9 | No stored key | `gcloud iam service-accounts keys list --managed-by=user` for both accounts; the repository's and environments' secrets listed | Both lists empty |

**What "approval" is here.** GitHub does not let the author of a PR approve it, and the Owner is
the only reviewer: the approval that binds a version is the Owner's approval of the `production`
job, given while its summary shows the `VERSION_ID` and the digest. A commit pushed to an open PR
re-previews it and records a new check run on the new head; what is merged and approved is that
head's version. The criterion "a changed candidate needs a new preview and a new approval" holds
because both conditions are re-checked after the approval (§4.4, `promote` step 2).

---

## 8. Removing it

Every resource is listed with its removal, in the order that leaves nothing half-bound:

```text
gcloud iam service-accounts delete hosting-live@bi-como-codigo.iam.gserviceaccount.com --project=bi-como-codigo
gcloud iam service-accounts delete hosting-preview@bi-como-codigo.iam.gserviceaccount.com --project=bi-como-codigo
gcloud iam workload-identity-pools providers delete github-actions --workload-identity-pool=github --location=global --project=bi-como-codigo
gcloud iam workload-identity-pools delete github --location=global --project=bi-como-codigo
gh api -X DELETE repos/alencardoug/bi-como-codigo/environments/production
gh api -X DELETE repos/alencardoug/bi-como-codigo/environments/preview
gh api -X DELETE repos/alencardoug/bi-como-codigo/rulesets/<id>
firebase hosting:channel:delete pr-<n> --project bi-como-codigo   # each preview channel left
```

A deleted pool stays reserved for 30 days under its name [assumed]: re-creating it in that window
means undeleting it.

---

## 9. Not verified, and assumptions

**Not verified** — each is proved or refuted by a test of §7, and the result recorded:

- that `firebase-tools` deploys to a channel and clones by `@VERSION_ID` with Application Default
  Credentials from federation, with no service-account key (PLAN §9) — T1, T7;
- that a `workflow_run` job's OIDC token carries `ref` = `refs/heads/main` and the `workflow_ref`
  of `publish.yml` on `main`, and an environment job's carries `environment` — T7, T8;
- that the Hosting API's file hashes of a version can be compared with the verified artifact (§4.3,
  step 5) — if they cannot, the comparison is the version's file count and paths, declared weaker;
- that no Hosting permission separates channel deploys from releases to `live` (§5);
- that the Spark plan allows the IAM and STS APIs with billing off;
- what the fork test can prove without a second owner (T2).

**Assumptions:**

- GitHub keeps secrets and OIDC away from fork PRs' `pull_request` runs, as documented; the design
  does not depend on it — the candidate workflow has `permissions: {}` and nothing to steal;
- a check run created with the workflow's `GITHUB_TOKEN` is attributed to the `github-actions` app
  and cannot be created by a PR's code, which runs with `permissions: {}`;
- Hosting keeps a channel's previous versions available to `hosting:clone` by version ID for as
  long as the promotion takes.
