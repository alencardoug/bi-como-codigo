-- S2: a contagem de pedidos da P01 sem source_system. Recalcula, no mesmo grão e
-- com o mesmo filtro da view, a contagem com a identidade composta.
with grupos as (
    select d.year_month, ch.sales_channel_name, ch.channel_type,
           cat.root_category_name, cat.category_name,
           count(distinct f.order_id)                          as como_na_view,
           count(distinct (f.source_system, f.order_id))       as com_origem
    from analytics.fact_sales_order_item f
    join analytics.dim_date d using (date_key)
    join analytics.dim_sales_channel ch using (sales_channel_key)
    join analytics.dim_category cat using (category_key)
    where f.is_realised
    group by 1, 2, 3, 4, 5
)
select count(*)                                        as grupos,
       count(*) filter (where como_na_view <> com_origem) as grupos_subcontados,
       sum(como_na_view)                               as soma_como_na_view,
       sum(com_origem)                                 as soma_com_origem,
       sum(com_origem - como_na_view)                  as pedidos_perdidos,
       max(com_origem - como_na_view)                  as maior_perda_num_grupo
from grupos;
-- confere que o recálculo reproduz a view (mesmo grão, mesma contagem)
with grupos as (
    select d.year_month, ch.sales_channel_name, ch.channel_type,
           cat.root_category_name, cat.category_name,
           count(distinct f.order_id) as como_na_view, sum(f.net_revenue_amount) as liquida
    from analytics.fact_sales_order_item f
    join analytics.dim_date d using (date_key)
    join analytics.dim_sales_channel ch using (sales_channel_key)
    join analytics.dim_category cat using (category_key)
    where f.is_realised
    group by 1, 2, 3, 4, 5
)
select count(*) as linhas_que_divergem_da_view
from grupos g
full join consumption.monthly_revenue_by_channel_and_category v
  on v.year_month = g.year_month and v.sales_channel_name = g.sales_channel_name
 and v.channel_type = g.channel_type and v.root_category_name = g.root_category_name
 and v.category_name = g.category_name
where v.year_month is null or g.year_month is null
   or v.order_count <> g.como_na_view or v.net_revenue_amount <> g.liquida;
-- sobreposição de order_id entre as origens na fato (realizados)
select count(*) as order_ids_nas_duas_origens
from (select order_id from analytics.fact_sales_order_item where is_realised
      group by order_id having count(distinct source_system) > 1) x;
select source_system, count(distinct order_id) as pedidos, count(*) as itens,
       min(order_id) as menor_id, max(order_id) as maior_id
from analytics.fact_sales_order_item where is_realised group by 1;
