-- S3: o mesmo padrão (count distinct order_id sem source_system) nas views P02, P05, P06.
-- P02: ano-mês × canal × segmento
with g as (
  select d.year_month, ch.sales_channel_name, c.customer_segment_name,
         count(distinct f.order_id) a, count(distinct (f.source_system, f.order_id)) b
  from analytics.fact_sales_order_item f
  join analytics.dim_date d using (date_key)
  join analytics.dim_sales_channel ch using (sales_channel_key)
  join analytics.dim_customer c using (customer_key)
  where f.is_realised group by 1, 2, 3)
select 'P02' as view, count(*) grupos, count(*) filter (where a <> b) subcontados, sum(b - a) perdidos from g
union all
-- P06: ano-mês × canal × tipo × categoria raiz
select 'P06', count(*), count(*) filter (where a <> b), sum(b - a) from (
  select d.year_month, ch.sales_channel_name, ch.channel_type, cat.root_category_name,
         count(distinct f.order_id) a, count(distinct (f.source_system, f.order_id)) b
  from analytics.fact_sales_order_item f
  join analytics.dim_date d using (date_key)
  join analytics.dim_sales_channel ch using (sales_channel_key)
  join analytics.dim_category cat using (category_key)
  where f.is_realised group by 1, 2, 3, 4) x
union all
-- P05: ano × trimestre × região × estado × canal
select 'P05', count(*), count(*) filter (where a <> b), sum(b - a) from (
  select d.year_number, d.quarter_number, g.region, g.state_code, g.state_name, ch.sales_channel_name,
         count(distinct f.order_id) a, count(distinct (f.source_system, f.order_id)) b
  from analytics.fact_sales_order_item f
  join analytics.dim_date d using (date_key)
  join analytics.dim_geography g using (geography_key)
  join analytics.dim_sales_channel ch using (sales_channel_key)
  where f.is_realised group by 1, 2, 3, 4, 5, 6) y;
-- não aditividade da contagem da P01: pedidos com itens em mais de uma categoria
select count(*) as pedidos_realizados,
       count(*) filter (where n_cat > 1) as com_itens_em_mais_de_uma_categoria
from (select source_system, order_id, count(distinct category_key) n_cat
      from analytics.fact_sales_order_item where is_realised group by 1, 2) p;
-- cobertura do período: primeiro e último dia com venda realizada, e o as_of
select min(order_date) primeiro_dia, max(order_date) ultimo_dia
from analytics.fact_sales_order_item where is_realised;
