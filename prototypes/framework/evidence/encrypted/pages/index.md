---
title: Receita por canal e categoria
---

<script>
  // The encrypted route's page (docs/framework_prototype.md §3): no source holds data, and the
  // report's table, p01.rows, exists only after login, created by Login from the opened package.
  // Every query names the store `session`, which Login raises once the table exists: the queries
  // run again then.
  import Login from '$lib/Login.svelte';
  import { session } from '$lib/session.js';
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
select year_month, root_category_name,
       sum(net_revenue_amount) as net_revenue_amount, sum(unit_count) as unit_count
from p01.rows
where sales_channel_name like '${inputs.canal.value}'
group by all
order by year_month, root_category_name -- session ${$session}
```

```sql detalhe
select sales_channel_name, category_name, order_count, unit_count, net_revenue_amount
from p01.rows
where sales_channel_name like '${inputs.canal.value}'
  and year_month = '${inputs.mes.value}'
order by sales_channel_name, category_name -- session ${$session}
```

{#if $session}

<Dropdown data={canais} name=canal value=sales_channel_name title="Canal">
    <DropdownOption value="%" valueLabel="todos"/>
</Dropdown>

<LineChart data={por_mes} x=year_month y=net_revenue_amount series=root_category_name title="Receita líquida por mês"/>

## Resumo

<div data-bice="summary">
<DataTable data={resumo} emptyMessage="Sem vendas neste recorte."/>
</div>

## Detalhe do mês

<Dropdown data={meses} name=mes value=year_month title="Mês"/>

<DataTable data={detalhe} emptyMessage="Sem vendas neste recorte."/>

Mês em curso: os números ainda vão mudar.

{/if}
