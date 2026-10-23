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
| Status | Round 1: Claude Code's review of this proposal (findings RP-01 to RP-15). Round 2: Codex's review of the resulting [`PLAN.md`](PLAN.md) (findings RV2-01 to RV2-14), each answered in its Status cell and applied in plan revision 7. A third round is the Owner's call |
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

## Round 2 — Codex review of PLAN.md

| Field | Reviewed base |
|---|---|
| Date | 2026-10-23 (America/Sao_Paulo; command timestamps below are UTC) |
| Reviewer | Codex, acting as the second agent at the Owner's request |
| bi-como-codigo | `16c35366079b2c78ed1e95eee73fd5db196c34f1` |
| mvp_eng_dados_1 | `26b58b33deac1ee89b9f7de1292ba40fec0d4de2` |
| Declaration reviewed | PLAN.md, including the Owner's decisions O1–O8 and N1–N25 |
| Context read | Both repositories' AGENTS.md and CLAUDE.md; REVIEW.md §§1–11 and RP-01–RP-15; all probes and literal outputs in evidence/20261022/; the upstream code and documents cited below |
| Method | The upstream [revisao skill](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/.claude/skills/revisao/SKILL.md), adapted to a plan review. No implementation or acceptance is implied. |

**Assessment — reading and review judgment:** the architecture is viable within the Owner's
choices, but the plan is not ready for execution unchanged. The blocking findings concern the
publication gates, the encryption specification, description inheritance and recovery acceptance.
They do not require changing the chosen hosting, public passwords, view-only contract or separation
of repositories. Resolve them in the plan and the named design/runbook before executing the affected
stages; independent foundation work need not wait.

**Evidence convention:** **reading** means an inference from the inspected code, documents or
official specifications; **hypothesis** means proposed behavior or cost that has not been exercised;
**measurement E0–E6** means the commands and literal outputs below. Earlier M1–M18 remain the
author's recorded evidence, not measurements repeated by this review. A counterexample against a
small model of the proposed encryption is not a test of an implementation that does not exist.

### Findings

The Status cells were left empty for the author; Claude Code filled them on 2026-10-23, after reproducing or checking each finding (evidence/20261023/).

| # | Where | Finding | Verdict | Status |
|---|---|---|---|---|
| RV2-01 | PLAN §3.2, chapter 6; §10 question 2 | **Reading; measurement E2.** N22 makes both profiles available to every visitor. A holder of the public Diretoria password can derive its wrapping key, recover every report key and decrypt offline, without the login page. They can also create ciphertext with a valid GCM tag; that does not give them Hosting deployment permission. Preserve N22/N23, but describe the result as a public demonstration of access scoped to a supplied key, not authentication of a person's role or confidentiality from the public. The Parquet also enters this public Git repository before CI encryption (§3.4). Qualify “no key/Parquet in the clear” as an inventory property of the deployed artifact; it cannot mean that visitors cannot recover them. | adjustment | Accepted, and it reaches further: in revision 6 the CI pipeline encrypted, so clear Parquet would have entered this public repository. Encryption moves to the export on the Owner's machine; Git and Hosting receive only ciphertext and a manifest with no clear figure; the plan describes the result as access scoped to a supplied key, not authentication or confidentiality (PLAN §3.2, §3.4, §3.6). Reproduced as M22 (evidence/20261023/r1) |
| RV2-02 | PLAN §3.2, §8; stage 2.6 | **Reading; hypothesis about the future build.** Standard primitives are appropriate, but “many iterations,” “a salt of its own” and “no initialisation vector ever repeated” do not specify an interoperable, reviewable protocol. The access matrix can pass even if a report key/IV pair is reused on a later publication. Specify the envelope, derivation parameters, randomness, key lifetime, metadata binding and negative tests described below. Review that design before the encrypted prototype or any report preview, then verify the implementation and browser path. A build matrix alone is insufficient. | blocking | Accepted. PLAN §3.6 specifies the envelope with proposed parameters — a fresh 256-bit data key per encryption, a 96-bit IV and 128-bit tag, a 128-bit salt per profile, PBKDF2-HMAC-SHA-256 with iterations set by measured latency, AES-KW with its fixed IV, identities bound in the authenticated data — and its oracles. New stage 2.2a reviews the design with a reference implementation before the prototype (2.3) and before any report preview |
| RV2-03 | PLAN §§3.4–3.5; stages 2.2 and 2.4 | **Reading; hypothesis/counterexample.** Hashes, row counts and sums establish package consistency, not agreement with the warehouse or correct grouping. An exporter can swap channel labels, regenerate the hashes and preserve every total. Checking against whichever dbt manifest accompanies it also does not detect a change to the consumer's previously accepted contract. Require the explicit view inventory, accepted schema/version, grain/uniqueness, null and decimal rules, a consistent read, and row-level round-trip equality against the views at export. Preserve the local oracle results with the package. M2 reads facts as custodian: generalising it must not silently grant the N4 exporter access to analytics. CI can verify recorded evidence and artifact consistency; it cannot certify an inaccessible warehouse. | blocking | Accepted. Reproduced with a new probe: swapping two channel labels keeps the 1,140 rows and every total, and only a row-level comparison catches the 761 diverging rows (M19). PLAN §3.4 adds the source-to-package gate — one consistent read, the contract pinned here, grain, nulls, decimals, typed rows equal after the round trip, oracle results in the package — and the mutation tests; §3.5 keeps the custodian's oracles apart from the exporter; stage 2.4's criteria follow |
| RV2-04 | PLAN §3.4; stages 2.2, 2.3 and 2.6 | **Reading; hypothesis about build output.** Encrypting inputs and looking for clear Parquet is not a sufficient publication boundary. A framework can emit report rows into prerendered HTML, JSON, JavaScript, caches or source maps; a renamed clear file also defeats an extension-only check. The earlier proposal's explicit inclusion list (§4.2 of this review) must survive into the plan. Build a fresh deploy directory containing only declared public assets/metadata and encrypted report artifacts, inspect the final output, and deploy exactly that directory. Reject injected clear data and unwrapped keys before both preview and live uploads. State whether report totals in a public manifest are intentionally public. | blocking | Accepted. PLAN §3.4 restores the explicit inclusion list, builds a fresh deploy directory, inspects the finished output by content (HTML, JSON, JavaScript, caches, source maps) before preview and live, and states that the public manifest carries no clear figure: control totals travel encrypted. Stage 2.3 fails a framework candidate that runs report queries over clear data at build time |
| RV2-05 | PLAN §3.4; N15/N25; stages 2.2 and 2.10 | **Reading; hypothesis about the future workflow.** “Reject, then nothing is published” needs a trusted deployment job, not just an earlier check step. A public PR can change the checker, build, workflow or firebase.json. Define which PRs may get deploy credentials, isolate untrusted builds, restrict OIDC trust, require checks on the exact approved revision and prevent obsolete concurrent runs from replacing newer releases. Promote the already validated artifact/version; a fresh encryption/build on merge is not the approved preview. The default Firebase GitHub setup stores a service-account key, contrary to N15; use and test a federation-compatible CLI path. See the publication requirements below. | blocking | Accepted. Checked: the portfolio's workflow uses the default action with a stored service-account key; the Firebase CLI documentation recommends Application Default Credentials for CI; `hosting:clone` within a site points live at the same version. PLAN §3.4 defines the trusted workflow — same-repository previews, protected environment, federation restricted to this repository and environment, required checks on the approved revision, concurrency, promotion by clone — and stage 2.2 proves it on harmless fixtures. If federation fails with the Firebase CLI, the way forward returns to the Owner (§7) |
| RV2-06 | PLAN §5.3; stages 1.4–1.6; §8 | **Reading.** “Recovery package redone and checked” is weaker than [Capacity and Recovery §§3.3–3.4](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/capacidade_e_recuperacao.md#33-regras). A candidate may replace the approved package only after a validated end-to-end restore and promotion; upstream recovery/cli.py explicitly distinguishes verify/list from restore. Require those operations and their oracles in 1.6, with the old approved package preserved until promotion. Identify the rollback cut, compatible code/configuration and what post-cut state would be lost before destructive work. Commit the maintenance code before packing: pack normally refuses a dirty tree. This is work and a destructive restore window missing from the explicit exit criterion. | blocking | Accepted. Confirmed by reading Capacity and Recovery §3.3 and `recovery/cli.py`: `pack` refuses a dirty tree, and `verify` is not `restore`. PLAN §5.3 and stage 1.6 now verify the approved package and identify the rollback cut before anything destructive, commit the maintenance code before packing, restore the candidate through the nine steps under `RESTAURAR=1` with the Owner's authorisation, promote it, and keep the previous package until then |
| RV2-07 | PLAN §5.3, N14; stages 1.4–1.6 and 3.6 | **Reading.** The cited regeneration procedure already requires more than reseeding and rebuilding: stop host producers/Beam/Prism and active jobs, reset CDC and the hot sink, reset the retail ingestion, compare complete event payloads and balances, reset SCD and incremental state together, preserve run_results, finish the specific DAG run and restore the recorded operating state. Make these explicit runbook checkpoints. N14 remains valid: D62/D63 mean alert correctness/draining cannot be inferred from sink convergence; D64 affects Airflow Connections/Variables, not the current DAG. Record those limits in release/lab evidence without silently fixing or closing them. Update current measured records after regeneration; preserve accepted ADRs and historical measurements. | adjustment | Accepted. Confirmed by reading Local Execution §3.2, steps 1 to 7. PLAN §5.3 lists the checkpoints that the runbook of 1.4 maps to command, oracle and restart point, records D62–D64 as declared limitations in the release evidence, and leaves accepted ADRs and historical measurements unchanged |
| RV2-08 | PLAN §5.4; stages 1.7–1.8 | **Reading; measurement E3.** sensitivity.py derives sets of value dependencies, not semantic identity. Copy, SUM, ROUND and multiplication have identical leaves in E3; P01's aggregated revenue also has a single immediate leaf of the same name. lineage.py additionally allows meta.lineage to skip legacy cleaning. Neither a single leaf nor a matching name proves that the source description still applies. Reuse the graph, but require a conservative identity/transport classification of the expression and every inherited hop, or an explicit reviewed declaration. Aggregation, transformations, generated fields and ambiguous unions must require text. Keep sensitivity semantics unchanged; a reasoned description override must survive regeneration. Add counter-proofs for same-name computed columns and declared legacy bridges. | blocking | Accepted. Reproduced, and extended with a type cast: copy, sum, rounding, multiplication and cast share one leaf (M21). PLAN §5.4 requires a conservative transport classification of the expression at every hop, legacy bridges by declaration only, unchanged sensitivity semantics, reasoned overrides that survive regeneration and the two counter-proofs; stage 1.7 moves to xhigh, and M18 is marked as superseded |
| RV2-09 | PLAN §5.4; stages 1.7–1.8 and 2.7 | **Reading; measurements E3/E4.** The ratchet's scope and bootstrap conflict: §5.4 says any missing column description fails check, 1.7 must already pass check, but 1.8 supplies the text and only promises full coverage in analytics/consumption. E3 still finds 451 and 157 missing descriptions in those layers alone. E4 shows gaps elsewhere, including model domain/owner outside the targeted objects. Define per-layer floors and the activation order; complete/approve the text before enforcing its full floor. Use the materialised-column inventory, as test_classificacao.py does, to avoid a vacuous pass on omitted columns. Distinguish explicitly scoped portal coverage from project-wide completeness. | adjustment | Accepted. PLAN §5.4 sets a ratchet with per-layer floors over the materialised-column inventory: introduced by 1.7 at today's coverage, raised to 100% in `analytics` and `consumption` by 1.8 only after the Owner approves the text. Portal coverage is stated apart from project-wide completeness |
| RV2-10 | PLAN §5.4; make check; stages 1.7–1.8 | **Reading; measurement E3; cost hypothesis.** One complete sensitivity derivation took 21.622 s in this environment; lineage.build reusing it took 0.007 s. The current Makefile already invokes separate sensitivity and lineage checks, and tests/test_linhagem.py derives again in its fixture. Do not add another complete parse per column or another independent full pass without measuring it. Share a derivation within the checker/fixtures where practical, invalidate any cache by its actual inputs, and measure the added end-to-end check cost. The new ratchet's time, memory and required manual text remain unmeasured; M18 is not a delivery estimate. | adjustment | Accepted. Confirmed by reading: `make catalog` derives classification and lineage in separate passes, and `tests/test_linhagem.py` derives again. PLAN §5.4 shares one derivation across the checks and their fixtures, invalidates any cache by its inputs and measures the added `make check` cost in 1.7 |
| RV2-11 | PLAN N16, §3.5; stage 2.12 | **Reading; measurement E5.** N16 correctly reads ADR-0008, ADR-0018 and Governance §7: analyst consumes consumption, not analytics, and views answer business questions rather than mechanically mirroring facts. E5 reads P01 and gets SQLSTATE 42501 on the fact. Keep the custodian's lesson/oracle capture separate. A justified detail view can be added through the upstream contract/ADR; nothing here calls for exposing the dimensional model wholesale. Test the future dedicated login through an actual non-superuser connection, including denied writes and role escalation, rather than relying only on SET ROLE from the existing superuser. | observation | Accepted. PLAN §3.5, §5.2 and stage 1.3 prove the dedicated login through an actual non-superuser connection — it reads `consumption`, is refused elsewhere, cannot write and cannot escalate — and keep the custodian's capture separate |
| RV2-12 | PLAN §3.2; stages 2.6 and 2.11 | **Reading; measurement E6.** P13's on_time_rate has usable numerator/denominator columns, but its transit and late-delay averages are already rounded and lack their exact sums. Across 313 month/carrier/service groups, weighting the exported averages by their counts differs from direct recomputation at the displayed four decimals in 46 transit groups and 20 late-delay groups. The rule about ratios does not cover this. Keep these averages at the view's native grain, or obtain sufficient statistics through an upstream contract change; do not present reconstructed rounded averages as exact. Include this in P13's oracle and audit the other reports for non-additivity, time-dependent balances and truncated populations. | adjustment | Accepted. Reproduced exactly: 313 groups, with 46 and 20 differences (M20). PLAN §3.2 keeps averages without sufficient statistics at the view's native grain — P13's first, in stage 2.6 —, adds the per-report audit to 2.11, and leaves any upstream contract change to the Owner, with an ADR (§7) |
| RV2-13 | PLAN §6.2–§6.3 | **Reading; scheduling/effort hypothesis.** The dependency graph needs repair: the encrypted prototype (2.3) needs the envelope contract now deferred to 2.6; publication infrastructure (2.2) precedes encryption safeguards; the hosted Artifact probe (3.1) needs a representative encrypted asset, worker and cross-origin policy; and a study site that reads showcase reports needs that published interface, not only 3.1. Make 3.3/3.5's implementation depend on the study foundation as well. Split encryption design/core tests from the later login/P13 delivery, use harmless fixtures for early infrastructure probes, and gate actual report uploads on the complete checks. Reconcile this with 2.10 being the first approved product publication. Suggested sequencing and effort are below. | adjustment | Accepted. PLAN §6: new stage 2.2a (envelope and core tests) before the prototype; 2.2 on harmless fixtures; 3.1 with the agreed envelope, the worker from jsDelivr and cross-origin headers; 3.2 after the first publication; 3.3 and 3.5 after 3.2; no real report data reaches Hosting before the gates exist |
| RV2-14 | PLAN §3.2, portal chapters and project governance | **Reading; usability hypothesis.** The proposed order works as a reference path: orientation → layers → catalogue → questions → vocabulary → access → lineage → quality → maintenance. Also offer a short question → report → column route from the introduction, so a newcomer need not traverse the catalogue first. Label missing metadata rather than inventing it, and distinguish declared tests, dated successful executions and currently open issues. In particular, a past review with no remaining findings does not imply D62–D64 are resolved today. Narrative and glossary usability still require the outsider test. | observation | Accepted. PLAN §3.2 adds the short route from question to report to column, labels missing metadata and keeps declared tests, dated executions and open issues apart, naming D62–D64; stage 2.7's criteria follow |

### Required detail for the encryption design

**Reading of standards; proposed implementation constraints, not implemented choices:** PBKDF2,
AES-KW and AES-GCM are supported by the [Web Cryptography API](https://www.w3.org/TR/2017/REC-WebCryptoAPI-20170126/).
Record a versioned envelope with password byte encoding, KDF/hash/iteration count, profile salt,
wrapping algorithm, report identity, wrapped key, GCM IV/tag and package identity. Specify lengths
rather than relying on library defaults. A concrete candidate is PBKDF2-HMAC-SHA-256, a wrapping
key and independently random data keys of 256 bits, a random salt of at least 128 bits per profile
and declared rotation scope, a 96-bit GCM IV and a 128-bit tag. These are **proposed parameters**;
the iteration policy and browser latency still need measurement. Salts and IVs are public.
[NIST SP 800-132 §§5.1–5.2](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-132.pdf)
supports random salts and selecting the work factor against acceptable client cost.

The relevant GCM uniqueness requirement is **per key across all encryptions**, including retries
and publications, not global uniqueness of every IV across unrelated keys. A fresh data key for
each new file encryption, with an explicitly defined retry policy, is a simple way to bound this.
An unchanged encrypted artifact can be promoted without encrypting it again.
[NIST SP 800-38D §8](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf)
defines the key/IV requirement. AES-KW has its own fixed initial value under the WebCrypto
algorithm; do not give it GCM's random-IV rule.
[WebCrypto AES-KW](https://www.w3.org/TR/2017/REC-WebCryptoAPI-20170126/#aes-kw).

Bind report and package identity to the authenticated data and the expected manifest mapping.
This catches accidental substitution; **it does not authenticate the publisher against someone
who knows the public password** (E2). Publication authenticity comes from the trusted release
path and HTTPS origin. Changing a password in a later release cannot revoke previously downloaded
ciphertext plus its former public password.

**Proposed oracles:** known-answer vectors; independent producer/browser round trips; the full
profile/report matrix exercised by actual unwrap/decrypt calls; wrong passwords; changed wrapped
keys, salts, IVs, tags and ciphertext; swapped report/package identifiers; malformed envelopes;
and an injected reused key/IV pair. Inspect the finished deploy artifact for raw data and keys.
Run the same reader against the preview, including profile switching/logout cleanup of DuckDB
tables, buffers and caches. A disallowed route must not keep previously decrypted Diretoria data
visible after switching to Logística. No browser interoperability, cleanup or complete matrix was
tested in this session.

### Publication and export gates

**Reading and proposed acceptance criteria:** distinguish three checks: source-to-package equality,
the encrypted build artifact, and deployment of those exact bytes. The first is local. The second
must run before any Hosting upload, including previews. The third belongs to a trusted workflow
whose checker and deployment configuration cannot be replaced by an untrusted PR.

The local export should read its views and control totals in one read-only consistent transaction,
validate the pinned consumer contract, and compare typed rows after writing and reading Parquet.
Validate column identity/order, decimal precision/scale, nullability, dates/time zones and the
declared grain, including empty/all-null cases. The sizing prototype exportar.py infers Arrow types,
falls back to strings and reads as superuser; it is evidence of size, not the N4 exporter.
Do not treat sums of ratios or averages as business totals. Independently maintained upstream
semantic oracles can be run by the custodian; the exporter itself remains a consumption reader.

**Hypothesis/counterexample to §10.1:** a package with channel labels exchanged and a newly matching
manifest can satisfy the advertised checksum/count/total checks while displaying wrong categories.
A passing hash therefore cannot support “nothing wrong is published.” Add deliberate mutations for
wrong row labels, missing/extra views, changed types, duplicates and raw-data injection, as well as
the already planned tampered-manifest case.

For N15, the [Firebase GitHub setup](https://firebase.google.com/docs/hosting/github-integration)
creates and stores a service-account JSON key. That default does not implement the Owner's choice.
The [Firebase CLI supports Application Default Credentials](https://firebase.google.com/docs/cli#cli-ci-systems);
test the selected CLI with federated credentials in 2.2 rather than substituting a stored key.
Restrict the [federation trust conditions](https://github.com/google-github-actions/auth)
to the intended repository and approved workflow/ref or environment; keep temporary credential
files outside the deploy artifact. Untrusted PR code must not execute with deploy authority.
[GitHub's workflow security guidance](https://docs.github.com/en/actions/reference/security/secure-use#mitigating-the-risks-of-untrusted-code-checkout).

Record the approved revision, package digest, artifact digest and preview version. On merge,
promote that immutable validated version, or revalidate and obtain approval for any changed
candidate. Firebase supports [cloning a version between channels](https://firebase.google.com/docs/hosting/manage-hosting-resources#clone-a-version);
on the same site this can point live at the same version. Define cache/version binding for the
application, manifest, keys and ciphertext: an open old page must not silently fetch incompatible
new files at reused URLs. Rejected or obsolete jobs must not update either channel. None of these
workflow behaviors has been tested here.

### Regeneration, sequencing and effort

**Reading:** §5.3 recognises most of the breadth of the maintenance. The missing precision is in
its gate, not evidence that the Owner's choice to regenerate is mistaken. The 1.4 runbook should
map every checkpoint in [Local Execution §3.2](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/execucao_local.md#32-regerar-uma-origem-que-já-alimenta-streaming)
to a command, expected oracle and restart/rollback point. Include both sources, a newly certified
legacy capture while preserving retained history, full event-content equality, and the exact
scope of the destructive reset. A recovery rollback follows its own procedure: it rebuilds around
restored SCD memory and must not use the regeneration step that drops that memory.

The plan must distinguish checking the existing approved rollback package, creating a current
candidate, restoring that candidate and promoting it. The package cutoff and code version determine
what rollback preserves. Keep the previous approved package until the candidate's restore passes.
The local maintenance's authorised destructive flags are not permission to override a memory
refusal. Historical B5 performance was read as historical evidence; it is not a timing prediction
for the changed generator, retained legacy captures or new description checks.

**Suggested sequence — hypothesis:** keep 1.4 before 1.5/1.6, and resolve the description semantics
and ratchet bootstrap before running 1.7/1.8 alongside runbook review. Pin the maintenance declaration
before regeneration and package creation; reserve 1.9 for final review, Owner acceptance and tag.
During Part I, 2.1, the envelope/export contract, framework comparison and deployment probes can
proceed using clearly labelled disposable fixtures. Complete the encryption core and artifact
checks before publishing actual report data. After 1.9, validate the real export, reports and
portal, approve the preview and promote it. The study foundation depends on its capability probe
and the stable encrypted interface; lesson/site implementation then has an actual home.

**Effort judgment — hypothesis, not a duration estimate:** 1.4 at xhigh and 1.6 at max/L are
appropriate. Treat 1.7's semantic work at xhigh, with size pending a conservative inheritance
prototype and measured remaining text. 1.8's full human review is not bounded by M18. Keep 2.6 at
xhigh, but separate its design/core from P13 and login/browser validation before trusting M.
The early capability probe remains contained only if it uses the agreed envelope, worker/CDN path
and cross-origin headers. There is no new measured basis for deadlines or session counts.

### Answers to PLAN.md §10

1. **Publication guarantee:** no absolute guarantee. The manifest detects certain inconsistencies;
   it does not prove source semantics, trusted workflow execution or identity of preview and live.
   RV2-03–RV2-05 supply the missing gates.
2. **Encryption/access:** the primitives can enforce which keys a supplied password unwraps.
   With both passwords public, every visitor can open all reports; there is no authenticated
   organisational role or public confidentiality. The build matrix is necessary, not sufficient.
   Keep N22/N23 with the limits and checks in RV2-01/RV2-02.
3. **Regeneration cost/effect:** the broad scope is acknowledged, but restoration validation,
   promotion, the rollback cutoff and detailed restart oracles must be explicit. Runtime and
   memory under the new generator remain unmeasured; N14's defects remain declared limitations.
4. **Descriptions/ratchet:** reuse lineage as infrastructure, not as proof of unchanged meaning.
   E3 disproves the single-leaf shortcut. Define safe inheritance and scoped floors first; share
   the expensive derivation and measure the incremental cost of check.
5. **N16:** yes. It preserves the warehouse's tested consumption boundary and business-question
   design. A custodian capture is a separate operation, not an exception for the exporter.
6. **Portal:** the chapters cover the needed story. Keep progressive navigation and a short route
   from a business question to a report/column; expose metadata gaps and dated evidence honestly.
   Comprehension and usability remain hypotheses.
7. **Order/dependencies/effort:** Part I first is sound. Repair the early encryption/publication
   dependencies, ratchet bootstrap and study-interface dependencies. The largest uncertainty is
   semantic declaration/review work, not just writing code; session sizes remain estimates.
8. **Decisions:** no additional product/platform choice is needed to resolve these findings.
   Framework selection, destructive execution authorisation, declaration review, ADR acceptance,
   release acceptance and pushes remain the Owner's. Parameterising an agreed primitive, writing
   counter-proofs and wiring dependencies are implementation work for review, not reasons to
   reopen N22/N23. Any genuinely new upstream contract or data-treatment decision still follows
   CLAUDE.md §5. Technical validation, review of declarations and formal acceptance stay distinct.

### Not verified, assumptions and environment

**Not verified:** no application, framework build, browser, Artifact, CDN download, Firebase project,
OIDC exchange, PR workflow, preview, deployment, cache transition or real encryption implementation
was exercised. No complete access matrix for sixteen actual encrypted reports exists yet. No
generator was changed or run; no ingestion, dbt build, DAG, streaming, migration, recovery pack,
verification, restore or promotion was executed. The existing approved package's contents/current
recoverability were not checked. The description generator and added make check cost do not exist
to measure. Usability, accessibility, browser key-derivation cost and hosting quotas remain open.
The known secrets-history false positive was accepted as recorded, not rediscovered.

**Assumptions:** the Owner's decisions remain authoritative and all future published data is synthetic.
Recorded historical probes are evidence at their stated cutoffs, not proof that the current database
was built by the inspected commit. The files in dbt/target are local generated artifacts, not a
Git-attested build. This review does not assume that a successful full pipeline will resolve the
parked issues, that data cannot change outside regeneration, or that a public preview is private.

**Environment — measurements E0/E1/E5:** Linux x86_64, the existing upstream Python environment,
Node WebCrypto and PostgreSQL through the prescribed ro.sh wrapper. Both Git trees were clean
before the append. docker ps ran before warehouse probing; all three project databases were
already healthy, so make up was unnecessary. An Airbyte control-plane container and an unrelated
PostgreSQL container were already running; they were neither started, stopped nor used by this
review. No Airflow or streaming service was started. Python ran with bytecode writing disabled;
scratch SQL lived only in /tmp. Only REVIEW.md is the requested repository edit.

The first warehouse attempt was denied by the sandbox's Docker-socket restriction; the approved
retry used the same read-only wrapper. E5 deliberately ends with permission denied to prove the
boundary. The skill's dossier generator and make checks were not run: those are unnecessary here
and would write upstream artifacts or execute builds. The evidence below records the actual
read-only probes and in-memory counterexamples instead.

### Commands and literal outputs

All new measurements cited above are here. Empty git-status output means a clean tree. Successful
commands exited 0; E5's exit 3 is expected. The code in these blocks is review evidence only.

#### E0 — reviewed commits and local runtime

Both status commands produced no output. The SHA-256 is of REVIEW.md before this append.

Working directory: `/home/doug/Projetos/bi-como-codigo`.

Command:

```bash
date -u '+%Y-%m-%dT%H:%M:%SZ'
uname -srm
node --version
/home/doug/Projetos/mvp_eng_dados_1/.venv/bin/python -B --version
git -C /home/doug/Projetos/bi-como-codigo rev-parse HEAD
git -C /home/doug/Projetos/bi-como-codigo status --porcelain=v1 --untracked-files=all
git -C /home/doug/Projetos/mvp_eng_dados_1 rev-parse HEAD
git -C /home/doug/Projetos/mvp_eng_dados_1 status --porcelain=v1 --untracked-files=all
sha256sum REVIEW.md
```

Literal output:

```text
2026-10-23T03:33:26Z
Linux 7.1.1-76070101-generic x86_64
v24.18.0
Python 3.11.15
16c35366079b2c78ed1e95eee73fd5db196c34f1
26b58b33deac1ee89b9f7de1292ba40fec0d4de2
1ae93954384d13b4538fac370ac834942128570344a7960b65b36800cef2d795  REVIEW.md
```

#### E1 — existing container inventory

This is a read-only inventory. It neither measures workload activity inside Airbyte nor authorises its use.

Working directory: `/home/doug/Projetos/mvp_eng_dados_1`.

Command:

```bash
docker ps --format '{{.Names}}\t{{.Status}}'
```

Literal output:

```text
linkedia-engine-postgres-1	Up 10 hours (healthy)
airbyte-abctl-control-plane	Up 10 hours
mvp_ed1_source_db	Up 10 hours (healthy)
mvp_ed1_legacy_db	Up 10 hours (healthy)
mvp_ed1_warehouse_db	Up 10 hours (healthy)
```

#### E2 — password/envelope counterexample

In-memory WebCrypto probe with two dummy report strings, not Parquet or the future application. The 100000 iterations are a probe parameter, not a proposed production work factor. No data key survives in a file. Deliberately permitting key extraction in this independent client models what a public password holder can do outside the site's JavaScript; making the site's own CryptoKeys non-extractable would not prevent that client.

Working directory: `/home/doug/Projetos/bi-como-codigo`.

Command:

```bash
node --input-type=module <<'JS'
import { webcrypto } from 'node:crypto';
import assert from 'node:assert/strict';
const s = webcrypto.subtle, enc = new TextEncoder(), dec = new TextDecoder();
const random = n => webcrypto.getRandomValues(new Uint8Array(n));
async function kek(password, salt) {
  const p = await s.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveKey']);
  return s.deriveKey({name:'PBKDF2', hash:'SHA-256', salt, iterations:100000}, p,
    {name:'AES-KW', length:256}, false, ['wrapKey','unwrapKey']);
}
const passwords = {Diretoria:'senha_complexa_123', Logistica:'complexa_senha_321'};
const salts = {Diretoria:random(16), Logistica:random(16)}, profiles = {};
for (const p of Object.keys(passwords)) profiles[p] = await kek(passwords[p], salts[p]);
const published = {};
for (const report of ['P01','P13']) {
  const key = await s.generateKey({name:'AES-GCM',length:256}, true, ['encrypt','decrypt']);
  const iv = random(12), aad = enc.encode('probe-v1:' + report);
  const ciphertext = await s.encrypt({name:'AES-GCM',iv,additionalData:aad,tagLength:128}, key, enc.encode(report));
  const wraps = {Diretoria:await s.wrapKey('raw',key,profiles.Diretoria,'AES-KW')};
  if (report === 'P13') wraps.Logistica = await s.wrapKey('raw',key,profiles.Logistica,'AES-KW');
  published[report] = {iv,aad,ciphertext,wraps};
}
async function open(report, profile, password, wrappedBy = profile) {
  const p = published[report], k = await kek(password, salts[profile]);
  const key = await s.unwrapKey('raw', p.wraps[wrappedBy], k, 'AES-KW', 'AES-GCM', true, ['encrypt','decrypt']);
  return {key, text:dec.decode(await s.decrypt({name:'AES-GCM',iv:p.iv,additionalData:p.aad,tagLength:128}, key, p.ciphertext))};
}
assert.equal((await open('P13','Logistica',passwords.Logistica)).text, 'P13');
console.log('Logistica password -> P13: OK');
await assert.rejects(open('P01','Logistica',passwords.Logistica,'Diretoria'), {name:'OperationError'});
console.log('Logistica key -> Diretoria wrap for P01: OperationError');
await assert.rejects(open('P13','Logistica','wrong'), {name:'OperationError'});
console.log('Wrong password -> P13: OperationError');
for (const report of Object.keys(published)) {
  assert.equal((await open(report,'Diretoria',passwords.Diretoria)).text, report);
}
console.log('Anonymous reader + public Diretoria password -> P01 and P13: OK');
const {key} = await open('P01','Diretoria',passwords.Diretoria);
const iv = random(12), forged = await s.encrypt({name:'AES-GCM',iv,additionalData:published.P01.aad}, key, enc.encode('altered'));
assert.equal(dec.decode(await s.decrypt({name:'AES-GCM',iv,additionalData:published.P01.aad}, key, forged)), 'altered');
console.log('Public password holder creates valid altered ciphertext: OK');
const corrupt = new Uint8Array(published.P01.ciphertext); corrupt[0] ^= 1;
await assert.rejects(s.decrypt({name:'AES-GCM',iv:published.P01.iv,additionalData:published.P01.aad}, key, corrupt), {name:'OperationError'});
console.log('Bit flip without re-encryption: OperationError');
JS
```

Literal output:

```text
Logistica password -> P13: OK
Logistica key -> Diretoria wrap for P01: OperationError
Wrong password -> P13: OperationError
Anonymous reader + public Diretoria password -> P01 and P13: OK
Public password holder creates valid altered ciphertext: OK
Bit flip without re-encryption: OperationError
```

#### E3 — lineage counterexample and isolated cost

One run, with unrelated services already present. The peak RSS is for the entire Python process, including imports and manifest parsing; the two timings cover only the named calls. No make check runtime or new description implementation is measured. This probe counts model columns only; E4 also counts seeds/snapshots and sources, which explains the different trusted total.

Working directory: `/home/doug/Projetos/mvp_eng_dados_1`.

Command:

```bash
set -a
. ./.env
set +a
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
import json, resource, time
from mvp_ed1.models import lineage, sensitivity as s
schema = {'raw': {'orders': {'total_amount': 'numeric'}}}
levels = {('raw', 'orders', 'total_amount'): 'confidential'}
for expression in ['total_amount', 'sum(total_amount)', 'round(total_amount, 2)', 'total_amount * 100']:
    node = {'unique_id': 'model.probe.x', 'schema': 'consumption', 'name': 'x',
            'compiled_code': f'select {expression} as total_amount from wh.raw.orders'}
    problems, warnings = [], []
    leaves = s._derive_node(node, schema, levels, 'wh', problems, warnings)
    print(expression, '=>', sorted(leaves['total_amount']), 'problems=', problems)
m = json.loads(s.MANIFEST.read_text())
print('manifest_generated_at=', m['metadata']['generated_at'])
models = [n for n in m['nodes'].values() if n['resource_type'] == 'model']
print('models=', len(models), 'compiled=', sum(bool(n.get('compiled_code')) for n in models))
start = time.perf_counter()
d = s.derive(m)
derive_seconds = time.perf_counter() - start
start = time.perf_counter()
lin = lineage.build(m, d)
print(f'derive_seconds={derive_seconds:.3f}; lineage_reusing_derivation_seconds={time.perf_counter()-start:.3f}')
print('max_rss_KiB=', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
print('lineage_problems=', len(lin.problems))
for rel, col in [('monthly_revenue_by_channel_and_category', 'net_revenue_amount'),
                 ('monthly_revenue_by_channel_and_category', 'gross_revenue_amount')]:
    print(f'consumption.{rel}.{col} =>', sorted(lin.leaves[('consumption', rel)][col]))
for layer in ['analytics', 'consumption', 'trusted']:
    cols = [c for n in models if n['schema'] == layer for c in n['columns'].values()]
    print(layer, 'declared_columns=', len(cols), 'missing_description=', sum(not (c.get('description') or '').strip() for c in cols))
PY
```

Literal output:

```text
total_amount => [('raw', 'orders', 'total_amount')] problems= []
sum(total_amount) => [('raw', 'orders', 'total_amount')] problems= []
round(total_amount, 2) => [('raw', 'orders', 'total_amount')] problems= []
total_amount * 100 => [('raw', 'orders', 'total_amount')] problems= []
manifest_generated_at= 2026-10-22T17:23:25.369622Z
models= 192 compiled= 192
derive_seconds=21.622; lineage_reusing_derivation_seconds=0.007
max_rss_KiB= 117396
lineage_problems= 0
consumption.monthly_revenue_by_channel_and_category.net_revenue_amount => [('analytics', 'fact_sales_order_item', 'net_revenue_amount')]
consumption.monthly_revenue_by_channel_and_category.gross_revenue_amount => [('analytics', 'fact_sales_order_item', 'gross_revenue_amount')]
analytics declared_columns= 477 missing_description= 451
consumption declared_columns= 188 missing_description= 157
trusted declared_columns= 1058 missing_description= 1003
```

#### E4 — catalogue coverage

The existing read-only probe was rerun unchanged. Source domain/owner zeros in this script are not measurements of their coverage: its source loop does not inspect those fields. Model-layer gaps and description counts are what this review uses.

Working directory: `/home/doug/Projetos/mvp_eng_dados_1`.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B /home/doug/Projetos/bi-como-codigo/evidence/20261022/catalogo_cobertura.py
```

Literal output:

```text
schema        obj c/desc domain  owner cols decl  c/desc
analytics      25     22      0      0       477      26
consumption    16     16      0      0       188      31
governance      2      2      0      0        17      17
quarantine      2      1      1      1        26      12
raw            37      7      0      0       545       0
raw_legacy     40      0      0      0       616       0
snapshots       4      0      0      0       109       0
staging        77     58     40     40      1114     659
trusted        75     46     43     43      1069      56
testes de dados: 700 {'not_null': 381, 'accepted_values': 84, 'unique': 64, 'relationships': 62, 'unique_combination_of_columns': 57, 'singular': 32, 'fato_reconcilia_com_a_condutora': 10, 'expect_column_values_to_be_between': 5}
blocos {% docs %} do projeto: 18
```

#### E5 — actual warehouse access boundary

The scratch file was created in /tmp; the ro.sh invocation ran from bi-como-codigo. Exit 3 is the intended denial on analytics (SQLSTATE 42501), after the successful analyst read. The read-only setting was on. The initial sandbox attempt returned the Docker-socket error quoted after the successful output; the approved retry changed no SQL.

Working directory: `/home/doug/Projetos/bi-como-codigo`.

Command:

```bash
cat > /tmp/bi_rv2_access.sql <<'SQL'
show transaction_read_only;
show server_version;
set role analyst;
select current_user, count(*) from consumption.monthly_revenue_by_channel_and_category;
\set VERBOSITY sqlstate
select count(*) from analytics.fact_sales_order_item;
SQL
ENG_DADOS_DIR=~/Projetos/mvp_eng_dados_1 evidence/20261022/ro.sh /tmp/bi_rv2_access.sql -q -t -A
```

Literal output:

```text
on
16.15
analyst|1140
ERROR:  42501
```

Initial sandbox attempt, exit 1 (not a database result):

```text
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

#### E6 — P13 averages after grouping away warehouse

The exact side reproduces the current view's delivered-shipment reduction and joins, then aggregates at month/carrier/service grain. The rolled side weights the published rounded averages by their corresponding counts. This compares those two calculations on the current data; it neither repairs the view nor tests any future frontend.

Working directory: `/home/doug/Projetos/bi-como-codigo`.

Command:

```bash
cat > /tmp/bi_rv2_p13.sql <<'SQL'
begin isolation level repeatable read read only;
show transaction_read_only;
with remessas as (
  select distinct shipment_id, delivered_date_key, carrier_key, warehouse_key,
    is_on_time, is_split_order, delivery_delay_days, transit_days, failed_attempt_count
  from analytics.fact_shipment_item where is_delivered
), exact as (
  select d.year_month, c.carrier_name, c.service_level,
    round(avg(r.transit_days), 4) as transit,
    round(avg(r.delivery_delay_days) filter (where not r.is_on_time), 4) as delay
  from remessas r
  join analytics.dim_date d on d.date_key = r.delivered_date_key
  join analytics.dim_carrier c on c.carrier_key = r.carrier_key
  join analytics.dim_warehouse w on w.warehouse_key = r.warehouse_key
  group by 1, 2, 3
), rolled as (
  select year_month, carrier_name, service_level,
    round(sum(avg_transit_days * delivered_count) / nullif(sum(delivered_count),0), 4) as transit,
    round(sum(avg_delay_days_when_late * late_count) / nullif(sum(late_count),0), 4) as delay
  from consumption.on_time_delivery_rate_by_carrier
  group by 1, 2, 3
)
select count(*) as groups_compared,
  count(*) filter (where e.transit is distinct from r.transit) as transit_differences,
  count(*) filter (where e.delay is distinct from r.delay) as delay_differences
from exact e join rolled r using (year_month, carrier_name, service_level);
rollback;
SQL
ENG_DADOS_DIR=~/Projetos/mvp_eng_dados_1 evidence/20261022/ro.sh /tmp/bi_rv2_p13.sql -q -A
```

Literal output:

```text
transaction_read_only
on
(1 row)
groups_compared|transit_differences|delay_differences
313|46|20
(1 row)
```
