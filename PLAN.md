# Plan — bi-como-codigo and the study content

> **What lives here:** the plan for the two new pieces of content — the `bi-como-codigo` showcase and
> the study content — and for the maintenance release of eng_dados they require: what gets built,
> the architecture, the impacts of the separation, the stages with the effort of each, the Owner's
> decisions, taken and pending, and what was measured to support all of it.
>
> **What does not:** the original proposal by Codex and the reviews of it and of this plan (see
> [`REVIEW.md`](REVIEW.md): §§1–11, findings RP-01 to RP-15, RV2-01 to RV2-14 in round 2, RV3-01 to RV3-04 in round 3, RV4-01 in round 4 and the closure in round 5); what
> eng_dados is and how it is operated (see its
> [README](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/README.md) and
> [Local Execution](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/execucao_local.md));
> the decisions, once recorded — they become ADRs in the repository that owns them.

| Field | Information |
|---|---|
| Date | 2026-10-23 — revision 10: the plan review closed by Codex in round 5 |
| Author | Claude Code, at the Owner's request |
| Base | eng_dados at `26b58b3` |
| Status | **Complete proposal, in execution.** Stage 2.1, the foundation, is done — its criterion met: the secret guard is green with the two demo passwords registered as public by design. In eng_dados, on 2026-10-23, stages 1.1 and 1.2 are done, committed locally and not yet pushed: 1.1 in `9c9ff9c` — the guard failed on eight views before the fix (P01, P02, P03, P05, P06, P13, P14 and the P15 denominator) and passes after; M3 redone on the views gives zero; only the two M3 groups changed; `make check` green, PASS=905 and 667 Python tests —, 1.2 in `7f97d62` — the ADR for O2, number 0049 there, `verificar.py` clean, `make check-offline` green. Nothing else is implemented. Every decision of the Owner taken (§1.2). Round 3 closed eleven round-2 findings and partly closed three. Round 4 closed five of the seven left in its scope and left RV3-02 and RV2-05 open only on RV4-01, applied in revision 9. Round 5 closed RV4-01, RV3-02 and RV2-05 with no new finding: the plan review is closed, and execution follows §6.3 (§10) |
| Nature | Lives in this repository. At stage 3.2, Part III moves to `caderno-de-dados`; Part I becomes ADRs and pending items in eng_dados |
| Evidence | [`evidence/20261022/`](evidence/20261022/) for M1–M18 and [`evidence/20261023/`](evidence/20261023/) for M19–M23: read-only probes, prototypes and counterexamples, with their literal outputs and the `ro.sh` that re-runs the SQL probes |
| Translation | Translated from Portuguese on 2026-10-22, at the Owner's request. The original is in commit `e046937` of this repository |

---

## 1. What is already decided

### 1.1 By the Owner, in the conversation of 2026-10-22

The choices from the conversation with Codex still hold
([`REVIEW.md` §1](REVIEW.md#1-the-request-and-the-choices-already-made)), redistributed by O6: P01 is
the first report of the showcase and the first lesson of the study content.

| # | Decision |
|---|---|
| **O1** | A **separate project, in a new repository**. eng_dados is complete, and the exclusion of BI and dashboards in its Charter §4 applies to it and still does |
| **O2** | **No synthetic field is restricted in the analyses**: all of them may — and should — appear |
| **O3** | Where it adds value, **fix the synthetic data** that is incoherent today |
| **O4** | **An in-depth study of the governance**: how it is built, what value it has and how to use it in the project |
| **O5** | The project **grows to every view and analysis** of eng_dados. The thesis: reports as rich as Power BI's, or richer, **with no licence**, and without bringing the whole database |
| **O6** | **Two pieces of content.** The **showcase** (`bi-como-codigo`) shows technical capability: a robust, summarised product, an executive presentation that needs no presenter; the governance of the project; and, above all, the data governance, told as a **reading portal** — "I have just arrived at this database and want to understand everything in it" —, organised and engaging, so that whoever consults it learns fast and recognises a well-governed project. The governance may be reassessed and refined. The **study** content is the learning: explorations, the path from the views to the source, understanding the governance and the project |
| **O7** | **Login, and content segregated by login,** in the showcase: two logins, one of them with access to a single report that makes sense in the story, to show **least privilege**. A simple implementation, straight in the code; no more logins and no management screen |
| **O8** | **A complete separation from eng_dados**: the new notes live in the new repositories, and eng_dados keeps only the references it needs — such as the justification for changing its database |

### 1.2 The decisions

| # | Question | Choice |
|---|---|---|
| **N1** | Name of the showcase | **`bi-como-codigo`** |
| **N2** | Data, querying and publishing | **Parquet queried by DuckDB in the browser; Firebase Hosting in a project of its own; GitHub Actions publishes on merge and builds a preview per PR; the DuckDB engine comes from jsDelivr** |
| **N6** | When to fix the synthetic data | **Now, before anything else** |
| **N8** | Scope of the ADR for O2 | **Classifying is not exposing**: the classification stays — metadata, and the basis of the policy tags of Stage 13 —, and exposing synthetic data becomes free. It rewrites the rule of [Governance §4](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#4-classificação-de-sensibilidade) and settles today's divergence (RP-02) |
| **N17** | How to organise the two pieces of content | **Two repositories, two sites**; the study content reads the data the showcase publishes and has its own capture for the lessons |
| **N18** | Where the study content lives | **Private on claude.ai, as long as nothing is limited by it; if any capability is limited, a `*.web.app`.** The probe of stage 3.1 decides |
| **N20** | When to refine the governance | **In v1.1.0**, as a stage of its own, separate from the regeneration |
| **N14** | D62, D63 and D64 in v1.1.0 | **No** — they remain pending items of their own |
| **N23** | How to implement the per-profile access (O7) | **The password becomes the key**: each report is encrypted at publication, and the fixed password of each profile opens only the keys of its reports — no account, no Firebase Authentication, no Firestore |
| **N22** | Do visitors see the passwords? | **Both, below the login box**, with the text in §3.2; above the box, an explanation of what the page and the product are |
| **N4** | Which login the exporter reads the views with | **A read-only login**, member of `analyst`, created by eng_dados in v1.1.0 |
| **N16** | The dimensional model in the showcase | **Only the 16 views, for now**: the consumption contract stays intact, and detail, when a report needs it, comes with an ADR in eng_dados |
| **N7** | The study trail after the regeneration | **A notice at the top**: the real outputs were measured on the v1.0.0 data. It goes in only with the next update of the trail, never on its own |
| **N21** | Name of the study repository | **`caderno-de-dados`** |
| **N3** | Framework for the reports and the portal | **A comparative prototype on P01** — Evidence against a build of our own with DuckDB-WASM and a charting library —, and the choice after it (stage 2.3) |
| **N15** | Authentication of the CI pipeline to Firebase | **Identity federation** from GitHub to Google Cloud, with no stored key |
| **N10** | Does the study clock count `caderno-de-dados`? | **Yes** |
| **N12** | The showcase in the portfolio | **A link on the page of project A** |
| **N24** | Language of the new repositories and of the communication between agents | **Construction in English** — code, commits, technical documents, plans, reviews and the communication between Claude Code and Codex; Portuguese for what visitors read, for the study content and for the conversation with the Owner ([`CLAUDE.md`](CLAUDE.md) §2) |
| **N25** | When to create `bi-como-codigo`, and with what visibility | **Now, public** — created on 2026-10-22 to keep this version and separate it from eng_dados |

### 1.3 Consequences

- N2 settles the former N13: updating the showcase means opening a PR with the new package (§3.4).
  It also replaces the single-file design of revision 1 (RP-10).
- With N23, O7 adds no component: Hosting still serves everything, and the reports go encrypted
  (§3.2). The study content reads the showcase reports by URL and opens them with the password of
  Diretoria (§3.3); the probe of stage 3.1 tests WebCrypto inside the Artifact.
- O6 settles the former N9: the study of the governance lives in the study content; the showcase
  has the reading portal.
- With N2, the showcase lives in a Firebase project of its own; if the probe sends the study content
  to a `*.web.app`, it gets its own as well, for the same reason — no shared quota. The former N19
  needs no question.
- N6 and N20 put Part I at the front of the queue.
- N16 leaves the dimensional model out for now: stage 2.12 exists only if a report asks for detail.
- O8 and N25 moved this plan, the review and the evidence out of eng_dados into this repository.
  eng_dados records only what Part I needs, as it is executed (§5.6).
- N24 sets the language of construction here; the evidence stays as recorded, in Portuguese.
- In the dimensional model, the `personal` fields are name, a document with the `SIN` suffix, date
  of birth and an e-mail at `example.com` — no phone number (M16). The phone caveat (RP-15) only
  comes back if `trusted` or `raw` are published.
- The round-2 review changed how the plan implements the decisions, not the decisions. Encryption
  moves to the export on your machine, so no clear report data ever enters the public repository
  (RV2-01); publication gains three gates and a trusted workflow (RV2-03 to RV2-05); the envelope is
  specified (RV2-02); description inheritance becomes conservative (RV2-08); the recovery package
  follows its full lifecycle (RV2-06).
- Round 3 completed the trust boundary of publishing: the credentialed job runs only reviewed
  code from `main` and treats the candidate as data (RV3-02); promotion goes by version ID
  (RV3-03); the envelope gets a byte-level format (RV3-01); and the stage table puts the workflow
  (2.2) and the complete gate (2.2b) before any real report reaches Hosting (RV3-04).

---

## 2. What was measured

M1–M18 were read in a `default_transaction_read_only=on` session on the running warehouse, between
2026-10-23 00:12Z and 01:22Z (2026-10-22, 21:12 to 22:22 in Brasília), on commit `26b58b3`. The view
was read as `analyst`; the inner layers, by the superuser in the same read-only session; the files,
with no database. M19–M22 reproduce the round-2 review on 2026-10-23 at 03:52Z, and M23 the round-3 probe at 04:23Z,
on the same commit.
Literal outputs in the evidence folders.

| # | What | Result | Consequence |
|---|---|---|---|
| M1 | The P01 view | 1,140 rows; 33 months (2024-01 to 2026-09); 3 channels; 4 root categories and 12 leaves; R$ 33,076,529.47 of net revenue; ~96 kB as text | — |
| M2 | P01 recomputed from the fact table, at the same grain | 0 rows diverging in count or revenue | An oracle for the custodian — the exporter never reads the fact table (§3.5) |
| M3 | Order count without `source_system` | 126 `order_id` values exist in both sources. P01 and P02: no group affected today. **P05 and P06 undercount one order in one group each**: P06 2025-07 · Aplicativo · Eletrônicos (11 × 12); P05 2024-T4 · Aplicativo · SP (20 × 21) | A real defect in the datamart, against the rule of the `empilhado` macro — "the source goes into the condition with the key, always". No test catches it |
| M4 | Realised orders with items in more than one category | 2,479 of 3,292 | P01's `order_count` does not add up across categories, and P01 does not even declare it as a measure in the [Glossary](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/glossario_de_negocio/perguntas_de_negocio.md#p01--qual-a-receita-líquida-por-mês-canal-e-categoria-de-produto) |
| M5 | Coverage | first realised sale on 2024-01-02, last on 2026-09-01 (`as_of_date`). 2026-09 has 3 groups, 9 units and R$ 17,795.87; the other months, R$ 0.65 M to R$ 2.07 M | 2026-09 is a one-day month: the monthly chart would show a drop that does not exist |
| M6 | Month × channel × category combinations with no row | 15 in complete months; 33 in 2026-09 | A slice with no sale, distinct from zero |
| M7 | Category tree | most leaves sit under an unrelated root: "Moda › Notebooks", "Moda › Sofás", "Eletrônicos › Panelas", "Eletrônicos › Camisetas", "Casa e Cozinha › Calças". The parent is assigned round-robin (`generator/domains/catalogo.py`) | The main axis of P01 has no business meaning |
| M8 | Price by category, in the retail source | average from R$ 1,970 (Caixas de som) to R$ 2,930 (Organizadores), overlapping ranges from R$ 63 to R$ 6,939. The base price comes from a single range for every product (`geracao.yml`: `faixa_de_preco: [9.90, 4800.00]`) | Contradicts [Data Generation §5](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/geracao_de_dados.md#5-realismo-e-coerência), which states the affinity between product, category and price as implemented |
| M9 | Sale before launch (D65) | 3,130 of 7,500 retail items — the same number as on 2026-10-04 | Still open |
| M10 | `ORD-0000037` | two different orders with the same number: in the legacy source, 2024-12-09, Eletrônicos; in retail, 2025-07-01, Moda and Eletrônicos — the latter is the case cited in D65 | A bad example for the first lesson; a good hook for the lesson on composite identity |
| M11 | Decimal scale in `trusted.order_items` | retail: discount with scale 0 to 2 and price 0 to 4; legacy: always 2 and 4 | Format by the declared scale, never by the text the database returns |
| M12 | Column lineage — a prototype that walks `Lineage.leaves`, reimplementing nothing | `net_revenue_amount`: 15 nodes and 14 edges down to `raw` and `raw_legacy`, 0 problems, complete manifest (192 models), 20 to 30 s. `year_month` ends at `dim_date` (generated); `category_name` reaches the name in `raw.product_categories` without going through the temporal join of the product; the legacy branch jumps from `raw_legacy.order_items` straight to `legado__order_items` | Value lineage answers "where does the value come from". Membership and controls need a small declaration |
| M13 | Size of the warehouse | **588 MB** for the whole database: `raw_legacy` 206 MB, `trusted` 138 MB, `raw` 86 MB, `quarantine` 77 MB, `analytics` 50 MB, `staging` 8 MB, the rest under 1 MB; `consumption` is views | The bulk is what comes before the product: bringing the database makes no sense |
| M14 | The analytical product in Parquet (zstd) | 25 `analytics` tables and 16 views: 162,351 rows, **8.10 MiB**. The views alone: 15,377 rows, 0.23 MiB; the largest, `inventory_turnover_by_sku_and_warehouse`, 77 KiB. The largest table, `fact_cart_event`: 81,199 rows, 3.4 MiB. Exported in 4.0 s | It fits in files on the site itself, encrypted per report |
| M15 | DuckDB-WASM engine 1.32.0, of 2025-12-16 — the latest stable on npm | **6.8 MB** downloaded with brotli, 7.6 MB with gzip and 34.2 MB uncompressed, stable over three reads. The first read gave 5.2 MB, from another CDN node — unexplained | Served by free Firebase, the 360 MB/day quota would hold ~50 first visits a day. That is why the engine comes from jsDelivr |
| M16 | `personal` fields in `analytics` | 9 columns: first name, last name, full name, document and birth date in `dim_customer`; first name, last name, full name and e-mail in `dim_support_agent`. No phone number | The phone caveat does not apply to the dimensional model |
| M17 | Catalogue coverage, in the dbt manifest | Classification, lineage, access and retention complete; 700 data tests. **Column descriptions**: `analytics` 26 of 477, `consumption` 31 of 188, `trusted` 56 of 1,069, `staging` 659 of 1,114, `raw` and `raw_legacy` 0 of 1,161. **`domain` and `owner`**: 0 of the 41 objects in `analytics` and `consumption`, although [Governance §5.1](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#51-padrão-de-metadados) requires them on every model | A reading portal with blank descriptions contradicts what it shows; the rule of §5.1 is not met today |
| M18 | Descriptions inheritable through lineage — an estimate, **superseded by M21** | Without a description and with a single leaf of the same name: 357 in `analytics`, 113 in `consumption`, 198 in `trusted`. Needing text: 94 in `analytics`, 44 in `consumption`; in `trusted`, 815 | It used the single-leaf shortcut that M21 disproves; it bounds nothing |
| M19 | Two channel labels swapped in P01 (`Aplicativo` ↔ `Loja física`) | Still 1,140 rows, R$ 33,076,529.47 and 13,920 units; **761 rows** diverge from the view in a row-level comparison | Counts, sums and hashes prove a package is consistent, not that it is right: the export needs row-level equality with the views (RV2-03) |
| M20 | P13's rounded averages, re-weighted by their counts, against the direct calculation over 313 month × carrier × service groups | 46 groups differ in transit days and 20 in late delay, at the view's four decimals | Those averages cannot be re-aggregated; they stay at the view's native grain (RV2-12) |
| M21 | Lineage leaves of `total_amount`, `sum(…)`, `round(…, 2)`, `… * 100` and `cast(… as numeric(12,2))` | The same single leaf for all five | A single leaf of the same name does not prove that a column only carries a value (RV2-08) |
| M22 | The envelope modelled with WebCrypto and the two public passwords | The Logística password opens P13 and fails on P01; the Diretoria password opens both; its holder can produce ciphertext the site accepts as valid; a flipped bit is rejected | What the encryption demonstrates is access scoped to a key, not authentication or confidentiality (RV2-01) |
| M23 | Authenticated data serialised as JSON, with the same fields in another order | Decryption with the reordered bytes fails | The authenticated data needs one canonical byte serialisation (RV3-01) |

**Read from official sources on 2026-10-22 and 2026-10-23 — not measured:**

| Source | What it says |
|---|---|
| [Firebase](https://firebase.google.com/pricing), Spark plan | Hosting: 10 GB of storage and 360 MB/day of transfer; on Blaze, US$ 0.026/GB and US$ 0.15/GB beyond that. What happens when Spark runs over the quota, the page does not say |
| [Firebase Hosting, managing versions](https://firebase.google.com/docs/hosting/manage-hosting-resources) | `firebase hosting:clone SITE:CHANNEL SITE:live` deploys a version to another channel; within the same site, the release points to the exact same version |
| [Firebase CLI](https://firebase.google.com/docs/cli) | Recommends Application Default Credentials for CI and no longer recommends tokens. That it accepts a federated credential from GitHub is described only by community guides |
| [Firestore](https://firebase.google.com/docs/firestore/quotas), free quota | 1 GiB stored; 50 thousand reads, 20 thousand writes and 20 thousand deletes a day; 10 GiB/month of egress; documents up to 1 MiB |
| [Cloud Storage for Firebase](https://firebase.google.com/docs/storage/faqs-storage-changes-announced-sept-2024) | Requires the Blaze plan, including the default bucket; on Spark, calls answer 402 or 403 |
| [Firebase Authentication](https://firebase.google.com/docs/auth/flutter/manage-users) | A signed-in user can change their own password and delete their own account through the client SDK; those actions require a recent sign-in |
| [Neon](https://neon.com/pricing), Free plan | 1 GB per project; 100 CU-hours; suspends after 5 idle minutes; 5 GB/month of public transfer — once exceeded, compute stays suspended until the next period |
| [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) | Published site up to 1 GB; 100 GB/month of bandwidth, a soft limit |
| GitHub API | Evidence: release of 2026-02-06 and last push on 2026-10-22, MIT. Observable Framework: release of 2026-03-02 and last push on 2026-05-15, ISC. DuckDB-WASM: last push on 2026-10-22, MIT |

**Not measured:** site build time; how any framework behaves with this data; DuckDB and WebCrypto
inside the claude.ai Artifact; the time to derive the keys in the browser; usability; the effect of
the fixes on the tests of eng_dados.

---

## 3. What gets built

### 3.1 The two pieces of content

| | **Showcase — `bi-como-codigo`** | **Study — `caderno-de-dados`** |
|---|---|---|
| For whom | Whoever evaluates your work, in minutes, without you there | You |
| Tone | A self-sufficient executive presentation | Exploration, lab, questions |
| Content | Overview; reports for the 16 questions, with per-profile access; reading portal of the data governance; governance of the project | Lessons from the view to the source; study of the governance; SQL explorations; link to the study trail |
| Data | Parquet of the 16 views, encrypted per report on your machine before it enters Git; public governance metadata, generated from eng_dados | The showcase reports, read by URL and opened with the password of Diretoria; its own capture for the lessons |
| Where | Firebase Hosting, in a project of its own (N2) | A private claude.ai Artifact or a `*.web.app`, by the probe of stage 3.1 (N18) |

### 3.2 The showcase

**Principles.** Every page explains itself, with no presenter and no jargon that does not lead to
the glossary. Every number comes from a record of eng_dados at a pinned commit, with its date —
none is typed (P5). Narrative first, reference after: whoever has two minutes reads the story;
whoever has twenty goes down into the catalogue. Navigation by tabs and links, always with a way
back; search in the catalogue; accessibility and narrow screens.

- **Overview.** The project on one page: what it is, the architecture in one picture, the numbers
  that prove its robustness and three doors — reports, data governance, how it was done.
- **Reports — BI as code.** The 16 questions, each a reviewable text file with the query and the
  presentation; filters, cross-filtering, charts and table in the browser. P01 first. Rules set by
  the reviews: partial month flagged (M5); a slice with no sale said as such (M6); `order_count`
  never added up across categories (M4); ratios re-aggregated only through numerator and
  denominator; an average published without its sufficient statistics stays at the view's native
  grain — P13's transit and late-delay averages among them (M20); no filter the view does not
  offer; no metric redefined in the report. Each report starts with an audit of its view for
  non-additivity, balances that depend on time and truncated populations.
- **Per-profile access (O7, N23).** Hiding a report in JavaScript is not access control: the file
  could still be downloaded by URL, and an evaluator sees that in the network tab. And an account in
  Firebase Authentication does not make the password immutable: a signed-in visitor can change it
  or delete the account (§2). Hence **the password becomes the key**. Because both passwords are
  public (N22), what this demonstrates is **access scoped to the key supplied**: each password opens
  exactly its profile's reports and no other. It is not the authentication of a person, and it is
  not confidentiality from the public — whoever reads the Diretoria password on the login screen
  can open every report, with or without the site (M22):
  - two profiles, declared once in the code: **Diretoria**, which opens the 16 reports, and
    **Logística**, which opens only **P13** — on-time delivery by carrier. Whoever handles carriers
    needs no revenue, margin or payment data;
  - encryption happens **on your machine, at export**, before anything enters Git: the public
    repository only ever receives ciphertext and a manifest with no clear figure. The envelope is
    specified in §3.6;
  - in the browser, WebCrypto derives the key from the password, unwraps the keys the profile is
    entitled to and decrypts only those reports. A wrong password opens nothing. Switching profile
    or logging out clears the decrypted tables, buffers and caches: no Diretoria data stays visible
    after switching to Logística;
  - the password is truly immutable: there is no account to change or delete, and it only changes in
    a new publication, through a PR of yours. A later change does not revoke ciphertext already
    downloaded with the former password;
  - the login screen has, **above** the box, an explanation of what the page and the product are
    and, **below** it, the credentials (N22), generated from the same declaration of the profiles:

    ```text
    Para acessar, use:
    Login: Diretoria
    Senha: senha_complexa_123
    ou
    Login: Logística
    Senha: complexa_senha_321
    ```

  - the overview, the portal and the governance of the project stay open, with no login;
  - the proof is by execution, like `test_acesso` in eng_dados: the whole profile × report matrix
    through actual unwrap and decrypt calls, at build and in the browser against the preview, plus
    the negative cases of §3.6. In the showcase, Logística is invited to open another report and sees
    that its key does not open it.
- **Reading portal of the data governance.** Generated from the declarations of eng_dados — dbt
  manifest, YAMLs, glossary, ADRs, lineage —, with the narrative curated into chapters:

  | Chapter | What it answers |
  |---|---|
  | 1. Start here | What database this is, the two sources, the nine layers in one picture, where to go next |
  | 2. The map | Each layer: why it exists, who writes, who reads, how long it keeps data, how many objects |
  | 3. The catalogue | Each object and column: description, domain, owner, grain, type, classification, the tests that guard it, incoming and outgoing lineage, the questions that use it |
  | 4. The business questions | Question → view → measures and additivity → fact and dimensions → report |
  | 5. The vocabulary | Business and technical glossary |
  | 6. Who sees what | Classification by layer, roles × layers in the warehouse, the proof by execution, classifying is not exposing — and the same least privilege applied in the showcase itself |
  | 7. Where each number comes from | Column lineage down to the source, with the crossings outside dbt — one hop at a time, never the whole graph |
  | 8. Why trust it | Tests by layer, reconciliation at every boundary, invariants, quarantine with a reason, capture certification |
  | 9. How this is maintained | Catalogue as code: everything here is generated from the declarations, and `make check` keeps them from diverging |

  From chapter 1, a short route — question → report → column — lets a newcomer reach an answer
  without walking through the catalogue first. Missing metadata is labelled as missing, never filled
  in. Tests appear in three distinct states: declared, executed successfully on a stated date, and
  open issues today — a past review with no finding left does not mean D62 to D64 are solved.
- **Governance of the project.** Principles P1–P10; the decisions as ADRs, on a timeline and
  searchable; the review by a second agent, round by round, until no finding was left; the
  definition of done; the documentation map with one owner per subject; risks and their
  treatments; milestones; the from-scratch cycle as measured and the recovery point. Generated from
  the documents and the history of eng_dados.

### 3.3 The study content

- **Lessons, starting with P01.** An item chosen by a declared criterion — retail, realised, with a
  discount, quantity above one and visible rounding —, captured in a single snapshot: `raw`,
  `staging`, `trusted`, `analytics` and `consumption` all live in `warehouse_db`, and one
  `REPEATABLE READ READ ONLY` transaction gives the same picture across all of them. The lesson
  starts at `raw`. The three questions of
  [`REVIEW.md` §3.2](REVIEW.md#32-a-didactic-path-with-progressive-disclosure) organise the path, with
  the item's value, the other items and the group total.
- **Study of the governance (O4).** For each mechanism of eng_dados: how it is built, what value it
  has — with the real incident it caught or prevents —, how to use it and what it does not cover,
  with labs actually executed. Three incidents already checked by reading: the grant given by hand
  to `analyst` on `trusted`, revoked on the next run
  ([Governance §7](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#7-regras-de-acesso-por-camada));
  P11, which passed `dbt build` and failed on its first read (`tests/test_consumo.py`); the `unique`
  of `dim_customer`, broken on the first load with the legacy source
  (`dbt/tests/legado_nao_colide_com_a_origem_principal.sql`).
- **Explorations.** Free SQL, with DuckDB in the browser, over the showcase reports opened with the
  password of Diretoria; and the next candidate lessons — composite identity (M10) and one rejection
  all the way to quarantine.
- **The study trail** stays in eng_dados, as it is; the study content points to it.

### 3.4 The architecture

```text
1. Export, on your machine — eng_dados databases up, the read-only login of N4:
   one consistent read of the 16 views → contract, grain, nulls and decimals checked
   → typed rows equal to the views after the Parquet round trip → encryption per report
   → package with oracle results, and a public manifest with no clear figure
2. PR in bi-como-codigo — branches of this repository only:
   CI checks the package, decrypts the whole matrix with the public passwords, builds a fresh
   deploy directory from an explicit inclusion list, inspects the finished output
   and deploys it to a preview channel
3. Merge, behind a protected environment:
   the approved preview version is cloned to live — the same bytes, no rebuild
4. Browser: password → key → only that profile's reports, opened by DuckDB-WASM (engine from jsDelivr)

study (GitHub) ── lessons and its own capture ──▶ Artifact or *.web.app ◀── URL + password of Diretoria
```

- The exporters run only on your machine: the warehouse is never reachable from the internet, and
  CI never reads it.
- **Three gates, each where it can actually be checked** (RV2-03 to RV2-05):
  - **source to package**, local, by the exporter: a single read-only `REPEATABLE READ`
    transaction; the explicit inventory of the 16 views; the accepted schema and version of each
    view, pinned in this repository — not whichever dbt manifest comes along; grain and uniqueness;
    nulls, decimal precision and scale, dates and time zones, including empty and all-null cases;
    and typed rows compared after writing and reading back the Parquet. The oracle results travel
    with the package. The exporter stays a consumption reader: oracles over the inner layers, like
    M2, belong to the custodian (§3.5);
  - **package to artifact**, in CI, before any upload — previews included: the package against its
    manifest, the whole decryption matrix with the public passwords, a fresh deploy directory built
    only from an explicit inclusion list, and the finished output inspected for clear report data
    and unwrapped keys — in HTML, JSON, JavaScript, caches and source maps, by content and not by
    file extension;
  - **artifact to live**: approval records the candidate revision, the package and artifact
    digests and the Hosting **version ID** of the preview. The merge promotes exactly that version
    with `firebase hosting:clone SITE_ID:@VERSION_ID SITE_ID:live`, which within the same site
    points live at the same version — never with the channel-name form, which takes whatever the
    channel deployed last (RV3-03). Promotions run one at a time, and each first rejects a
    superseded candidate, so neither a preview advanced after approval nor a rerun of an older job
    can replace the current release. A changed candidate needs a new preview and a new approval.
- **Mutation tests prove the gates**: swapped row labels (M19), missing and extra views, changed
  types, duplicated rows, injected clear data, a tampered manifest and a reused key/IV pair.
- **A trusted workflow** (RV2-05, RV3-02). A branch of this repository does not make a PR's code
  trustworthy: a PR can change the checker, the build or `firebase.json`. So the work splits in two:
  - the **candidate workflow** (`pull_request`) builds and checks the candidate with no deploy
    credentials and no permission to request an OIDC token, and uploads the result as an artifact;
  - the **publishing workflow** (`workflow_run`) runs only what is on `main` — its checker,
    inclusion list and Hosting configuration, changed only through a separately reviewed PR —,
    downloads the candidate as data, never executes its scripts or hooks, revalidates the exact
    artifact against every gate and only then deploys, to a preview or, after approval, to live;
  - federation (N15) trusts only that workflow file at `refs/heads/main`, in this repository and
    its protected environment: the GitHub OIDC token carries `workflow_ref`, `ref` and
    `environment` for that binding (RV4-01). The publishing workflow is called directly, not as a
    reusable workflow, so the binding uses `workflow_ref`; `job_workflow_ref` identifies a called
    reusable workflow, which this design does not have. Firebase's default GitHub setup stores a service-account key,
    contrary to N15: stage 2.2 proves the Firebase CLI with Application Default Credentials obtained
    from the federation instead;
  - code from forks never runs with deploy credentials, and a same-repository PR that changes the
    checker or the configuration gets neither a preview nor a live update — one of the rejection
    tests of 2.2.
- **Versions are bound**: content-hashed names for the application, the manifest, the wrapped keys
  and the ciphertext, so that a page left open never fetches incompatible new files at reused URLs.
- **Updating means opening a PR** with the new package: the preview shows the result, the diff of
  the manifest shows what changed, and the merge publishes.
- **The public manifest carries no clear figure**: the control totals travel encrypted with each
  report, and CI checks them after decrypting with the public passwords. This applies to the report
  packages and their control totals; the governance metadata is public by design, and the evidence
  already in Git stays as recorded.

### 3.5 The contract with eng_dados

Every crossing between the repositories is explicit and versioned.

| What is used | How | Why |
|---|---|---|
| The 16 views | Read by a login that is a member of `analyst` (N4), tested through an actual non-superuser connection: it reads `consumption`, is refused elsewhere, cannot write and cannot escalate its role | The database itself guarantees the exporter only reads consumption |
| The contract of the views | The accepted schema and version of each view, pinned in this repository and checked at every export; a change upstream fails the export until it is accepted here | A contract change in eng_dados fails loudly instead of becoming a wrong number |
| Oracles over the inner layers | Run by the custodian, separately, never with the exporter's login | The exporter stays a consumption reader |
| The dimensional model | Out for now (N16); if a report asks for detail, through a consumption contract, with an ADR in eng_dados | [Governance §7](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#7-regras-de-acesso-por-camada) and [ADR-0008](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/adr/0008-schemas-do-armazem.md) do not let a consumer read `analytics`, and [ADR-0018](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/adr/0018-fatos-e-views-a-partir-de-perguntas-de-negocio.md) rejected "one view per fact" |
| Governance metadata | Read from the repository at a pinned commit — dbt manifest, YAMLs, glossary, ADRs, documents —, with no access to the data | The portal is derived, not written; what changes in eng_dados changes in the portal at the next export |
| Column lineage | `python -m mvp_ed1.models.lineage --json`, run with the `.venv` of eng_dados (stage 1.3) | No second declaration of the lineage, and no dependency on internal code |
| SQL excerpts and documents | A text anchor per file, read with `git show <commit>:<path>` at a pinned commit; a GitHub link at that commit | An excerpt that disappeared breaks the build; links do not rot |
| Capture for the lessons | By the custodian: superuser, read-only `REPEATABLE READ` transaction, an explicit and rare command | It is the study-reading pattern eng_dados already uses (`make pgcli-*`); no new role |
| Version | eng_dados commit, `generated_at` of the dbt manifest, time of the read | "This warehouse was built by this commit" has no evidence today: it stays marked as not verified |

### 3.6 The encryption envelope — a proposal to review before stage 2.3

Standard WebCrypto primitives only (PBKDF2, AES-KW and AES-GCM, all in the
[Web Cryptography API](https://www.w3.org/TR/2017/REC-WebCryptoAPI-20170126/)), in a versioned
envelope that fixes every parameter instead of relying on library defaults (RV2-02). **Proposed
parameters**, to be reviewed by Codex together with the reference implementation of stage 2.2a:

| Element | Proposal |
|---|---|
| Password | The UTF-8 bytes of the password exactly as declared |
| Key derivation | PBKDF2-HMAC-SHA-256 with a random 128-bit salt per profile, public, rotated with a declared scope. The iteration count is set from the browser latency measured in 2.2a, following [NIST SP 800-132 §5](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-132.pdf) |
| Wrapping | AES-KW with a 256-bit key-encryption key per profile. AES-KW uses its own fixed initial value: the random-IV rule of GCM does not apply to it |
| Data keys | A 256-bit AES-GCM key, **fresh for every encryption of a file** — retries and new publications included. An unchanged encrypted artifact is promoted, never encrypted again |
| Encryption | AES-GCM with a random 96-bit IV and a 128-bit tag. With a fresh key per encryption, no key/IV pair repeats — [NIST SP 800-38D §8](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf) requires uniqueness per key |
| Authenticated data | Envelope version, package identity, report identity and the expected mapping in the manifest |
| Envelope fields | Version, password encoding, KDF, hash, iterations, salt, wrapping algorithm, report identity, the wrapped key per profile, IV, tag length and package identity — every length stated |

**The byte-level format is frozen in stage 2.2a** (RV3-01), because equal fields are not equal
bytes (M23): the binary encoding and the format of the wrapped key; the layout of ciphertext and
tag; the layout of the encrypted payload — the Parquet and its control totals; the authenticated
data as one canonical serialisation, with fixed field order and lengths; the scope of salt rotation;
and the accepted versions, algorithms, lengths and iteration bounds, outside which the reader
refuses. Package identity is minted independently of any ciphertext hash, so nothing is defined in
terms of itself. The reader takes the identities it expects from the validated manifest, never from
the envelope it is checking. All randomness comes from a cryptographic generator, and the generation
and retry path is reviewed: fresh random keys make accidental reuse negligible, not impossible —
hence the injected-reuse test.

**What it guarantees, and what it does not.** Binding identities to the authenticated data — and
checking them against the identities the validated manifest expects — catches the substitution of
one report or package for another. It does not authenticate the publisher
against someone who knows a public password, who can produce ciphertext the site accepts (M22):
authenticity comes from the trusted release path and the HTTPS origin. A password changed in a later
release does not revoke what was already downloaded with the former one.

**Oracles:** known-answer vectors; a fixed, complete envelope vector consumed by an independently
implemented reader; producer and browser round trips through independent implementations; the whole profile × report matrix through actual unwrap and decrypt calls; wrong
passwords; altered wrapped keys, salts, IVs, tags and ciphertext; swapped report and package
identities; malformed envelopes; an injected reused key/IV pair; the finished deploy artifact
inspected for raw data and keys; and profile switching and logout clearing DuckDB tables, buffers
and caches.

---

## 4. Impacts of the separation

| Aspect | Impact | Treatment |
|---|---|---|
| Scope of eng_dados | None: it stays complete, and BI stays out of it | Objective, scope and out of scope in the README of each new repository |
| Fixes and refinements in eng_dados | The separation does not spare them: the generator, the views and the governance declarations live there. The completed project reopens for a **maintenance release, v1.1.0**, with its own acceptance and tag | Part I |
| Access to the warehouse | The only login today is the superuser (Governance §7). Copying that password into another repository is what no real environment would do | A dedicated login, member of `analyst` (N4) — the "next step" that §7 itself already states |
| Access to the showcase | No new component: encryption at the export, opened in the browser by WebCrypto (N23, §3.6). Firebase Authentication and Firestore were left out | Stages 2.2a and 2.6; an ADR in `bi-como-codigo` |
| Environment | Exporting needs only the eng_dados databases up (`make up`) | — |
| Governance | The policy of eng_dados still owns the published data; each new repository states what it publishes and cites the ADR | Stage 1.2 |
| CI/CD | Out of scope for eng_dados (Charter §4); part of the product in the showcase | Stage 2.2: a trusted workflow — same-repository previews, protected environment, federation restricted to this repository, promotion by clone (§3.4; N15) |
| Hosting | Showcase decided (N2), with a 360 MB/day quota. Study content by the probe of stage 3.1 | Engine from jsDelivr; each page loads only its own files; separate Firebase projects |
| Secrets | Each new repository needs its own guard. The `secrets_review` of eng_dados knows the keys of its own `.env`. The two demo passwords are public by design (N22) and are not secrets: they go into a register with the reason, like `segredos_tratados.yml` in eng_dados, so that the guard does not flag them | Stages 2.1 and 3.2 |
| Conventions and skills | `CLAUDE.md` and `AGENTS.md` do not come by themselves. The `revisao` skill was written to be portable — only `comandos.txt` changes —; the `adr` skill points at eng_dados paths | Stages 2.1 and 3.2 |
| Claude Code memory | It is per folder: each new repository starts with none | Conventions in the `CLAUDE.md` of each; working preferences in new memories |
| Study clock | The bash hook only records commands inside eng_dados; in the Artifact, the clock already works through the database capability | The hook and the collector extend to `caderno-de-dados` (N10; stage 3.8) |
| Study trail | Stays in eng_dados. With N6, its real outputs come to describe the v1.0.0 data | A notice at the top (N7), with the next update of the trail — local and Artifact —, never on its own |
| Portfolio | The showcase is the portfolio piece | A link on the page of project A (N12), at stage 2.10 |
| This plan and `REVIEW.md` | Moved from the root of eng_dados into this repository | Part III moves to `caderno-de-dados` at stage 3.2 |

---

## 5. Part I — maintenance release v1.1.0 of eng_dados

First in the queue (N6, N20).

### 5.1 Order count with the source

`count(distinct (source_system, order_id))` in the P01, P02, P05 and P06 views, a sweep of the other
counts and joins by identifier without the source, and a test that fails when consumption counts an
identifier without it. **Value:** fixes today's two wrong groups (M3) and closes the class of
defect. **Cost:** small; the contract types do not change. It is a fix — the behaviour becomes what
the rule already written says.

### 5.2 The ADR for O2, lineage as JSON and the exporter's login

The ADR that separates classifying from exposing (N8). `--json` in the lineage module: immediate
leaves and terminal origins per column. With N4, `governance.garantir()` comes to create a login that
is a member of `analyst`, with its password in `.env`; the proof goes through an actual connection
with that login — it reads `consumption`, is refused on the other layers, cannot write and cannot
escalate its role —, not through `SET ROLE` from the superuser (RV2-11).

### 5.3 Realism of the synthetic data (O3, N6)

| Fix, in the generator | Value | What changes |
|---|---|---|
| A declared category tree — leaf, middle and root coherent, still balanced | P01's axis gains business meaning (M7) | Names and parents of the categories |
| A price range per category | Comparing revenue across categories starts to mean something; closes the divergence between Generation §5 and the code (M8) | Every monetary value in the warehouse |
| Launch before sale, with invariant 14 | Closes D65 (M9) | Launch or sale dates; the SCD history of the product |

**The regeneration**, under [Local Execution §3.2](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/execucao_local.md#32-regerar-uma-origem-que-já-alimenta-streaming)
— destructive maintenance, with the `FORCE=1` of the procedure itself, which never overrides a
refusal for memory. The runbook of stage 1.4 maps every checkpoint of that procedure to a command, an
expected oracle and a restart or rollback point (RV2-07): host producers, Beam/Prism and active jobs
stopped; CDC and the hot sink reset; the retail ingestion reset; keys and every business column
compared across both paths, and the balance by warehouse and SKU; SCD snapshots and the incremental
fact rebuilt together, with `run_results.json` kept; when the stock ledger is affected, the producer,
duplicates and alerts exercised again, with `LIMITE`, `SEED` and the offset of
`.stream/producer_state.json` recorded, and the increment checked against the full rebuild, the
invariants and P13 on the common cut; the triggered DAG run followed to its end; the recorded
operating state restored. Both sources: the legacy source regenerated by the same engine
and captured again, with a new certified capture and the retained history preserved. D62, D63 and
D64 stay declared limitations in the release evidence (N14): the sink converging does not prove the
alert right, and the Fernet key affects Airflow Connections and Variables, not the current DAG.
Current measured records are updated afterwards; accepted ADRs and historical measurements are not
rewritten.

**The recovery package follows its own rules**
([Capacity and Recovery §§3.3–3.4](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/capacidade_e_recuperacao.md#33-regras);
RV2-06). Before anything destructive: the approved package verified, and the rollback cut
identified — what state it preserves, with which code and configuration, and what would be lost
after it. The maintenance code is committed before packing, because `pack` refuses a dirty tree.
After the regeneration, a candidate is packed, restored through the nine-step sequence with its
oracles — a second destructive window, under `RESTAURAR=1` and with your authorisation —, and only
then promoted. The previous approved package stays until the promotion. A rollback follows the
recovery procedure, which rebuilds around the restored SCD memory, and never the regeneration step
that drops it.

**Side effects:** the real outputs of the study trail come to describe the v1.0.0 data, and the
notice at the top goes in with its next update (N7); `ORD-0000037` changes content; so does the copy
of the trail in the Artifact.

### 5.4 Refining the data governance (O6, N20)

- **Descriptions inherited only through transport** (RV2-08). The lineage graph is reused as
  infrastructure, not as proof of meaning: copy, sum, rounding, multiplication and cast share the
  same leaf (M21), and P01's aggregated revenue has a single immediate leaf of the same name.
  Inheritance therefore requires a conservative classification of the expression at every hop — a
  bare column reference, an alias or a value-preserving cast carries the value; aggregation,
  arithmetic, functions, generated fields and ambiguous unions require text. The existing leaf sets
  are not repurposed as that classifier, and a cast carries the value only when its types and domain
  prove it — an unknown or narrowing cast requires text. The legacy bridges
  inherit only through an explicit, reviewed declaration, because their `meta.lineage` skips the
  cleaning. The semantics of `sensitivity` do not change. A reasoned override written by hand
  survives regeneration. Counter-proofs: a same-name computed column — P01's revenue sum — that must
  not inherit, and a legacy bridge that inherits only with its declaration.
- **Written text for the computed columns** — keys, measures, flags and renamed columns —, starting
  with `analytics` and `consumption`. It is a declaration: reviewed in full by you. Its volume is not
  bounded by M18, which used the shortcut M21 disproves.
- **`domain` and `owner`** on the 41 objects that lack them, as §5.1 already requires (M17).
- **A ratchet with floors per layer** (RV2-09), like the classification ratchet of
  `test_classificacao.py`, over the inventory of materialised columns, so that an omitted column
  cannot pass vacuously. Stage 1.7 introduces it with each floor at today's measured coverage; stage
  1.8 raises `analytics` and `consumption` to 100% only after you approve the text. Portal coverage
  is stated as such, apart from project-wide completeness.
- **Cost measured, not assumed** (RV2-10). One complete derivation takes about 21.6 s, and
  `make catalog` and the lineage test already derive separately. The new check shares one derivation
  with the classification and lineage checks and their test fixtures; any cache is invalidated by its
  actual inputs; and the added end-to-end cost of `make check` is measured in stage 1.7.
- Adjustments the portal reveals go in here, in the declaration — never in the generated output.

### 5.5 Out of v1.1.0

D62, D63 and D64 (N14). The consumption contract of the dimensional model (N16). Where v1.1.0 gets
recorded in eng_dados — its plan ends at Stage 13 — is decided in the runbook of stage 1.4.

### 5.6 What eng_dados records (O8)

Only the references it needs, each in the document that owns the subject there:

- the ADR for O2 (stage 1.2);
- a short entry for v1.1.0, with the justification for changing the database — M3, M7 to M9 and
  M17 — and a link to this plan (stage 1.9);
- the registration, in `docs/segredos_tratados.yml`, of a false positive the history sweep has
  flagged since 2026-10-13: the Makefile line of commit `e3c226c` that sets `PGPASSWORD` from the
  variable `$(1)_DB_PASSWORD` is a reference to a variable, not a value. The fix of `ba8244a`
  cleaned the current file, but the old blob stays in history, and `make secrets-history` has
  exited with an error ever since (measured on 2026-10-22: one untreated finding, that one). Stage
  1.9 brings it back to green.

---

## 6. Stages and effort

### 6.1 How to read the effort

**Effort** is the `/effort` level recommended for Claude Code at each stage — switch at the boundary
between stages. **Size** is an estimate, not a measurement: it serves to order the work, not to
promise a deadline.

| Effort | When |
|---|---|
| `low` | No stage of this plan: all of them touch data, governance, access or publishing |
| `medium` | A closed specification and contained risk: founding a repository, probing, publishing |
| `high` | Development with tests and moderate semantic or security risk |
| `xhigh` | Subtle semantics, where an error looks right, or text that will represent the project: the regeneration runbook, the encryption envelope and access, description inheritance, the descriptions, the overview, the portal, the lesson, the writing of the governance study |
| `max` | A long, destructive operation on the machine, with many failure modes. The comparable cycle, B5, found eight deviations |

| Size | Estimate |
|---|---|
| S | One session |
| M | One to two full sessions |
| L | Several sessions, with pauses for decisions or review |

### 6.2 The stages

**Part I — eng_dados v1.1.0**

| Stage | Deliverable | Effort | Size | Depends on | Criterion to move on |
|---|---|---|---|---|---|
| **1.1** | Order count with the source (§5.1) | `high` | S | — | The new test fails before the fix and passes after; M3 redone gives zero; `make check` green |
| **1.2** | The ADR for O2 (N8) | `high` | S | — | `verificar.py` with no orphan pending item; `make check-offline` green |
| **1.3** | Lineage as JSON and the exporter's read-only login (N4) | `high` | S | — | The output contains the 14 edges of M12; the login, through an actual non-superuser connection, reads `consumption`, is refused on the other layers, cannot write and cannot escalate; `make check` green |
| **1.4** | Runbook for the data fix: every checkpoint of Local Execution §3.2 mapped to a command, an oracle and a restart point; the rollback cut; the recovery-package lifecycle (§5.3) — reviewed by Codex | `xhigh` | M | — | Codex with no blocking finding |
| **1.5** | The three fixes in the generator, invariant 14 and the tests that need no database | `high` | M | 1.4 | In-memory generation deterministic; M7–M9 redone on it; `make check-offline` green |
| **1.6** | Regeneration, the full cycle and the new recovery package | `max` | L | 1.5, the maintenance code committed and your authorisation — twice: the regeneration and the restore window | `make check` green, with the count differences explained; legacy capture certified and history preserved; event content and balances equal across both paths; the triggered DAG run finished; the candidate package restored through the nine steps with their oracles, then promoted, with the previous one kept until then; M3 and M7–M9 redone in the warehouse; the operating state restored |
| **1.7** | Description inheritance through transport, the per-layer ratchet and its measured cost (§5.4) | `xhigh` | M–L, pending a prototype of the conservative inheritance | — | Counter-proofs: a carried column inherits; a same-name computed column and an undeclared legacy bridge do not; floors at today's coverage; the added `make check` cost measured; `make check` green |
| **1.8** | Text for the computed columns; `domain` and `owner` on the 41 objects | `xhigh` | M–L, not bounded by M18 | 1.7 | The floors of `analytics` and `consumption` at 100%, after your full review of the text |
| **1.9** | Documents — including the references of §5.6 —, review by Codex, acceptance and tag `v1.1.0` | `high` | M | 1.1–1.8 | `make secrets-history` green; the Owner's acceptance; push authorised |

**Part II — the `bi-como-codigo` showcase**

| Stage | Deliverable | Effort | Size | Depends on | Criterion to move on |
|---|---|---|---|---|---|
| **2.1** | Complete the foundation: the full conventions, skills, the secret guard, README with objective and map — the repository already exists, with this plan, the review and the evidence (N25) | `medium` | S | — | Secret guard green, with the two demo passwords registered as public by design |
| **2.2** | A Firebase project of its own and the trusted workflow of §3.4 — candidate and publishing workflows, federation bound to the publishing workflow on `main`, previews, promotion by version ID, one promotion at a time —, on harmless fixtures only | `high` | M–L | 2.1 | A test PR gets a preview, and its promotion is the same version ID; a fork's PR gets no credentials; a same-repository PR that changes the checker or `firebase.json` gets no preview and no live update; a preview advanced after approval and a rerun of an older job do not replace the current release; a tampered manifest and a planted clear file are rejected and nothing is uploaded; federation accepts the publishing workflow on `main` in its environment and rejects another workflow, another ref and another environment; no stored key |
| **2.2a** | The encryption envelope (§3.6): the byte-level format frozen, a reference implementation, the browser latency measured to set the iterations, and the negative tests — design reviewed by Codex | `xhigh` | M | 2.1 | An independently implemented reader consumes a fixed, complete envelope vector; known-answer vectors pass in both implementations; every negative case of §3.6 rejected; Codex with no blocking finding on the design |
| **2.2b** | The complete package-to-artifact gate of §3.4 in the publishing workflow, on encrypted fixtures: the decryption matrix, the control totals and the mutation tests | `high` | S–M | 2.2, 2.2a | Every mutation of §3.4 rejected by the publishing workflow before any upload |
| **2.3** | Comparative prototype of the framework on P01, opening a report encrypted with the envelope | `high` | M | 2.2a | The same page in each candidate, with what each cost and what was missing; the finished build output of each inspected — a candidate that runs report queries over clear data at build time fails; you choose |
| **2.4** | Exporters: the 16 views through the source-to-package gate (§3.4), encrypted on your machine; the governance metadata as JSON | `high` | M | 1.3, 1.9, 2.2b | One consistent read; contract, grain, nulls and decimals checked; typed rows equal to the views after the round trip; the mutation tests of §3.4 caught; no clear report data in Git |
| **2.5** | The complete P01 report | `high` | M | 2.3, 2.4 | Filter, chart and table agree with the package, checked in a headless browser; keyboard and focus; 360 px; light and dark; partial month and empty slice |
| **2.6** | Per-profile access in the product (O7, N23): the login screen with the explanation and the credentials, profile switching and logout, and the P13 report at its native grain | `xhigh` | M | 2.2b, 2.5 | The whole matrix through actual unwrap and decrypt in the browser, against the preview; switching to Logística leaves no Diretoria data visible; P13's averages never re-aggregated (M20) |
| **2.7** | Reading portal of the data governance (§3.2) | `xhigh` | L | 1.8, 2.4 | The nine chapters and the short route from question to report to column; every number with its source and date; every warehouse object reachable through search; missing metadata labelled; declared, executed and open kept apart; no text that contradicts the declaration |
| **2.8** | Governance of the project | `high` | M | 2.4 | Every statement points to a document, ADR or history entry at the pinned commit |
| **2.9** | Executive overview | `xhigh` | M | 2.5–2.8 | Read on its own by an outsider, with no presenter; every number generated |
| **2.10** | Validation, review by Codex, the first publication by promotion of the approved preview, and the portfolio link (N12) | `high` | M | 2.2b, 2.9 and authorisation | Codex with no blocking finding; live is the approved preview version, promoted by its ID; the link on project A, with your push to the portfolio |
| **2.11** | The other fourteen reports, in batches by domain | `high` | L | 2.10 | Per report: the audit of its view for non-additivity, time-dependent balances and truncated populations; an oracle against the view; ratios only through numerator and denominator; the access matrix still proven |
| **2.12** | The dimensional model for exploration and detail, only when a report asks for it (N16) | `xhigh` | L | An ADR in eng_dados | Consumption contract applied; each published table reproduces its source |

**Part III — the study content**

| Stage | Deliverable | Effort | Size | Depends on | Criterion to move on |
|---|---|---|---|---|---|
| **3.1** | Probe on claude.ai: a private Artifact with DuckDB-WASM and its worker from jsDelivr, a report encrypted with the agreed envelope, and the read of a file published by URL with its cross-origin headers | `medium` | S | 2.2, 2.2a | Everything works → study content in the Artifact; any item fails → `*.web.app` (N18) |
| **3.2** | The `caderno-de-dados` repository and the study site | `medium` | S | 3.1, 2.10 | Secret guard green; the site reads the published showcase reports |
| **3.3** | The P01 lesson, from the view to the source | `xhigh` | L | 1.3, 1.9, 3.2 | The five proofs of [`REVIEW.md` §3.4](REVIEW.md#34-a-small-example-that-actually-takes-part-in-the-result), each with its checking query kept; no statement without evidence |
| **3.4** | Study of the governance: inventory and outline, reviewed by Codex | `high` | S | 1.9 | Each mechanism with its source, incident and planned lab |
| **3.5** | Study of the governance: writing, mechanism by mechanism | `xhigh` | L | 3.2, 3.4 | Every statement points to code or an ADR at a pinned commit; every "value" points to a recorded incident |
| **3.6** | Study of the governance: labs actually executed | `high` | M | 3.5 | Every pasted output comes from a recorded run, with its date; the state of the machine handed back |
| **3.7** | SQL explorations and the link to the study trail | `high` | M | 3.2 | Queries over the showcase reports working on the study site |
| **3.8** | Study clock on `caderno-de-dados` (N10) | `medium` | S | 3.2 | Minutes recorded with the same rule as the study trail |

### 6.3 Recommended order

1. **1.1, 1.2 and 1.4.** While Codex reviews the runbook of 1.4, settle the inheritance semantics and
   the ratchet bootstrap of §5.4, then run **1.7 and 1.8**. Then **1.5 and 1.6** — the critical
   path, with its two destructive windows. **1.3** at any point; **1.9** last, for the final review,
   the acceptance and the tag.
2. In parallel with Part I, on disposable fixtures only: **2.1, 2.2a, 2.2, 2.2b, 2.3 and 3.1**. No real
   report data reaches Hosting before the gates of §3.4 exist.
3. After 1.9: **2.4 to 2.10** — the first publication carries the overview, P01 and P13 with the
   per-profile access, the portal and the governance of the project, promoted from its approved
   preview —; then **2.11** in batches.
4. After 2.10 and 3.1: **3.2 to 3.8**.

---

## 7. What is still decided, at the right moment

Every design question is answered (§1.2). Two kinds of decision remain.

**Choices that stand unless you object:** the restricted profile is **Logística, with P13 only** —
you delegated the choice, and it is the one the story explains best; lineage arrives through the
`--json` of eng_dados (the former N11); the lesson reads the inner layers through the custodian, in
a read-only transaction, with no new role (the former N5).

**Decisions that only fit during execution** — work stops until you answer:

- the framework, after the prototype of stage 2.3;
- the authorisation of the regeneration and of the restore window, in 1.6 — both destructive;
- the full review of the written descriptions, at 1.8;
- the acceptance of v1.1.0 and every push, from 1.9 onwards;
- the creation of `caderno-de-dados` and of the Firebase project, at 3.2 and 2.2 — done by you or
  with your authorisation; `bi-como-codigo` already exists (N25);
- the ADRs for the new components of each repository — hosting, CI pipeline and per-profile
  encryption —, recorded as each one is born;
- if federated credentials with the Firebase CLI prove infeasible in 2.2, the way forward comes
  back to you; N15 stands until then;
- if a report needs averages re-aggregated beyond the grain of its view, the sufficient statistics
  require an upstream contract change, with an ADR in eng_dados — yours to decide (M20);
- the result of the probe of stage 3.1 needs no decision: the rule of N18 already says what to do.

---

## 8. Risks

| Risk | Treatment |
|---|---|
| The regeneration breaks what no test covers | A reviewed runbook (1.4) with every checkpoint mapped, the approved package verified beforehand, one step at a time with an oracle, a written rollback cut |
| The recovery package stops representing the state | Candidate packed after the regeneration, restored through the nine steps, then promoted; the previous one kept until then (§5.3) |
| Machine memory (R11) | Only the guarded targets; a refusal for memory stops and asks the Owner, never `FORCE=1` on our own |
| An inherited description with the wrong meaning | Inheritance only through transport at every hop; legacy bridges only by declaration; disagreement written by hand with a reason; inherited text reviewed by sample and written text in full |
| The showcase states what the record does not support | Every number generated from a record at a pinned commit; Codex reviews the showcase before the first publication |
| Clear report data reaching the public repository or Hosting | Encryption at the export on your machine; an explicit inclusion list; the finished output inspected by content, previews included (§3.4) |
| Untrusted code deploying | Candidate code builds without credentials; the publishing workflow runs only reviewed code from `main` and treats the candidate as data; federation bound to that workflow; promotion by version ID, one at a time, superseded candidates rejected (§3.4) |
| Equal fields read as equal bytes | One canonical serialisation of the authenticated data, and expected identities taken from the validated manifest (§3.6; M23) |
| A framework that prerenders report rows | The prototype inspects the finished output of each candidate (2.3) |
| Federated credentials do not work with the Firebase CLI | Proved in 2.2 on fixtures; if not, the way forward comes back to you (§7) |
| A wrong package passing as consistent | Row-level equality with the views and mutation tests (§3.4; M19) |
| The encryption built wrong — a repeated key/IV pair, weak derivation, a key or a Parquet in the clear | The envelope of §3.6, fixed parameters, a fresh data key per encryption, the negative tests and the artifact inspection; Codex reviews the design before the prototype |
| A public password flagged by the secret guard | Both credentials registered as public by design, with the reason (N22) |
| The portal becomes the whole graph again | Lineage one hop at a time; narrative by chapters before the reference; the short route from question to column |
| The daily quota of free Firebase | Engine from jsDelivr; each page loads only its own files; separate projects |
| jsDelivr being down turns off interactivity | Accepted in N2; the page shows the error instead of stale or empty numbers |
| claude.ai limits the study content | The probe of stage 3.1 decides before building; the rule of N18 sends it to a `*.web.app` |
| An average or ratio re-aggregated wrongly | Native grain without sufficient statistics (M20); numerator and denominator otherwise; the per-report audit |
| eng_dados changes and a site diverges silently | The accepted contract pinned here and anchors at a pinned commit: export and build fail loudly |
| A partial dbt manifest after a `dbt --select` | The exporter rejects lineage with problems, as `lineage.main` already does |
| Volume nobody reviews (R14) | Reports, portal chapters, access rules and the lesson path are declarations in text, reviewed in full; what is generated, by oracle |

---

## 9. Not verified, and assumptions

**Not verified:**

- whether DuckDB-WASM, its worker, WebCrypto and a cross-origin read work inside the claude.ai
  Artifact — 3.1 measures it;
- how long the key derivation takes in the browser, with the chosen iterations — 2.2a measures it;
- whether the Firebase CLI accepts federated credentials from GitHub in practice — only community
  guides describe it —, and whether deploy and clone run inside a `workflow_run` job bound to
  `workflow_ref` — 2.2 proves both;
- whether each framework candidate can keep report queries away from build time — 2.3 inspects it;
- whether the chosen framework bundles DuckDB-WASM into the site itself or accepts jsDelivr;
- what Firebase does when the Spark plan runs over its quota;
- whether any query, test or document of eng_dados depends on today's category names or on the
  single price range — 1.4 finds out;
- the volume of description text to write — 1.7 measures what remains after conservative inheritance;
- the time and memory of the regeneration and of the restore window with the new data;
- whether the change to §4 of Governance affects any classification or access test;
- accessibility and usability of the sites.

**Assumptions:**

- eng_dados remains the single source of the data, the rules and the governance; the new
  repositories neither recompute metrics nor rewrite metadata;
- the data only changes through a deliberate regeneration, so updating is rare;
- reports, chapters, access rules and the lesson path stay small enough, as text, for a full review.

---

## 10. Review by Codex

The review of this plan is closed: round 5 closed RV4-01, RV3-02 and RV2-05 at the plan level, with
no new finding. Closure means that the plan requires the work and its exit evidence, not that any
gate has passed — the acceptance and rejection tests of stage 2.2 and every other exit criterion
of §6.2 remain to be proved. The next reviews by Codex are the ones the stages of §6.2 call for,
starting with the runbook of 1.4.

The probes re-run with the eng_dados databases up (`make up`) and nothing else:
`evidence/20261022/ro.sh <file.sql>`, with `ENG_DADOS_DIR` pointing at the eng_dados checkout,
always in a read-only session. The Python probes need only the `.venv` of eng_dados and a complete
dbt manifest; the Parquet export, `uv`. See [`evidence/20261022/README.md`](evidence/20261022/README.md)
and [`evidence/20261023/README.md`](evidence/20261023/README.md).
