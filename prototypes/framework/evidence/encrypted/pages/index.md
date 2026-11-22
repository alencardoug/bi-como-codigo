---
title: Receita por canal e categoria
---

<script>
  // The encrypted route's page (docs/framework_prototype.md §2.3, §3): no source holds data, and the
  // report's table, p01.rows, exists only after login, created by Login from the opened package.
  // Every query names the store `session`, which Login raises once the table exists: the queries
  // run again then. The inputs are Controls' (A4). Evidence formats numbers in English and shows an
  // absent value as blank, so the tables' cells are formatted in pt-BR by the queries, and a cell
  // with no row under the filter is written as the page's text (A5).
  import Login from '$lib/Login.svelte';
  import Controls from '$lib/Controls.svelte';
  import { session } from '$lib/session.js';

  $: ultimo = meses?.length ? meses[meses.length - 1].year_month : null;
</script>

<Login />

```sql canais
select distinct sales_channel_name from p01.rows order by 1 -- session ${$session}
```

```sql meses
select distinct year_month from p01.rows order by 1 -- session ${$session}
```

```sql por_mes
select year_month, root_category_name, sum(net_revenue_amount) as net_revenue_amount
from p01.rows
where sales_channel_name like '${inputs.canal.value}'
group by all
order by year_month, root_category_name -- session ${$session}
```

```sql resumo
with cells as (
  select m.year_month, r.root_category_name
  from (select distinct year_month from p01.rows) m cross join (select distinct root_category_name from p01.rows) r
), filtered as (
  select year_month, root_category_name, sum(net_revenue_amount) as n, sum(unit_count) as u
  from p01.rows
  where sales_channel_name like '${inputs.canal.value}'
  group by all
)
select c.year_month as mes, c.root_category_name as raiz,
       coalesce('R$ ' || translate(format('{:,.2f}', f.n), ',.', '.,'), 'Sem vendas neste recorte.') as receita,
       coalesce(translate(format('{:,d}', cast(f.u as bigint)), ',', '.'), 'Sem vendas neste recorte.') as unidades
from cells c left join filtered f using (year_month, root_category_name)
order by c.year_month, c.root_category_name -- session ${$session}
```

```sql detalhe
select sales_channel_name as canal, category_name as categoria,
       translate(format('{:,d}', order_count), ',', '.') as pedidos,
       translate(format('{:,d}', unit_count), ',', '.') as unidades,
       'R$ ' || translate(format('{:,.2f}', net_revenue_amount), ',.', '.,') as receita
from p01.rows
where sales_channel_name like '${inputs.canal.value}'
  and year_month = '${inputs.mes.value}'
order by sales_channel_name, category_name -- session ${$session}
```

{#if $session}

<Controls {canais} {meses}/>

<LineChart data={por_mes} x=year_month y=net_revenue_amount series=root_category_name title="Receita líquida por mês"/>

## Resumo

<div data-bice="summary">
<DataTable data={resumo} rows=1000 sortable=false downloadable=false>
  <Column id=mes title="Mês"/>
  <Column id=raiz title="Categoria raiz"/>
  <Column id=receita title="Receita líquida"/>
  <Column id=unidades title="Unidades"/>
</DataTable>
<p data-bice="partial">Mês em curso: os números ainda vão mudar.</p>
</div>

## Detalhe do mês

<div data-bice="detail">
{#if detalhe.length === 0}
<p data-bice="empty">Sem vendas neste recorte.</p>
{:else}
<DataTable data={detalhe} rows=1000 sortable=false downloadable=false>
  <Column id=canal title="Canal"/>
  <Column id=categoria title="Categoria"/>
  <Column id=pedidos title="Pedidos"/>
  <Column id=unidades title="Unidades"/>
  <Column id=receita title="Receita líquida"/>
</DataTable>
{/if}
{#if ultimo && inputs.mes?.value === ultimo}
<p data-bice="partial">Mês em curso: os números ainda vão mudar.</p>
{/if}
</div>

{/if}
