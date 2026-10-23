-- S8: os grupos subcontados hoje em P05 e P06, e a escala do desconto por origem no trusted.
select 'P06' as view, d.year_month::text as periodo, ch.sales_channel_name, cat.root_category_name as recorte,
       count(distinct f.order_id) as como_na_view, count(distinct (f.source_system, f.order_id)) as com_origem
from analytics.fact_sales_order_item f
join analytics.dim_date d using (date_key)
join analytics.dim_sales_channel ch using (sales_channel_key)
join analytics.dim_category cat using (category_key)
where f.is_realised
group by d.year_month, ch.sales_channel_name, ch.channel_type, cat.root_category_name
having count(distinct f.order_id) <> count(distinct (f.source_system, f.order_id))
union all
select 'P05', d.year_number || '-T' || d.quarter_number, ch.sales_channel_name, g.state_code,
       count(distinct f.order_id), count(distinct (f.source_system, f.order_id))
from analytics.fact_sales_order_item f
join analytics.dim_date d using (date_key)
join analytics.dim_geography g using (geography_key)
join analytics.dim_sales_channel ch using (sales_channel_key)
where f.is_realised
group by d.year_number, d.quarter_number, g.region, g.state_code, g.state_name, ch.sales_channel_name
having count(distinct f.order_id) <> count(distinct (f.source_system, f.order_id));
select source_system, min(scale(discount_amount)) as escala_min, max(scale(discount_amount)) as escala_max,
       min(scale(unit_price)) as escala_preco_min, max(scale(unit_price)) as escala_preco_max
from trusted.order_items group by 1 order by 1;
