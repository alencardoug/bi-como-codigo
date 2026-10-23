set role analyst;
-- S4: totais por mês (cobertura) e combinações ausentes
select year_month, count(*) as grupos, sum(net_revenue_amount) as liquida, sum(unit_count) as unidades
from consumption.monthly_revenue_by_channel_and_category
group by 1 order by 1;
with m as (select distinct year_month from consumption.monthly_revenue_by_channel_and_category),
     c as (select distinct sales_channel_name from consumption.monthly_revenue_by_channel_and_category),
     k as (select distinct root_category_name, category_name from consumption.monthly_revenue_by_channel_and_category)
select m.year_month, count(*) as combinacoes_ausentes
from m cross join c cross join k
left join consumption.monthly_revenue_by_channel_and_category v
  on v.year_month = m.year_month and v.sales_channel_name = c.sales_channel_name and v.category_name = k.category_name
 and v.root_category_name = k.root_category_name
where v.year_month is null
group by 1 order by 1;
