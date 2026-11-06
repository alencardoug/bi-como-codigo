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
| Date | 2026-11-06 — revision 2: round 1 of Codex's review applied — Hosting reads moved to the authenticated job (PIPE-1-01); the record authenticated by its run, all of `.github/` protected, and the guarantee narrowed by the Owner to no credential Google accepts (PIPE-1-02, N74); T8 in two layers (PIPE-1-03); no workflow-level concurrency (PIPE-1-04); T4b (PIPE-1-05); exact served bytes, no fallback (PIPE-1-06); environment names as variables (PIPE-1-07); the approval's lifetime (PIPE-1-08). Revision 1 is `88d4c33` |
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
| `.github/workflows/candidate.yml` | The candidate workflow (§3) | A reviewed PR; a PR that touches anything under `.github/` gets no preview (§4.1) |
| `.github/workflows/publish.yml` | The publishing workflow (§4) | The same |
| `.github/workflows/promote.yml` | The promotion workflow (§4.4) | The same |
| `firebase.json` | Hosting configuration: the `deploy/` directory as public root, headers, no rewrites to functions | The same |
| `release/include.txt` | The inclusion list: the only paths that may enter `deploy/`, one glob per line | The same |
| `src/bi_como_codigo/release.py` | The release checker: builds `deploy/` from the inclusion list, writes the release record, and inspects the result (§4.2) | The same |
| `site/` | The fixture site of 2.2: one page and a package of harmless encrypted fixtures, sealed with the envelope over synthetic stand-ins | Any PR — it is the content under test |

The protected set — **everything under `.github/`**, so a PR that adds a workflow is as protected
as one that edits one (PIPE-1-02), `firebase.json`, `release/`, `src/bi_como_codigo/` and the
`Makefile` — is declared once, in `release/protected.txt`, which is itself in it. Configuration —
project, site, provider, service accounts **and the names of the two GitHub environments** — comes
from repository **variables** of GitHub (`FIREBASE_PROJECT`, `FIREBASE_SITE`, `WIF_PROVIDER`,
`SA_PREVIEW`, `SA_LIVE`, `ENV_PREVIEW`, `ENV_PRODUCTION`), never from the workflow text: a job says
`environment: ${{ vars.ENV_PREVIEW }}`, and the bindings of §5 are written by
`release/setup.sh` from the same values (PIPE-1-07), so that sandbox, qa and prod stay possible
with other values (CLAUDE.md §5). The names in this document are the values of this installation.
No secret is stored anywhere: federation needs none (N15).

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

**What this does and does not guarantee** (PIPE-1-02, N74). The `permissions` block is part of
the PR's own code: a same-repository PR can edit it, or add a workflow of its own, and obtain a
GitHub OIDC token, and GitHub offers a personal repository no setting that forbids it. What the
pipeline guarantees is narrower and true: **a PR's code can obtain no credential that Google
accepts**. Its token's `ref` is `refs/pull/<n>/merge` or a branch, and its `workflow_ref` names a
file at that ref, so the provider's condition (§5) refuses the exchange; T11 proves it. And the PR
gets no preview and no live update (§4.1), so whatever it ran published nothing. A fork's PR gets
no OIDC token at all from GitHub.

One job, no environment, no secret, and no token requested:

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

`permissions: { id-token: write, actions: read }`, `environment: ${{ vars.ENV_PREVIEW }}`.

1. download `verified`; recompute its digests and compare with `release.json`;
2. authenticate through federation (`google-github-actions/auth`, with `workload_identity_provider`
   and `service_account: SA_PREVIEW`, `create_credentials_file: true`), which leaves Application
   Default Credentials for `firebase-tools` [assumed, §9];
3. `firebase hosting:channel:deploy pr-<n> --expires 30d --project … --json` — 30 days, the
   maximum, and the deadline of the approval (§4.5);
4. read the channel back through the Hosting REST API (`sites/{site}/channels/pr-<n>`): its
   current release's version name, `sites/{site}/versions/{VERSION_ID}`;
5. **prove the version is the verified artifact, exactly, or fail** (PIPE-1-06): list every page
   of `versions/{VERSION_ID}/files` and require its set of paths, all `ACTIVE`, to equal the
   artifact's exactly; then fetch every path from the channel's URL, decoding any transfer
   encoding, and require its bytes to equal the artifact's file, by SHA-256. No fallback: a
   representation the check cannot read fails the job. Comparing served bytes avoids reproducing
   the CLI's gzip, whose hash is of its own level-9 stream;
6. upload `release-record.json` as the artifact `release-record` **of this run**: PR number, head
   SHA, candidate run ID, `VERSION_ID`, channel, its expiry, and the canonical digest of
   `release.json`. A PR comment, or a check run, is not the record: both are writable by any
   workflow with the right scope, a PR's included (PIPE-1-02). An artifact belongs to the run that
   uploaded it, and the promotion finds that run by facts GitHub sets on the server (§4.4).

### 4.4 The promotion workflow (`push` to `main`)

```yaml
on: { push: { branches: [main] } }
permissions: {}
```

No workflow-level concurrency: a group there would let an obsolete rerun take the single pending
slot from the current merge before anything checked it (PIPE-1-04). Serialisation is on the job
that clones, and only runs that `decide` has admitted reach it.

**Job `decide`** — GitHub only, no Google credential, `permissions: { contents: read,
actions: read, pull-requests: read }`. It promotes nothing unless every condition holds; otherwise
it ends green with "nothing to promote", or red with the reason:

1. `github.sha` is **the current tip of `main`** (`git ls-remote`): a rerun of an older run, or a
   run overtaken by a later merge, stops here — before it can queue for `promote`;
2. the push is the merge of exactly one PR (`commits/{sha}/pulls`), merged, from this repository;
3. **the authenticated record** (PIPE-1-02): among the runs of the publishing workflow — found by
   the workflow's ID on `main`, and each run's `path` equal to `.github/workflows/publish.yml`,
   `event` equal to `workflow_run`, `head_branch` equal to `main`, all set by GitHub —, the latest
   successful one whose triggering candidate run is for that PR's **head SHA**; its artifact
   `release-record`, downloaded by that run's ID, names the same PR, head SHA and candidate run. A
   check run or a URL a PR could write does not enter;
4. the tree of the merge, restricted to the inclusion list, equals the tree of the PR's head for
   the same paths (`git diff --quiet <head> <merge> -- <included paths>`): what was previewed is
   what was merged. A merge that changed included content — a conflict resolution, a squash of a
   later commit — needs a new preview and a new approval;
5. the record's channel expiry is more than one day away (§4.5).

Its summary — the one the Owner reads before approving — shows the PR, the `VERSION_ID`, the
preview URL, the canonical digest and the expiry. It reads nothing from Hosting: it has no Google
credential, and Hosting's control-plane reads require one (PIPE-1-01).

**Job `promote`** — `needs: decide`, `environment: ${{ vars.ENV_PRODUCTION }}` — the Owner approves
it in GitHub's interface —, `permissions: { id-token: write }`,
`concurrency: { group: promote, cancel-in-progress: false }`, one clone at a time:

1. authenticate as `SA_LIVE`;
2. re-check condition 1 — time passed while waiting for the approval;
3. read `sites/{site}/channels/pr-<n>`: its release's version is still the recorded `VERSION_ID`
   — **a preview advanced while the approval waited stops here**; and the version exists, not
   deleted with an expired channel (§4.5);
4. read `sites/{site}/channels/live`: if it already serves `VERSION_ID`, end — nothing to do (a
   rerun after success); an empty live channel, on the first release, is not an error;
5. `python -m bi_como_codigo.release promote --version VERSION_ID`, which runs exactly
   `firebase hosting:clone {site}@{VERSION_ID} {site}:live` — the CLI reads `<site>@<version>`
   (M50); within one site, live then points at that same version, the same bytes, with no rebuild.
   The command is built in one function, tested against a stand-in CLI (T4b), never with the
   channel form;
6. read `sites/{site}/channels/live` back: its release's version is `VERSION_ID`, or the job fails
   — if the channel had moved between steps 3 and 5 and the clone had taken the channel, this is
   where it shows.

### 4.5 How long an approval lasts

A preview channel lives 30 days (§4.3); when it expires, Firebase deletes the channel, its
releases and the versions no other release references, within a day (PIPE-1-08). So an approval
is valid only while the record's expiry is more than a day away (`decide`, condition 5) and the
version exists (`promote`, step 3). Past that, the recovery is a new preview — re-run the
candidate workflow on the PR, or push to it — and a new approval of the new version. A new build
or the channel's latest version is never substituted under the old approval.

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

After creating them, `release/setup.sh check` reads both policies back (`gcloud iam
service-accounts get-iam-policy`) and requires each to hold **exactly** its one member above, and
the provider's condition to be exactly the one written: the binding oracle of T8.

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
| T1 | A test PR gets a preview, and its promotion is the same version ID | A PR changing `site/index.html`; merge; approve `production` | The authenticated record's `VERSION_ID` equals the live channel's version after promotion, read from the API; §4.3 step 5 passed on the real fixture |
| T2 | A fork's PR gets no credentials | A PR from a fork — of an organisation of the Owner's, created on the web (N70); without it, a `workflow_run` payload with another `head_repository` replayed against `admit` locally, the limit declared | `admit` stops; `preview` never starts; the run's log has no token request |
| T3 | A same-repository PR changing the checker, the workflows or `firebase.json` gets no preview and no live update | PRs touching `src/bi_como_codigo/release.py`, `firebase.json`, the candidate's `permissions`, and one adding a fourth workflow; then a PR previewed at H1 that adds, at H2, a workflow writing a counterfeit record and check run copying H1's version (PIPE-1-02); merge one of them | `admit` stops on every one; after the merge, `decide` finds no authenticated record for the merged head and promotes nothing |
| T4 | A preview advanced after approval does not replace the release | A PR previewed and merged; while `promote` waits for the Owner's approval, the channel `pr-<n>` is re-deployed by hand from the Owner's machine with other content — no workflow can do it once the PR is closed (§4.1) —; then the Owner approves | `promote` stops at its step 3: the channel's version is no longer the recorded one; live unchanged |
| T4b | The clone takes the version, never the channel (PIPE-1-05) | A unit test of `release.py promote` against a stand-in `firebase` that records its arguments; and the same test against a copy whose command uses `{site}:pr-<n>` | The real command is exactly `hosting:clone {site}@{VERSION_ID} {site}:live`; the channel-form copy fails the test. The race between step 3 and the clone is not reproduced in CI: step 6's read-back is what catches it, and the stand-in shows the command could not have taken the channel |
| T5 | A rerun of an older job does not replace the current release, and cannot crowd out the current one | Two PRs merged one after the other, both promoted, then the first one's promotion re-run; and the schedule of PIPE-1-04 — A waiting for approval, B merged and waiting, C, an older run, re-run | The re-run stops at `decide`'s condition 1; in the schedule, C stops at `decide` without queuing, B reaches `promote` and publishes after its approval, A stops at its step 2, and at most one clone runs at a time |
| T6 | A tampered manifest and a planted clear file are rejected, and nothing is uploaded | Two PRs: one with a manifest whose `sha256` of one envelope is wrong; one with a `.txt` holding a Parquet's bytes under the inclusion list | `verify` fails; `preview` never starts; the channel does not exist |
| T7 | Federation accepts the publishing workflow on `main` in its environment | T1 itself | The token exchange succeeds |
| T8 | … and rejects another workflow, another ref and another environment | **Two layers, tested apart** (PIPE-1-03). *The provider's condition:* a throwaway `federation-probe.yml` on `main` and the same file on a branch, both exchanging their token at Google's STS directly, with no environment — so GitHub's environment branch policy cannot be what refuses. *The bindings:* a temporary probe job added to `promote.yml` on `main` — an allowlisted workflow and ref, through a reviewed PR —, in each environment, exchanging its token at STS and then asking IAM Credentials for an access token of **each** service account: `preview` → `SA_PREVIEW` (control) and `preview` → `SA_LIVE`, `production` → `SA_LIVE` (control) and `production` → `SA_PREVIEW`. Then the probe file and the probe job are removed by another PR, and `release/setup.sh check` re-reads the policies | The condition refuses both probes at STS, with the error kept. In the bindings, STS succeeds for every probe job and IAM Credentials succeeds only for the two controls; the two cross attempts fail with a permission error, kept. A local copy of the expected policies with a pool-wide member makes `setup.sh check` fail — tried on the JSON, never installed in Google Cloud |
| T10 | An approval past its version's life does not promote (PIPE-1-08) | A PR previewed and merged; before approving, its channel is deleted by hand (`hosting:channel:delete`), which schedules its version for deletion; then the Owner approves | `promote` stops at step 3 — the channel or the version is gone —, with the recovery of §4.5 in the error; live unchanged. Then a new preview and approval promote normally |
| T11 | A PR's own token is refused by Google (N74) | A same-repository PR whose candidate workflow is edited to `permissions: { id-token: write }` and tries the STS exchange; the PR gets no preview by §4.1 | GitHub issues the JWT; Google's STS refuses it on the provider's condition, error kept; nothing deployed |
| T9 | No stored key | `gcloud iam service-accounts keys list --managed-by=user` for both accounts; the repository's and environments' secrets listed | Both lists empty |

**What "approval" is here.** GitHub does not let the author of a PR approve it, and the Owner is
the only reviewer: the approval that binds a version is the Owner's approval of the `production`
job, given while its summary shows the `VERSION_ID` and the digest. A commit pushed to an open PR
re-previews it and uploads a new record for the new head; what is merged and approved is that
head's version. The criterion "a changed candidate needs a new preview and a new approval" holds
because the tip and the channel's version are re-checked after the approval (§4.4, `promote` steps
2 and 3).

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
- that the channel's URL serves each file's bytes exactly as uploaded, once any transfer encoding
  is decoded (§4.3, step 5) — if it does not, the job fails; there is no weaker comparison;
- that no Hosting permission separates channel deploys from releases to `live` (§5);
- that the Spark plan allows the IAM and STS APIs with billing off;
- what the fork test can prove without a second owner (T2).

**Assumptions:**

- GitHub keeps secrets and OIDC away from fork PRs' `pull_request` runs, as documented; the design
  does not depend on it — a same-repository PR can get a JWT, and Google refuses it (N74, T11);
- that a run's `path`, `event` and `head_branch`, and the artifacts listed for a run ID, are set by
  GitHub and cannot be written by a workflow (§4.4, condition 3) — T3's counterfeit proves the
  promotion ignores what a PR can write.

**Corrected** from revision 1: Hosting does not keep a version for as long as a promotion takes —
an expired channel's versions are deleted within a day (§4.5).
