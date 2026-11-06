# ADR-0002 — Host the showcase on Firebase Hosting, reached only through identity federation

| Field | Information |
|---|---|
| Status | Accepted |
| Date | 2026-11-06 |
| Decider | The Owner |
| Resolves | The pending row "Hosting and publication" of the [record](README.md#3-pending), and the plan's N2 (hosting) and N15 |
| Supersedes / superseded by | — |

## Context

The showcase is a static site whose reports travel encrypted (ADR-0001), so the host only has to
serve files — but the plan asks more of it than serving: a preview of every PR before anything
reaches visitors, and a promotion of **exactly** the bytes that were previewed, never a rebuild
([PLAN §3.4](../../PLAN.md#34-the-architecture), RV3-03). It also asks that no long-lived credential
exist anywhere (N15), and that nothing fix a project, a site or an environment name in the code, so
that sandbox, qa and prod on Google Cloud stay possible (`CLAUDE.md` §5).

Before stage 2.2 three things were open. The free Spark plan was assumed, not proved, to allow the
IAM and STS APIs that federation needs with billing off. Firebase's own GitHub setup stores a
service-account key, contrary to N15, and that the CLI deploys and clones with Application Default
Credentials from a federated token was described only by community guides (PLAN §2). And the CLI's
form for a version was written as `SITE:@VERSION`. Stage 2.2 settled all three by execution: the
federation works on Spark with billing off and no key exists (T1, T7, T9); the CLI reads
`<site>@<version>` (M50); the version check serves Hosting's reserved files beside the site's
(M51) — `evidence/20261106/`.

## Alternatives considered

| Alternative | For | Against |
|---|---|---|
| **Firebase Hosting in a project of its own, reached only through workload identity federation** | Preview channels per PR, and a version that can be cloned to live byte for byte; free on Spark; a Google Cloud project, so it lives where eng_dados' stage 13 goes; no stored key | The Hosting Admin role covers every channel, so the preview identity could release to live: the separation has to come from GitHub's environments and the IAM bindings; channels expire, and with them what an approval refers to (§4.5 of the pipeline); the CLI's semantics (`@VERSION`, reserved `__/firebase/` files) must be known and tested |
| Firebase Hosting with Firebase's default GitHub setup | One command; the official path | A service-account key stored as a repository secret, readable by any workflow that runs on `main` and valid until revoked — contrary to N15 |
| GitHub Pages serving a branch or an artifact | No account, no project, no workflow beyond Pages' own; RP-12 recommended it for P01 alone | No preview channel: a PR's result cannot be served without publishing it; no version to promote, only whatever the branch holds; outside Google Cloud |
| A Cloud Storage bucket as a website | Plain Google Cloud, no Firebase | Requires the Blaze plan and billing, even for the default bucket (PLAN §2); no channels nor versions: previews and exact promotion would be built by hand |

## Decision

The showcase is served by the Firebase Hosting site of the project `bi-como-codigo`, on the Spark
plan with billing off, and is deployed only by GitHub Actions through workload identity federation
— the pool `github` and the provider `github-actions`, trusting only `publish.yml` and `promote.yml`
on `refs/heads/main` of this repository, and two service accounts with Firebase Hosting Admin, each
impersonable only from its own GitHub environment, `preview` or `production` — with no
service-account key, as specified in [`docs/publishing_pipeline.md` §5](../publishing_pipeline.md#5-the-federation).

## Consequences

- **Positive:** previews and exact promotion are the host's own features, not code of ours; no
  secret exists in the repository nor in its environments (T9); a token from any other workflow,
  ref or repository is refused at Google's token exchange, before any permission is read (T8,
  T11), and each environment reaches only its own account (T8).
- **Negative:** the preview identity holds the same Hosting role as the live one — Hosting offers
  no permission that separates channel deploys from releases (§5 of the pipeline, assumed) —, so
  the only thing between a preview and live is the `production` environment and its approval; a
  preview channel lives 30 days, and an approval older than its channel's life minus a day cannot
  be honoured (T10); the site serves Firebase's reserved `__/firebase/init.js` and `init.json`,
  which carry the project's public web configuration; what Spark does when its quota is exceeded is
  not documented (PLAN §2); the whole release path depends on `firebase-tools` behaving as pinned
  (15.28.2) and on Google Cloud's federation, and is undone only by the removal list of §8.
- **Continued operation on Google Cloud:** the project, the site, the provider, the service
  accounts and the environment names reach the workflows as repository variables, never written in
  the code; sandbox, qa and prod would be separate projects or sites, each with its own provider
  condition, service accounts, GitHub environments and variables — the same files, other values.
- **Documents to update:** PLAN's N2 and N15, which point to this ADR;
  [`docs/publishing_pipeline.md`](../publishing_pipeline.md), which owns the federation and its
  removal; the record's index and the README's count.
