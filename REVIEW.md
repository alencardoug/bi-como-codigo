# Plan review — a public site to learn the path of the data

> **From Codex to Claude Code, at the Owner's request.** This is a plan for critique, with ideas
> deliberately open to simplification or removal. The deliverable of that session is this document.
> Implementation, tool choice and publishing had not been carried out yet.
>
> A hand-over following the [`revisao` skill](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/.claude/skills/revisao/SKILL.md)
> of eng_dados, adapted to the review of a plan with no implementation yet. The Owner's live request
> keeps defining the role of each session.

| Field | Information |
|---|---|
| Date | 2026-10-22 |
| Author of the proposal | Codex |
| Intended reviewer | Claude Code |
| Base inspected | `26b58b33deac1ee89b9f7de1292ba40fec0d4de2` of eng_dados; clean tree before this file |
| Status | Review by Claude Code recorded (findings RP-01 to RP-15, at the end). The resulting plan, with every decision of the Owner, is in [`PLAN.md`](PLAN.md); next step: the review of the plan by Codex, requested in its §10 |
| Source of the constraints | The conversation with the Owner, the [CLAUDE.md of eng_dados](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/CLAUDE.md) and the code referenced below |
| Translation | Translated from Portuguese on 2026-10-22, at the Owner's request. The original is in commit `e046937` of this repository; literal command outputs are kept as recorded |

## 1. The request and the choices already made

The Owner wants to publish a site with the data map of eng_dados. The first goal is **to learn the
flow and the transformations**, starting from the analytical result and investigating how it was
produced. The dashboard should answer the questions that already justify the `consumption` views.

These choices came from the conversation and need not be asked again:

| Subject | The Owner's choice |
|---|---|
| First analysis | Start with one view: `consumption.monthly_revenue_by_channel_and_category`, P01 |
| Interaction | Interactive filters and charts |
| Learning | Click an indicator and follow one order item to its contribution in the result |
| Problem to solve | The current dependency map opens almost every table; exploration should be focused and illustrative, possibly by column |
| Updating | On request, **only re-reading the view**; the local engineering challenge is over |
| Who updates | Only the Owner; analysis and explanations are public |
| Complexity | A simple solution; updating can wait if it complicates the first delivery |
| Other ideas | Write down other ways of exploring, for Claude to judge which are worth it |

**Summary to guide the future implementation:** an educational dashboard for P01, linked to a
verifiable path of one order item. The explanation opens by stages and by column, shows the
transformations and rules that shape the result and reuses the existing project. The public
operation must work independently of the local machine; the Owner publishes new reads of the view
when he wants. That way of operating is the proposal of §4, still open to critique.

## 2. Review map and the sources that remain the reference

**Declaration of this delivery:** this review document, written by hand and subject to full review.
There is no code and no new generated artefact. The sections below hold proposals, not accepted
architectural decisions. The documents and models below remain the owners of the facts about the
project.

| Source | What to check or reuse |
|---|---|
| [Business questions — P01](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/glossario_de_negocio/perguntas_de_negocio.md#p01--qual-a-receita-líquida-por-mês-canal-e-categoria-de-produto) | The question, the measures and the existing slices |
| [The P01 view](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/dbt/models/consumption/monthly_revenue_by_channel_and_category.sql) | Published grain, dimensions, aggregations and the realised-sale filter |
| [Consumption contract](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/dbt/models/consumption/_consumption__models.yml) | Columns, types and classification; avoid inventing filters the view does not offer |
| [Revenue in `trusted`](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/dbt/models/trusted/order_items.sql) | The calculation and the exact point of rounding |
| [Orders in `trusted`](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/dbt/models/trusted/orders.sql) | The `is_realised` rule |
| [Item fact table](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/dbt/models/analytics/fact_sales_order_item.sql) | Source identity, date, dimensions and temporal joins |
| [Existing lineage](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/src/mvp_ed1/models/lineage.py) and [leaf derivation](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/src/mvp_ed1/models/sensitivity.py) | Immediate dependencies per column, terminal origins and the limits of the value rule |
| [Data dictionary, §3](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/dicionario_de_dados.md#3-linhagem) | Published lineage and the crossings outside dbt |
| [Study trail](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/CONVERSAS_COM_CHAT/trilha_de_estudo_fase_local.html) | The existing journey, historical examples, navigation and map; assess reuse |
| [Governance](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md) | Classification and access; the analytical consumer reads `consumption` |
| [ADR-0018](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/adr/0018-fatos-e-views-a-partir-de-perguntas-de-negocio.md) | Questions before views, and an enforced contract |

The site will be a didactic presentation derived from these sources. Metric definitions, SQL and
lineage must not gain a second manual declaration inside visual components. Didactic text may be
curated, with a reference to the file and version that support it. A divergence between document
and implementation must be recorded, not hidden by the presentation.

## 3. Proposed experience

### 3.1 One question and one analysis screen

Open with the question **"Qual a receita líquida por mês, canal e categoria de produto?"** (what is
the net revenue by month, channel and product category?), a short explanation, a note that the data
is synthetic and the extraction date. The first screen proposes:

- **monthly** period, channel and category filters, limited to the columns of the view;
- the net revenue of the slice as the main indicator;
- monthly evolution and a comparison by channel or category;
- an accessible table with the values behind the charts;
- an explicit action **"How was this value formed?"**, reachable by keyboard as well.

Gross revenue, discount and units may complement net revenue if they help tell the story. There is
no need to fill the screen with every field of the view. **Order count requires the analysis of §5.2
before it becomes an indicator.**

Filters must change charts, table and the context of the explanation consistently. Distinguish "no
result for this filter" from revenue equal to zero. Sort months chronologically and explain the
period coverage; a missing row does not prove, on its own, that there were no sales.

### 3.2 A didactic path with progressive disclosure

The click starts at the selected metric. The first explanation shows the calculation in business
language; then it offers the stages that support it. The proposal is a readable sequence of
connected cards, before justifying a graph library.

```text
Question and filters → indicator → explanation of the calculation
                                   ↓
                         verified order item
                                   ↓
                 expandable stages, columns and rules
```

The user may investigate backwards, but the **data flow** arrows keep the source → consumer
direction. The legend tells that direction apart from the navigation order.

Each stage shows: layer and object, relevant columns, input and output values, the operation applied
and its reason. The SQL excerpt sits next to the explanation, with the rest behind an expansion.
When a stage only carries the value, say so; do not invent a transformation to liven up the screen.

**Three questions organise the path:**

| Question | What to show |
|---|---|
| Where does the value come from? | Quantity, price and discount; the per-item calculation; the sum in consumption |
| Why does this sale fall in this group? | Realised sale, month of the sale, channel, category and the joins that determine its association |
| Which controls allow this data to be used? | Ingestion, eligible legacy capture, cleaning, quarantine and the other relevant dependencies |

The first opens by default. The others stay visible as additional paths, without expanding every
table at once. A control dependency must not be drawn as if it directly supplied the monetary value.

### 3.3 What to reuse from column lineage

The published lineage links `net_revenue_amount` to `quantity`, `unit_price` and `discount_amount`
of `order_items`, in both sources. The code keeps immediate leaves in `Lineage.leaves` and closes the
terminal origins in `origins()`. **Proposal:** assess extracting the intermediate path of those
leaves, preserving `meta.lineage` on the legacy bridges.

That mechanism follows the expressions that produce values. It is not, by itself, a complete
explanation of filters, conditions, join cardinality or a row's membership in a total. The legacy
source itself uses an explicit declaration to cross the shared payload. So do not promise "complete
automatic lineage" from it.

For P01, propose a small didactic declaration that **references** the existing rules and SQL
excerpts. Use it to organise the narrative and the complementary dependencies. The reviewer should
judge whether that is enough or whether it would add too much maintenance. Changing the project's
general classification/lineage algorithm is not a prerequisite of this first experience.

On the map, keep `retail` and `legacy` as identifiable branches; selecting a branch explains that
source. This **does not create a source filter on the dashboard**: the current view does not expose
`source_system`. Broad cleaning/certification dependencies may appear grouped, with an explanation
and optional expansion. The detail does not disappear; it stays outside the main path.

### 3.4 A small example that actually takes part in the result

Choose an identity made of `source_system` and `order_item_id`, keeping `order_id` where needed. The
same numeric identifier may exist in both sources. Starting with a `retail` item is a suggested
simplification; the legacy branch can be the next lesson.

The existing trail uses `ORD-0000037`. It is a **historical candidate**, not a confirmed current
sample. Choose or reconfirm the item with read-only queries. Prefer a case that explains price,
quantity and discount without needing many exceptions at once.

The sample must prove:

1. the identity of the item across the stages shown and the source/capture of each read;
2. the calculation in `trusted`, including the per-item rounding;
3. the passage through the fact table and the month, channel and category associations;
4. eligibility under the realised-sale rule;
5. the contribution to the exact group of the view, telling apart **the item's value**, **the other
   items** and **the group total**. The item illustrates the total; it does not replace it.

Reads in the warehouse must use a consistent state during the capture. A current read of `source_db`
and another of `warehouse_db` do not demonstrate a common cut between databases: prefer the raw
data already ingested to prove the state that feeds the warehouse; the crossing back to the source
uses the existing mapping and compatible evidence, or stays explicitly limited.

**Suggested simplification:** initially offer a known guided slice. If the visitor's filters exclude
the example, say so and offer "Open the example's slice". Do not pick a non-existent item, nor
present the sample as taking part in any chart.

### 3.5 Reconciling the sample with view-only updates

The view is aggregated: re-reading it does not recover the items that formed it. There are two data
products:

- **dashboard:** an extraction of the view, which the Owner may replace on request;
- **lesson:** a small, verified sample of the layers, with its own context and date.

In the first version, build both from one reconciled cut. In a future update limited to the view,
keep the lesson as a **historical example** and open the historical slice that was verified. Do not
claim the item still makes up the newly extracted total. Equal totals do not prove equal items
either.

This separation preserves the "view only" request. Updating the sample automatically would require
new reads of the layers and would be an extension to discuss. Claude should critique whether the
switch between current analysis and historical example is understandable; if not, prioritise a
first, fixed publication and postpone updating — an option the Owner has already accepted.

## 4. A simple way to implement and publish — a proposal for critique

### 4.1 Preferred alternative: a static site with a local export

```text
Owner, on the local machine
  → read the view in a read-only session
  → export and check a data package
  → publish the validated package with the site
  → visitors filter and explore the data in the browser
```

Preferring this alternative is a **simplicity hypothesis**, not a measurement of cost or
performance. It avoids depending on a local database reachable from the internet. The update
mechanism can be a documented local command, followed by publication by the Owner; an
administrative button inside the site is not a requirement of the conversation.

| Alternative | Benefit | Cost or limit to assess |
|---|---|---|
| A — local export and static hosting | Public operation independent of the database; updating controlled by the Owner's access to publishing | Requires export, validation and a publishing routine; package size not yet measured |
| B — a site with an API and an admin area | Updating through the interface | Adds a service, authentication and connectivity to the database; looks out of proportion to the first scope |
| C — a fixed first publication | The smallest scope to validate analysis and learning | Offers no new read of the view; an authorised alternative if updating delays the essentials |

Ask Claude to compare A and C first. Hosting, charting library and any framework remain unchosen.
No price, service-plan limit or estimated deadline is confirmed in this document. Tool choice follows
the Owner's process in `CLAUDE.md` §5.

### 4.2 Small pieces, separated by what changes

The reviewer should propose the definitive paths. As a conceptual organisation:

- **declaration of the analysis:** identification of the view, allowed fields, metrics, filters,
  formats and aggregation rules; prefer deriving from the contract what it already declares;
- **declaration of the path:** didactic sequence, references to the code, complementary relations
  and the identity of the example; without copying the whole business model;
- **local exporter:** reading the view and serialising it; the initial capture of the sample is a
  distinct operation, with its own permissions and provenance;
- **generated artefacts:** analysis data, didactic sample, lineage excerpts/edges and version
  metadata;
- **interface:** presentation and filter state, reading those artefacts.

A simple frontend in HTML, CSS and JavaScript is an option to compare; the project already has
material in that format. Reusing useful patterns from the trail does not mean publishing the whole
HTML: its content, images, examples and scripts must be selected for this public scope. Choose a
charting library only if it reduces interaction and accessibility work.

The package must identify its version, source view, extraction time, period covered, version of the
reference code and version/date of the sample. The exporter's commit does not prove which code built
the warehouse: record the build version only if there is evidence; otherwise, leave that link
unverified. Extraction time is not ingestion time either.

Public files must result from an explicit inclusion list. `dbt/target/`, `.env`, logs, credentials
and full dumps are not part of the package. The `.gitignore` already excludes `data/`, `dbt/target/`
and some data formats; decide consciously where the publishing artefacts live, without opening a
broad exception or using forced inclusion as a permanent design.

### 4.3 Update behaviour

Prepare the new extraction separately, validate contract and values, and only then promote the
published version. A read or validation failure keeps the last valid publication, with its date.
Record the error in the Owner's environment; do not show success nor change the date on the site.

The routine reads the existing view. It does not trigger Airbyte, a DAG, a dbt build, data
generation or streaming. If the view is missing or inconsistent, report the impediment; rebuilding
the flow is other work. Publishing must keep data, interface and version metadata compatible, to
avoid mixing old and new files through caching. The concrete solution depends on the hosting chosen.

### 4.4 Publication and the existing classification

Public publication was requested. Its implementation must represent that decision concretely: which
aggregated fields and which synthetic sample will be exposed. The current contract marks the
monetary values of P01 as `confidential`; the policy also restricts personal data, even synthetic.
This deserves explicit assessment by Claude, with reference to
[Governance, §§4 and 10](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#4-classificação-de-sensibilidade).

Proposal: declare the scope of the public demonstration and preserve the source classification; do
not switch generated metadata to `public` just to make the site possible. Define with the Owner the
record needed for publication and any access changes. Authorisation to read the view does not give
the visitor access to the intermediate layers.

The dashboard uses consumption access. The didactic sample is prepared in the Owner's authorised
study/audit context and publishes only the fields needed, with no name, document, e-mail, address or
full payload. The policy and the way to access those layers must be checked before the capture; do
not widen `analyst` or create a new role implicitly.

## 5. Semantic care that shapes the interface

### 5.1 Calculation and precision

The SQL of `trusted.order_items` computes revenue per item as
`round(quantity * unit_price, 2) - discount_amount`; the view sums the result over eligible items. An
explanation that rounds only the total may teach a different rule. Show the rounding where it
happens and keep exact values in the calculations that feed the interface.

Transport proposal: decimals as text with their scale preserved. To sum two-decimal monetary fields
in the browser, assess integer cents with a validated range, or decimal arithmetic. The unit price
has four decimals in the inspected code: do not blindly turn every monetary column into cents. If
the chart design uses a numeric approximation, the label and the total must come from the exact
calculation. No library chosen here.

The calendar of the slice follows the rule of the fact table, which takes the sale date in
`America/Sao_Paulo`. The category may depend on the version of the product at the time of the sale.
Do not swap those definitions for the extraction month or the current catalogue to make the
presentation easier.

### 5.2 Orders and the available slices

The SQL uses `count(distinct f.order_id)` per group. Summing the category counts does not guarantee
distinct orders in the total, because one order may have items in more than one category. The
aggregated view does not offer the identifiers needed to deduplicate again in the frontend.

There is a second question for the reviewer: the count does not include `source_system`, although
the sources may reuse `order_id`. **It is a risk identified by reading the SQL; no undercount was
measured in this session.** Check it before publishing that metric. Do not fix the view nor redefine
the question as a side effect of the site. Prioritising revenue and units in the MVP is a way to keep
the scope while the count is assessed.

P01 does not expose item, SKU, order, source or individual day. Exploring an example of those fields
in the lesson does not allow offering those filters in the aggregated analysis. A new slice requires
assessing the contract, not distributing existing totals by approximation.

## 6. Suggested sequence of work

| Stage | Deliverable | Criterion to move on |
|---|---|---|
| 1 — critique of this plan | Claude's opinion: feasibility, cuts, gaps, alternatives and the Owner's decisions | Minimum scope made explicit, without confusing suggestions with accepted choices |
| 2 — sketch of the experience | One screen and one revenue path, with interaction notes | The Owner can explain what he will learn; missing numbers stay pending |
| 3 — initial package | A read-only extraction of P01 and a reconciled sample, after deciding publication/access | Grain, identity, calculation, membership and provenance checked |
| 4 — usable local version | Filters, charts, table, progressive explanation and no-data states | Values match the extraction and the path stays understandable |
| 5 — first publication | A public site independent of local services | Published content matches the package and works by keyboard and on a narrow screen |
| 6 — on-demand update | The Owner's routine, if the effort pays off | Re-reads only the view, a failure keeps the previous version, and the lesson keeps its historical context |

There is no estimate in hours and no measured package volume. Ask Claude for a qualitative
assessment of effort per stage; any future estimate must be labelled as an estimate. Do not wait to
implement every way of exploring before validating the first question.

## 7. Additional ideas for Claude to critique

Everything in this section is a **suggestion**, not an approved requirement. Classify each idea as
keep, simplify, postpone or discard, explaining why.

| Idea | Value for learning | Dependency or risk | Suggested priority |
|---|---|---|---|
| A formula that highlights the matching column at each stage | Connects business language, SQL and data | Must preserve the real scale and rounding | Candidate for the first path |
| Before/after comparison, with changes highlighted | Explains rename, cast, cleaning and calculation | Many stages do not change the value; represent that honestly | Candidate for the first path |
| "Why does this sale count?" with filter and join highlighted | Explains the population of the metric, beyond the formula | Conditions do not come complete from value lineage | Candidate for the first path |
| Contextual glossary of grain, dimension, fact and view | Reduces the need to leave the analysis | Reference the existing glossary to avoid parallel definitions | Apparently small scope, not measured |
| A short question before revealing a transformation | Makes the visitor predict and then check | The answer must come from evidence; no gamification at first | Test after the basic path |
| A link that preserves filters and the lesson stage | Makes it easy to return to the study and share a slice | Must also preserve the version, or warn about data changes | Next improvement |
| Free navigation by column | Allows investigating beyond the script | May recreate the excessive map; demand focus and local expansion | After the guided P01 |
| The same field in `retail` and `legacy` | Shows two inputs arriving at the same contract | Equal keys do not prove the same sale; compare identified cases | Candidate next lesson |
| One rejection all the way to quarantine | Shows why not all data reaches the indicator | Choose a real case and avoid exposing the whole payload | Candidate next lesson |
| A map of the legacy control dependencies | Explains why so many tables appear in the current graph | Shared certification and cleaning need a narrative of their own | Extension of the legacy lesson |
| Category at sale time versus current category | Teaches history and temporal joins | Only worth it with an observed case and evidence of the versions | Postpone until an example is found |
| Comparing two extractions of P01 | Shows what changed in consumption | Two different totals do not explain the cause; needs additional evidence | Postpone |
| Quality evidence next to the stage | Links data, rule and verification | A test from another date does not prove the quality of the current extraction | Postpone, or show only a dated reference |
| Simulating the inclusion of unrealised orders | Explores the selection rule | Cannot be computed from the filtered view alone; would need another authorised set | Postpone |

Avoid making a chatbot, free SQL in the browser, a universal graph, access to every view or a
pipeline execution environment prerequisites of the first delivery. They are distinct scopes, with
no benefit demonstrated for the initial experience.

## 8. Proposed acceptance and validation criteria

**Learning:** at the end of the path, the Owner can locate the columns that form the revenue,
explain where it is calculated and rounded, why an item falls in the group and how its contribution
relates to the total. Make that assessment with the screen finished; a pretty design and a working
click, on their own, do not demonstrate learning.

**Correctness:** compare values per group and for representative slices with the view's query;
check monetary sums without loss of precision, the composite identity of the example and its joins,
and the handling of slices with no data. Do not create simulated results that look like measurements.
The sample must have extracted values and preserved checking queries.

**Navigation:** filter, chart and table agree; every expanded stage has a way back; arrows and
legends are consistent; differences do not depend on colour alone. Check keyboard, focus, contrast
and narrow screens in the implementation. Prefer links to source excerpts at the referenced version,
without depending on line numbers of a file that may change.

**Operation:** visiting the site neither queries nor changes the local machine. When implemented,
updating is exclusive to the Owner, re-reads only the view and keeps the previous publication if it
fails. Extraction dates and historical-example dates appear with their correct meanings.

**Review:** review in full the declarations of the analysis, the path and the public fields; check
the generated output by sample and reconciliation. Test what carries real risk — aggregation,
precision, membership, mixing of versions and publishing failure —, without adding an extensive
suite just to repeat the interface markup.

## 9. What was not verified, and assumptions

### Not verified in this delivery

- The state of the databases, the availability of the view and whether the current warehouse
  matches the commit read.
- Values, cardinality, extraction size and read/publish time.
- The candidate item, its participation in the group, compatibility between cuts and whether the
  sample eventually chosen has a discount or another illustrative transformation.
- Whether collisions occur in the order count of P01, and their impact.
- Completeness and freshness of `dbt/target/manifest.json`; a partially compiled manifest does not
  support generating a complete path.
- Hosting, libraries, costs, performance, accessibility and usability of the future site.
- The concrete solution for publishing the classified fields and for reading the layers for the
  sample.

### Assumptions to confirm

- The main goal is still to study the completed project, with a public demonstration.
- The aggregated slice of P01 probably fits in a static publication; **size not measured**.
- A small example with guided expansion should be more readable than the whole graph; **usability
  not tested**.
- The lineage artefacts can be reused without changing the general classification; the path to
  extract the intermediate edges still needs prototyping.

### Environment the review needs

To critique the plan, this checkout is enough. No service needs to start. Future data probes need
only the strictly necessary environment and read-only queries, as in
[Local Execution](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/execucao_local.md).
They are not part of the present documentary review.

The skill's generator was not run: it assumes a delivery in commits and runs `make check`, which
includes a dbt build. This plan was prepared by hand and its structure checked with
`dossie.py --conferir`; that does not validate the data nor the future site.

### Where I hesitated

- **Free graph or curated path:** I propose starting with the path; it leaves free exploration by
  column open once the first explanation is proven to work.
- **API or static package:** I propose the package; a local button or publishing routine meets the
  Owner-only update with fewer conceptual pieces, to be confirmed in the implementation.
- **Always-current or historical sample:** I propose a dated lesson, to respect re-reading only the
  view. The experience across versions needs judging by Claude and the Owner.
- **Every metric of the view, or revenue first:** I propose revenue first; the order count has
  limitations the interface cannot solve by summing aggregated rows.

## 10. Evidence of this preparation

What follows is **file inspection**, not an operational measurement. No database query, build,
installation or publication was executed. Historical examples from the trail were not re-measured
nor copied as if they were current results. Commands ran in the eng_dados checkout; outputs are kept
as recorded.

Command executed:

```bash
git log -1 --format='%H%n%cs%n%s'
```

Literal output:

```text
26b58b33deac1ee89b9f7de1292ba40fec0d4de2
2026-10-22
docs: mostra no R24 o caminho do source() até o nome da tabela, com ilustração
```

Command executed:

```bash
rg -n 'count\(distinct|sum\(f.net_revenue_amount\)|where f.is_realised|group by' dbt/models/consumption/monthly_revenue_by_channel_and_category.sql
```

Literal output:

```text
21:    count(distinct f.order_id)                      as order_count,
25:    sum(f.net_revenue_amount)                       as net_revenue_amount
30:where f.is_realised
31:group by 1, 2, 3, 4, 5, 6, 7
```

Command executed:

```bash
rg -n 'round\(quantity \* unit_price, 2\)' dbt/models/trusted/order_items.sql
```

Literal output:

```text
26:    round(quantity * unit_price, 2)                          as gross_revenue_amount,
28:    round(quantity * unit_price, 2) - discount_amount        as net_revenue_amount,
```

Command executed:

```bash
rg -n 'for projecao in consulta.selects|resultado\[projecao.alias_or_name\]' src/mvp_ed1/models/sensitivity.py
```

Literal output:

```text
352:            for projecao in consulta.selects:
353:                resultado[projecao.alias_or_name] = folhas_de(projecao, escopo)
```

Documentary check executed:

```bash
python3 .claude/skills/revisao/dossie.py --conferir
```

Literal output:

```text
dossiê completo: sem pendências e sem verificação falhando
```

The message checks the fill-in and failure markers the tool recognises. The decisions, hypotheses
and validations still open in the previous sections remain pending; that result is neither an
approval of the plan nor a feasibility test of the implementation.

## 11. Request for Claude Code's opinion

Assess this plan against the code, the ADRs and the choices the Owner has already recorded. The
answer should allow reducing the scope before implementing. In particular:

1. Does the proposed path teach the flow without hiding relevant filters, joins and controls?
2. What is the smallest convincing experience for P01? What can be cut right away?
3. Does the existing lineage offer a sufficient base? Which declarative complement would be needed?
4. Does separating an updated dashboard from a historical lesson preserve the Owner's intent
   clearly? If not, which alternative respects view-only updates?
5. Which interface, export and hosting option do you recommend, with trade-offs and decisions that
   belong to the Owner? What record is needed to publish the selected synthetic package?
6. Which data or aggregation limitations affect the first scope, and which can be postponed?
7. For each idea in §7, is the opinion keep, simplify, postpone or discard?
8. Which validations are still missing, and what would the order of execution be after the
   necessary decisions?

Record findings below and add the opinion, distinguishing code reading, hypothesis and measurement.
Do not mark suggestions of this plan as implemented or approved. When closing the review, keep the
decisions and the resulting plan in the appropriate documentary home before removing this transient
file, as the skill says; do not create a second copy of the plan now.

## Review findings

Filled in by Claude Code on 2026-10-22, from the checkout at `26b58b3` and read-only probes on the
running warehouse. The basis of each finding is marked: **reading** (of code or documents),
**measurement** (the Mn of the [plan](PLAN.md#2-what-was-measured), with literal outputs in
[`evidence/20261022/`](evidence/20261022/)) or **hypothesis**. No suggestion of this proposal was
implemented or approved by this review.

| # | Where | Finding | Verdict | Status |
|---|---|---|---|---|
| RP-01 | §1, §4, §6 | The proposal does not confront [Charter §4](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/Abertura_de_projeto.md#4-fora-do-escopo) and [Plan §6](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/plano_de_desenvolvimento.md#6-fora-deste-plano) of eng_dados: BI, dashboards and CI/CD are out of its scope, and a scope change goes through §10 of the Charter. **Reading** | `blocking` | Settled by the Owner's decision O1 (2026-10-22): a separate project, in a new repository. Impacts in [plan §4](PLAN.md#4-impacts-of-the-separation) |
| RP-02 | §4.4 | Classification is not just an obstacle to publication: the rule of Governance §4 for `confidential` — kept out of the views open to `analyst` — no longer holds today. 28 `confidential` columns in 10 `consumption` views are read by `analyst`, because the grant covers the whole layer. **Reading** of `_consumption__models.yml` and `dbt_project.yml` | `adjustment` | The Owner decided (O2) that no synthetic field is restricted in the analyses, and N8 (2026-10-22) fixed the scope: classifying is not exposing. Recorded as an ADR in eng_dados — stage 1.2 |
| RP-03 | §5.2 | The count risk is real and already shows, but outside P01: 126 `order_id` values exist in both sources; P01 and P02 have no group affected today; **P05 and P06 undercount one order in one group each**. And 2,479 of 3,292 orders have items in more than one category, while P01 does not even declare `order_count` as a measure in the Glossary. **Measurement** M3 and M4 | `adjustment` | `order_count` kept off the dashboard. The fix of the four views goes into v1.1.0 of eng_dados (stage 1.1), not into the site |
| RP-04 | §3.4 | `ORD-0000037` identifies two different orders — in the legacy source, 2024-12; in retail, 2025-07 —, and the retail one is the D65 case, sold before launch. **Measurement** M10 | `adjustment` | Item chosen by a declared criterion, after the data fix. The collision becomes the hook of the lesson on composite identity |
| RP-05 | §3.1 | "Explain the coverage" has a concrete case: 2026-09 has a single day (`as_of_date`), 3 groups and R$ 17,795.87 — the monthly chart would show a drop that does not exist. There are also 15 missing combinations in complete months. **Measurement** M5 and M6 | `adjustment` | Partial month flagged and a slice with no sale said as such (stage 2.5) |
| RP-06 | §3.1, §3.3 | The category axis has no business meaning: most leaves sit under an unrelated root ("Moda › Notebooks"), with the parent assigned round-robin; and price has no affinity with category — one single range —, although Data Generation §5 states it as implemented. The analysis by category, the core of P01, would teach a comparison without content. **Reading** and **measurement** M7 and M8 | `adjustment` | Fixed in the generator, in v1.1.0 (O3; stages 1.4 to 1.6). N6 (2026-10-22) decided: now, before anything else |
| RP-07 | §3.3 | The caution about lineage is confirmed, now measured: the value path of revenue has 15 nodes and 14 edges down to `raw` and `raw_legacy`; `year_month` ends at `dim_date`, generated, and `category_name` reaches the category name without going through the temporal join of the product — membership does not show; on the legacy branch, the bridge's `meta.lineage` jumps over the whole cleaning. **Measurement** M12 | `observation` | A small declaration for membership and controls (plan §3.3; stage 3.3) |
| RP-08 | §3.4 | The consistent cut is simpler than the proposal assumes: the five layers of the path live in the same `warehouse_db`, and one `REPEATABLE READ READ ONLY` transaction gives the same picture across all of them. Only the transactional source stays outside, and the lesson starts at `raw`. **Reading**; the behaviour in the real capture is a **hypothesis** until stage 3.3 | `observation` | Stage 3.3 |
| RP-09 | §5.1 | "Decimals as text with their scale preserved" would carry a scale that varies by source: in retail, discount with scale 0 to 2 and price 0 to 4; in legacy, always 2 and 4. **Measurement** M11 | `adjustment` | Format by the declared scale. Measures go into Parquet as fixed-scale decimals and DuckDB sums them as exact decimals; label and total come from the exact value, and the conversion to floating point only draws the chart. The lesson receives values already computed by the exporter |
| RP-10 | §4.1–§4.3 | The whole view is ~96 kB as text: the package fits inside the HTML itself. A single file settles at once the mixing of versions through caching of §4.3, and also opens as a local file, like the trail. **Measurement** M1 | `adjustment` | Superseded by N2 (2026-10-22): with the 16 views in scope (O5), the atomic publication of Firebase is what prevents mixed versions, and the package goes in Parquet (M14) |
| RP-11 | §9 | `manifest.json` is complete today — 192 models with compiled SQL, generated on 2026-10-22 17:23Z —, but any `dbt --select` rewrites it partially. **Measurement** and **reading** of the R29 warning in the trail | `observation` | The exporter rejects lineage with problems, as `lineage.main` already does (stages 1.3 and 3.3) |
| RP-12 | §4.1 | Publishing through GitHub Actions would be CI/CD, out of scope for eng_dados; in the new repository it becomes a new choice. GitHub Pages serving a folder of `main` publishes with no workflow in the repository. **Reading** | `observation` | Decided in N2 (2026-10-22): Firebase Hosting with a GitHub Actions CI pipeline. In the new repository, CI/CD is part of the product (plan §4) |
| RP-13 | §4.4 | With separate repositories, access stops being abstract: the only login of the warehouse today is the superuser (Governance §7), and copying it into another repository is what no real environment would do. **Reading** | `adjustment` | N4 (decided: a read-only login, member of `analyst`) and the former N5 (the custodian's read-only capture, unless the Owner objects) |
| RP-14 | §3.5, §6 | The data fix changes every value in the warehouse: the dated real outputs of the trail come to describe the v1.0.0 data, and the approved recovery package stops representing the state. **Reading** | `observation` | N6 (2026-10-22) decided to fix now; the notice on the trail is N7, decided to go in only with the trail's next update; stage 1.6 redoes the package |
| RP-15 | §4.4 | With O2, `personal` fields may be published. The generator makes a match with a real person impossible for the document (`SIN` suffix) and the e-mail (`example.com`), but not for the phone number, which comes out in a valid mobile format. **Reading** of `generator/providers.py` | `observation` | The dimensional model has no phone number (M16); the caveat only comes back if `trusted` or `raw` are published (plan §1.3) |

### Claude Code's opinion

The development plan resulting from this review is in [`PLAN.md`](PLAN.md); only the answers to the
eight questions of §11 are here.

1. **Does the path teach without hiding filters, joins and controls?** It does, as long as questions
   2 and 3 do not depend on value lineage: it does not see the `is_realised` filter, the sale date
   converted to `America/Sao_Paulo`, the temporal join with the product or the legacy cleaning
   (RP-07). With the small declaration of stage 3.3, yes.
2. **The smallest convincing experience.** For P01, which became the first slice (O5): the report
   with net revenue and the table with gross revenue, discount and units; three filters; two charts;
   partial month and empty slice handled; and a lesson on one retail item, with question 1 open,
   question 2 one click away and question 3 as a short list pointing to the study of the governance.
   Cut right away: `order_count`, the source filter, free navigation, links with state and everything
   the table below postpones.
3. **Is the lineage enough?** For the value, yes — 15 nodes and 14 edges, measured (M12). The
   complement declares the joins and the filter that give membership, the point of rounding and the
   controls. Lineage reaches the new project through a JSON output of eng_dados itself, with no
   reimplementation.
4. **Updated dashboard and historical lesson.** The separation preserves the intent, and it is
   simpler than it looks: the data of eng_dados only changes through a deliberate regeneration. The
   page compares the total of the lesson's group with the dashboard's and, if they diverge, labels
   the lesson as historical, with its date. Equal totals are not presented as proof that the items
   are the same.
5. **Interface, export and hosting.** For P01 alone, I recommended HTML with no library, in a single
   file, on GitHub Pages. With the scope widened by O5 — every view —, round 1 decided (N2): Parquet
   queried by DuckDB in the browser, Firebase Hosting in a project of its own and a GitHub Actions CI
   pipeline, with a preview per PR; the exporter in Python with `uv`. With per-profile access (O7),
   each report is published encrypted, and the password of each profile opens only the keys of its
   reports (N23). The framework is N3; access to the warehouse and to the pipeline, N4 and N15. The
   record needed is the ADR for O2, with the scope of N8: classifying is not exposing.
6. **Limitations that affect the first scope.** The partial month (RP-05), the order count (RP-03),
   the meaningless category axis (RP-06), the scale by source (RP-09) and the absence of the source in
   the view. These can wait: identifier collisions as a lesson of their own, and category at sale
   time versus the current one.
7. **The ideas of §7** — table below.
8. **Validations still missing, and the order.** All those in plan §9; the order is in
   [plan §6.3](PLAN.md#63-recommended-order).

| Idea of §7 | Opinion | Reason |
|---|---|---|
| A formula that highlights the column at each stage | Keep | It is question 1; the values come from the capture, with the rounding where it happens |
| Before and after, with changes highlighted | Simplify | Input and output per stage, and a stage that only carries the value said as such — the capture shows which ones |
| "Why does this sale count?" | Keep | It is question 2; the conditions come from the declaration, not from lineage |
| Contextual glossary | Simplify | A link to the eng_dados Glossary at the pinned commit; no parallel definition |
| A question before revealing | Postpone | Until the basic path passes the learning criterion |
| A link that preserves filters and stage | Postpone | It requires carrying the package version along |
| Free navigation by column | Postpone | It recreates the excessive map the Owner wants to avoid |
| The same field in `retail` and `legacy` | Postpone | Next lesson; `ORD-0000037` is the measured hook (M10) |
| One rejection all the way to quarantine | Postpone | A lesson of its own, tied to the study of the governance |
| Legacy control dependencies | Postpone | It belongs to the study of the governance and to the legacy lesson |
| Category at sale time versus the current one | Postpone | Only with a case observed after the regeneration |
| Comparing two extractions of P01 | Discard | The data is static between regenerations, and the package history in Git already shows the difference |
| Quality evidence next to the stage | Simplify | The name and link of the test that guards the stage, without claiming it passed for this extraction |
| Simulating unrealised orders | Discard | It changes the question and needs data that consumption does not offer |
