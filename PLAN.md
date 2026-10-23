# Plan — bi-como-codigo and the study content

> **What lives here:** the plan for the two new pieces of content — the `bi-como-codigo` showcase and
> the study content — and for the maintenance release of eng_dados they require: what gets built,
> the architecture, the impacts of the separation, the stages with the effort of each, the Owner's
> decisions, taken and pending, and what was measured to support all of it.
>
> **What does not:** the original proposal by Codex and the review of it (see
> [`REVIEW.md`](REVIEW.md): §§1–11 and findings RP-01 to RP-15); what eng_dados is and how it is
> operated (see its [README](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/README.md)
> and [Local Execution](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/execucao_local.md));
> the decisions, once recorded — they become ADRs in the repository that owns them.

| Field | Information |
|---|---|
| Date | 2026-10-22 — revision 6: the separation from eng_dados, the language of construction and the public repository recorded (O8, N24, N25); ready for review by Codex |
| Author | Claude Code, at the Owner's request |
| Base | eng_dados at `26b58b3` |
| Status | **Complete proposal.** Nothing implemented. Every decision of the Owner taken (§1.2); review by Codex pending (§10) |
| Nature | Lives in this repository. At stage 3.2, Part III moves to `caderno-de-dados`; Part I becomes ADRs and pending items in eng_dados |
| Evidence | [`evidence/20261022/`](evidence/20261022/): read-only SQL probes, the lineage prototype, the Parquet export, the DuckDB engine measurement, catalogue coverage, the literal outputs and the `ro.sh` that re-runs the probes |
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

---

## 2. What was measured

Read in a `default_transaction_read_only=on` session on the running warehouse, between 2026-10-23
00:12Z and 01:22Z (2026-10-22, 21:12 to 22:22 in Brasília), on commit `26b58b3`. The view was read
as `analyst`; the inner layers, by the superuser in the same read-only session; the files, with no
database. Literal outputs in the evidence folder.

| # | What | Result | Consequence |
|---|---|---|---|
| M1 | The P01 view | 1,140 rows; 33 months (2024-01 to 2026-09); 3 channels; 4 root categories and 12 leaves; R$ 33,076,529.47 of net revenue; ~96 kB as text | — |
| M2 | P01 recomputed from the fact table, at the same grain | 0 rows diverging in count or revenue | An oracle ready for the exporter |
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
| M18 | Descriptions inheritable through lineage — an estimate | The 418 source columns have descriptions declared in the SQLAlchemy models. Without a description and with a single leaf of the same name: 357 in `analytics`, 113 in `consumption`, 198 in `trusted`. Needing text — renamed leaf, several leaves or none —: 94 in `analytics`, 44 in `consumption`; in `trusted`, 815, mostly because the `union` of the two sources shows up as two leaves of the same name | The mechanism that already derives classification can derive descriptions; written text is left for the computed columns. The same name does not guarantee the same meaning: this is an estimate |

**Read from official sources on 2026-10-22 — not measured:**

| Source | What it says |
|---|---|
| [Firebase](https://firebase.google.com/pricing), Spark plan | Hosting: 10 GB of storage and 360 MB/day of transfer; on Blaze, US$ 0.026/GB and US$ 0.15/GB beyond that. What happens when Spark runs over the quota, the page does not say |
| [Firestore](https://firebase.google.com/docs/firestore/quotas), free quota | 1 GiB stored; 50 thousand reads, 20 thousand writes and 20 thousand deletes a day; 10 GiB/month of egress; documents up to 1 MiB |
| [Cloud Storage for Firebase](https://firebase.google.com/docs/storage/faqs-storage-changes-announced-sept-2024) | Requires the Blaze plan, including the default bucket; on Spark, calls answer 402 or 403 |
| [Firebase Authentication](https://firebase.google.com/docs/auth/flutter/manage-users) | A signed-in user can change their own password and delete their own account through the client SDK; those actions require a recent sign-in |
| [Neon](https://neon.com/pricing), Free plan | 1 GB per project; 100 CU-hours; suspends after 5 idle minutes; 5 GB/month of public transfer — once exceeded, compute stays suspended until the next period |
| [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) | Published site up to 1 GB; 100 GB/month of bandwidth, a soft limit |
| GitHub API | Evidence: release of 2026-02-06 and last push on 2026-10-22, MIT. Observable Framework: release of 2026-03-02 and last push on 2026-05-15, ISC. DuckDB-WASM: last push on 2026-10-22, MIT |

**Not measured:** site build time; how any framework behaves with this data; DuckDB and WebCrypto
inside the claude.ai Artifact; the time to open the keys in the browser; usability; the effect of
the fixes on the tests of eng_dados.

---

## 3. What gets built

### 3.1 The two pieces of content

| | **Showcase — `bi-como-codigo`** | **Study — `caderno-de-dados`** |
|---|---|---|
| For whom | Whoever evaluates your work, in minutes, without you there | You |
| Tone | A self-sufficient executive presentation | Exploration, lab, questions |
| Content | Overview; reports for the 16 questions, with per-profile access; reading portal of the data governance; governance of the project | Lessons from the view to the source; study of the governance; SQL explorations; link to the study trail |
| Data | Parquet of the 16 views, encrypted per report; public governance metadata, generated from eng_dados | The showcase reports, read by URL and opened with the password of Diretoria; its own capture for the lessons |
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
  the review: partial month flagged (M5); a slice with no sale said as such (M6); `order_count`
  never added up across categories (M4); ratios re-aggregated only through numerator and
  denominator; no filter the view does not offer; no metric redefined in the report.
- **Per-profile access (O7, N23).** Hiding a report in JavaScript is not access control: the file
  could still be downloaded by URL, and an evaluator sees that in the network tab. And an account in
  Firebase Authentication does not make the password immutable: a signed-in visitor can change it
  or delete the account (§2). Hence **the password becomes the key**:
  - two profiles, declared once in the code: **Diretoria**, which opens the 16 reports, and
    **Logística**, which opens only **P13** — on-time delivery by carrier. Whoever handles carriers
    needs no revenue, margin or payment data;
  - at publication, the CI pipeline encrypts the Parquet of each report with a key of its own
    (AES-GCM, a random initialisation vector per file). The password of each profile derives,
    through PBKDF2 with a salt of its own, the key that wraps only the keys of that profile's reports
    (AES-KW). This is envelope encryption with several recipients, the same idea as SOPS and age;
  - in the browser, WebCrypto derives the key again from the password, unwraps the keys the profile
    is entitled to and decrypts only those reports. A wrong password opens nothing;
  - the password is truly immutable: there is no account to change or delete, and it only changes in
    a new publication, through a PR of yours;
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
  - the proof is by execution, like `test_acesso` in eng_dados: the build checks that the password
    of Logística opens P13 and fails on the other fifteen, that the one of Diretoria opens them all
    and that no Parquet reaches Hosting in the clear. In the showcase, Logística is invited to open
    another report and sees that its key does not open it.
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
eng_dados, on your machine      bi-como-codigo (GitHub)                    Firebase Hosting           browser
warehouse_db ─exporter─▶ Parquet + manifest ─PR─▶ Actions: checks, ─▶ PR preview
repository ──exporter─▶ metadata (JSON)            encrypts, builds └merge─▶ app, pages and     ─▶ password → key,
                                                                             encrypted reports      DuckDB-WASM
study (GitHub) ── lessons and its own capture ──▶ Artifact or *.web.app ◀── URL + password of Diretoria
```

- The exporters run only on your machine: the warehouse is never reachable from the internet, and
  the CI pipeline never reads it.
- The package **manifest** travels with the Parquet: row count, the sum of each measure and the hash
  of each file, the eng_dados version and the time of the read. The CI pipeline rejects a package
  whose manifest does not match, and then nothing is published — the live version stays.
- **Updating means opening a PR** with the new package: the preview shows the result, the diff of
  the manifest shows what changed, and the merge publishes.
- The CI pipeline encrypts each report before building; no Parquet reaches Hosting in the clear —
  the build checks this, and fails if it finds one.

### 3.5 The contract with eng_dados

Every crossing between the repositories is explicit and versioned.

| What is used | How | Why |
|---|---|---|
| The 16 views | Read by a login that is a member of `analyst` (N4) | The database itself guarantees the exporter only reads consumption |
| The dimensional model | Out for now (N16); if a report asks for detail, through a consumption contract, with an ADR in eng_dados | [Governance §7](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#7-regras-de-acesso-por-camada) and [ADR-0008](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/adr/0008-schemas-do-armazem.md) do not let a consumer read `analytics`, and [ADR-0018](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/adr/0018-fatos-e-views-a-partir-de-perguntas-de-negocio.md) rejected "one view per fact" |
| Governance metadata | Read from the repository at a pinned commit — dbt manifest, YAMLs, glossary, ADRs, documents —, with no access to the data | The portal is derived, not written; what changes in eng_dados changes in the portal at the next export |
| The contract of the views | Columns and types checked against the dbt manifest before exporting | A contract change in eng_dados fails loudly instead of becoming a wrong number |
| Column lineage | `python -m mvp_ed1.models.lineage --json`, run with the `.venv` of eng_dados (stage 1.3) | No second declaration of the lineage, and no dependency on internal code |
| SQL excerpts and documents | A text anchor per file, read with `git show <commit>:<path>` at a pinned commit; a GitHub link at that commit | An excerpt that disappeared breaks the build; links do not rot |
| Capture for the lessons | By the custodian: superuser, read-only `REPEATABLE READ` transaction, an explicit and rare command | It is the study-reading pattern eng_dados already uses (`make pgcli-*`); no new role |
| Version | eng_dados commit, `generated_at` of the dbt manifest, time of the read | "This warehouse was built by this commit" has no evidence today: it stays marked as not verified |

---

## 4. Impacts of the separation

| Aspect | Impact | Treatment |
|---|---|---|
| Scope of eng_dados | None: it stays complete, and BI stays out of it | Objective, scope and out of scope in the README of each new repository |
| Fixes and refinements in eng_dados | The separation does not spare them: the generator, the views and the governance declarations live there. The completed project reopens for a **maintenance release, v1.1.0**, with its own acceptance and tag | Part I |
| Access to the warehouse | The only login today is the superuser (Governance §7). Copying that password into another repository is what no real environment would do | A dedicated login, member of `analyst` (N4) — the "next step" that §7 itself already states |
| Access to the showcase | No new component: encryption is done by the CI pipeline and opened in the browser by WebCrypto (N23). Firebase Authentication and Firestore were left out | Stage 2.6; an ADR in `bi-como-codigo` |
| Environment | Exporting needs only the eng_dados databases up (`make up`) | — |
| Governance | The policy of eng_dados still owns the published data; each new repository states what it publishes and cites the ADR | Stage 1.2 |
| CI/CD | Out of scope for eng_dados (Charter §4); part of the product in the showcase | Stage 2.2, with identity federation, no stored key (N15) |
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
is a member of `analyst`, with its password in `.env`, and `test_acesso` gains the proof that it
reads `consumption` and nothing else.

### 5.3 Realism of the synthetic data (O3, N6)

| Fix, in the generator | Value | What changes |
|---|---|---|
| A declared category tree — leaf, middle and root coherent, still balanced | P01's axis gains business meaning (M7) | Names and parents of the categories |
| A price range per category | Comparing revenue across categories starts to mean something; closes the divergence between Generation §5 and the code (M8) | Every monetary value in the warehouse |
| Launch before sale, with invariant 14 | Closes D65 (M9) | Launch or sale dates; the SCD history of the product |

**Cost:** the regeneration of [Local Execution §3.2](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/execucao_local.md#32-regerar-uma-origem-que-já-alimenta-streaming)
— destructive maintenance, with the `FORCE=1` of the procedure itself —, the legacy source regenerated
by the same engine and captured again, `dbt build` and `make check`, streaming redone, the recovery
package redone (the approved one stops representing the state) and the documents that quote numbers.
**Side effects:** the real outputs of the study trail come to describe the v1.0.0 data, and the
notice at the top goes in with its next update (N7); `ORD-0000037` changes content; so does the copy
of the trail in the Artifact.

### 5.4 Refining the data governance (O6, N20)

- **Descriptions derived through lineage**, by the same mechanism that already derives the
  classification: the declaration stays in the SQLAlchemy models of the source — the 418 columns
  already described —, and a column that only carries a value inherits the text. Whoever disagrees
  with the inherited text writes the description by hand with a reason, as `sensitivity_reason`
  already does. The classification ratchet gains a sibling: a column without a description fails
  `make check`.
- **Written text for the computed columns** — keys, measures, flags and renamed columns —, starting
  with `analytics` and `consumption` (M18). It is a declaration: reviewed in full by you.
- **`domain` and `owner`** on the 41 objects that lack them, as §5.1 already requires (M17).
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
| `xhigh` | Subtle semantics, where an error looks right, or text that will represent the project: the regeneration runbook, the per-profile encryption, the descriptions, the overview, the portal, the lesson, the writing of the governance study |
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
| **1.3** | Lineage as JSON and the exporter's read-only login (N4) | `high` | S | — | The output contains the 14 edges of M12; the login reads `consumption` and is refused on the other layers; `make check` green |
| **1.4** | Runbook for the data fix: starting state, steps, oracles, rollback — reviewed by Codex | `xhigh` | M | — | Codex with no blocking finding |
| **1.5** | The three fixes in the generator, invariant 14 and the tests that need no database | `high` | M | 1.4 | In-memory generation deterministic; M7–M9 redone on it; `make check-offline` green |
| **1.6** | Regeneration and the full cycle on the machine | `max` | L | 1.5 and the Owner's authorisation | `make check` green, with the count differences explained; legacy capture certified; reconciliations; recovery package redone and checked; M3 and M7–M9 redone in the warehouse |
| **1.7** | Descriptions derived through lineage and the description ratchet (§5.4) | `high` | M | — | Counter-proof: a carrying column without text inherits, a computed column without text fails; `make check` green |
| **1.8** | Text for the computed columns; `domain` and `owner` on the 41 objects | `xhigh` | M | 1.7 | Description ratchet at 100% in `analytics` and `consumption`; your full review of the text |
| **1.9** | Documents — including the references of §5.6 —, review by Codex, acceptance and tag `v1.1.0` | `high` | M | 1.1–1.8 | `make secrets-history` green; the Owner's acceptance; push authorised |

**Part II — the `bi-como-codigo` showcase**

| Stage | Deliverable | Effort | Size | Depends on | Criterion to move on |
|---|---|---|---|---|---|
| **2.1** | Complete the foundation: the full conventions, skills, the secret guard, README with objective and map — the repository already exists, with this plan, the review and the evidence (N25) | `medium` | S | — | Secret guard green, with the two demo passwords registered as public by design |
| **2.2** | A Firebase project of its own and the CI pipeline: manifest check, build, preview per PR, publication on merge | `high` | M | 2.1 | A test PR builds a preview; a tampered manifest is rejected and nothing is published |
| **2.3** | Comparative prototype of the framework on P01, opening an encrypted Parquet | `high` | M | 2.1 | The same page in each candidate, with what each one cost and what was missing; you choose |
| **2.4** | Exporters: the 16 views as Parquet with the manifest; the governance metadata as JSON | `high` | M | 1.3, 1.9 | Each Parquet reproduces its view, with M2 generalised as the oracle; exact sums; rejects a diverging contract; the metadata matches the counts of the dbt manifest |
| **2.5** | The complete P01 report | `high` | M | 2.3, 2.4 | Filter, chart and table agree with the package, checked in a headless browser; keyboard and focus; 360 px; light and dark; partial month and empty slice |
| **2.6** | Per-profile access (O7, N23): the declaration of the profiles, encryption in the CI pipeline, opening in the browser, the login screen with the explanation and the credentials, and the P13 report | `xhigh` | M | 2.2, 2.5 | Matrix checked at build: the password of Logística opens P13 and fails on the other fifteen, the one of Diretoria opens them all; no Parquet in the clear on Hosting; no initialisation vector ever repeated; Codex reviews the encryption design |
| **2.7** | Reading portal of the data governance (§3.2) | `xhigh` | L | 1.8, 2.4 | The nine chapters; every number with its source and date; every warehouse object reachable through search; no text that contradicts the declaration |
| **2.8** | Governance of the project | `high` | M | 2.4 | Every statement points to a document, ADR or history entry at the pinned commit |
| **2.9** | Executive overview | `xhigh` | M | 2.5–2.8 | Read on its own by an outsider, with no presenter; every number generated |
| **2.10** | Validation, review by Codex, first publication and the portfolio link (N12) | `high` | M | 2.9 and authorisation | Codex with no blocking finding; the live site is the approved preview; the link on project A, with your push to the portfolio |
| **2.11** | The other fourteen reports, in batches by domain | `high` | L | 2.10 | Per report: an oracle against the view; ratios only through numerator and denominator; the access matrix still proven |
| **2.12** | The dimensional model for exploration and detail, only when a report asks for it (N16) | `xhigh` | L | An ADR in eng_dados | Consumption contract applied; each published table reproduces its source |

**Part III — the study content**

| Stage | Deliverable | Effort | Size | Depends on | Criterion to move on |
|---|---|---|---|---|---|
| **3.1** | Probe on claude.ai: a private Artifact with DuckDB-WASM, a worker, an encrypted Parquet opened by WebCrypto and the read of a file published by URL | `medium` | S | 2.2 | Everything works → study content in the Artifact; any item fails → `*.web.app` (N18) |
| **3.2** | The `caderno-de-dados` repository and the study site | `medium` | S | 3.1 | Secret guard green; the site reads the showcase reports |
| **3.3** | The P01 lesson, from the view to the source | `xhigh` | L | 1.3, 1.9, 2.4 | The five proofs of [`REVIEW.md` §3.4](REVIEW.md#34-a-small-example-that-actually-takes-part-in-the-result), each with its checking query kept; no statement without evidence |
| **3.4** | Study of the governance: inventory and outline, reviewed by Codex | `high` | S | 1.9 | Each mechanism with its source, incident and planned lab |
| **3.5** | Study of the governance: writing, mechanism by mechanism | `xhigh` | L | 3.4 | Every statement points to code or an ADR at a pinned commit; every "value" points to a recorded incident |
| **3.6** | Study of the governance: labs actually executed | `high` | M | 3.5 | Every pasted output comes from a recorded run, with its date; the state of the machine handed back |
| **3.7** | SQL explorations and the link to the study trail | `high` | M | 3.2 | Queries over the showcase reports working on the study site |
| **3.8** | Study clock on `caderno-de-dados` (N10) | `medium` | S | 3.2 | Minutes recorded with the same rule as the study trail |

### 6.3 Recommended order

1. **1.1, 1.2 and 1.4.** While Codex reviews the runbook of 1.4, **1.7 and 1.8** — the refinement
   does not depend on the data. Then **1.5 and 1.6**, the critical path: the longest stage, the only
   destructive one and the one most likely to surprise. **1.3** at any point; finally, **1.9**.
2. In parallel with Part I, because they do not touch the warehouse: **2.1, 2.2, 2.3 and 3.1**.
3. After 1.9: **2.4 to 2.10** — the first publication carries the overview, P01 and P13 with the
   per-profile access, the portal and the governance of the project —; then **2.11** in batches.
4. After 1.9 and 2.4: **3.2 to 3.8**.

---

## 7. What is still decided, at the right moment

Every design question is answered (§1.2). Two kinds of decision remain.

**Choices that stand unless you object:** the restricted profile is **Logística, with P13 only** —
you delegated the choice, and it is the one the story explains best; lineage arrives through the
`--json` of eng_dados (the former N11); the lesson reads the inner layers through the custodian, in
a read-only transaction, with no new role (the former N5).

**Decisions that only fit during execution** — work stops until you answer:

- the framework, after the prototype of stage 2.3;
- the authorisation of the regeneration, before 1.6, because it is destructive;
- the full review of the written descriptions, at 1.8;
- the acceptance of v1.1.0 and every push, from 1.9 onwards;
- the creation of `caderno-de-dados` and of the Firebase project, at 3.2 and 2.2 — done by you or
  with your authorisation; `bi-como-codigo` already exists (N25);
- the ADRs for the new components of each repository — hosting, CI pipeline and per-profile
  encryption —, recorded as each one is born;
- the result of the probe of stage 3.1 needs no decision: the rule of N18 already says what to do.

---

## 8. Risks

| Risk | Treatment |
|---|---|
| The regeneration breaks what no test covers | A reviewed runbook (1.4), the recovery package checked beforehand, one step at a time with an oracle, a written rollback |
| Machine memory (R11) | Only the guarded targets; a refusal for memory stops and asks the Owner, never `FORCE=1` on our own |
| An inherited description with the wrong meaning | Inheritance only for carried values; disagreement written by hand with a reason; inherited text reviewed by sample and written text in full |
| The showcase states what the record does not support | Every number generated from a record at a pinned commit; Codex reviews the showcase before the first publication |
| Encryption built wrong — repeated vector, weak derivation, a key or a Parquet in the clear on the site | Only standard WebCrypto primitives (PBKDF2 with many iterations, AES-KW, AES-GCM with a random vector per file); the build checks the matrix and the absence of clear text; Codex reviews the design before publication |
| A public password flagged by the secret guard | Both credentials registered as public by design, with the reason (N22) |
| The portal becomes the whole graph again | Lineage one hop at a time; narrative by chapters before the reference |
| The daily quota of free Firebase | Engine from jsDelivr; each page loads only its own files; separate projects |
| jsDelivr being down turns off interactivity | Accepted in N2; the page shows the error instead of stale or empty numbers |
| claude.ai limits the study content | The probe of stage 3.1 decides before building; the rule of N18 sends it to a `*.web.app` |
| A ratio re-aggregated as an average of averages | The rule of §3.2 and an oracle per report against the view |
| eng_dados changes and a site diverges silently | Contract checked and anchors at a pinned commit: export and build fail loudly |
| A partial dbt manifest after a `dbt --select` | The exporter rejects lineage with problems, as `lineage.main` already does |
| Volume nobody reviews (R14) | Reports, portal chapters, access rules and the lesson path are declarations in text, reviewed in full; what is generated, by oracle |

---

## 9. Not verified, and assumptions

**Not verified:**

- whether DuckDB-WASM, the worker and WebCrypto work inside the claude.ai Artifact — 3.1 measures it;
- how long the key derivation takes in the browser, with the chosen iterations — 2.6 measures it;
- what Firebase does when the Spark plan runs over its quota;
- whether the chosen framework bundles DuckDB-WASM into the site itself or accepts jsDelivr;
- identity federation from GitHub to Firebase, in practice;
- whether any query, test or document of eng_dados depends on today's category names or on the
  single price range — 1.4 finds out;
- how many inherited descriptions need fixing by hand — M18 is an estimate;
- the time and memory of the regeneration with the new data;
- whether the change to §4 of Governance affects any classification or access test;
- accessibility and usability of the sites.

**Assumptions:**

- eng_dados remains the single source of the data, the rules and the governance; the new
  repositories neither recompute metrics nor rewrite metadata;
- the data only changes through a deliberate regeneration, so updating is rare;
- reports, chapters, access rules and the lesson path stay small enough, as text, for a full review.

---

## 10. Request for review by Codex

Review this plan against the code, the ADRs and the decisions O1–O8 and N1–N25 in §1. In particular:

1. does the architecture of §3.4 — manifest, PR and rejection — guarantee that nothing wrong is
   published?
2. is the per-profile encryption of §3.2 real access control, with standard primitives, no key and
   no Parquet in the clear, and is the proof at build enough?
3. does §5.3 underestimate the cost or the effect of the regeneration?
4. is §5.4 — descriptions derived through lineage — the right mechanism, and does the new ratchet
   fit in `make check` without excessive cost?
5. does N16 read ADR-0008, ADR-0018 and Governance §7 correctly?
6. do the chapters of the portal (§3.2) tell the story a newcomer needs, in the right order?
7. do the order of §6.3, the dependencies and the effort of each stage hold?
8. is any decision missing, or should any of the pending ones not be the Owner's?

The probes re-run with the eng_dados databases up (`make up`) and nothing else:
`evidence/20261022/ro.sh <file.sql>`, with `ENG_DADOS_DIR` pointing at the eng_dados checkout,
always in a read-only session. The lineage prototype and the catalogue measurements need only the
`.venv` of eng_dados and a complete dbt manifest; the Parquet export, `uv`, as in the header of
`exportar.saida.txt`. See [`evidence/20261022/README.md`](evidence/20261022/README.md).
