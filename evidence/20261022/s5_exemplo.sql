-- S5: o candidato histórico da trilha (ORD-0000037) e o que ele ilustra hoje.
select f.source_system, f.order_id, f.order_item_id, f.order_number, f.order_status, f.is_realised,
       f.order_date, d.year_month, ch.sales_channel_name, cat.root_category_name, cat.category_name,
       f.quantity, f.unit_price, f.quantity * f.unit_price as bruto_exato,
       f.gross_revenue_amount, f.discount_amount, f.net_revenue_amount
from analytics.fact_sales_order_item f
join analytics.dim_date d using (date_key)
join analytics.dim_sales_channel ch using (sales_channel_key)
join analytics.dim_category cat using (category_key)
where f.order_number = 'ORD-0000037'
order by f.source_system, f.order_item_id;
-- quantos itens realizados têm arredondamento visível e desconto, por origem
select source_system,
       count(*) as itens_realizados,
       count(*) filter (where quantity * unit_price <> round(quantity * unit_price, 2)) as com_arredondamento,
       count(*) filter (where discount_amount > 0) as com_desconto,
       count(*) filter (where discount_amount > 0 and quantity > 1
                        and quantity * unit_price <> round(quantity * unit_price, 2)) as com_os_tres
from analytics.fact_sales_order_item where is_realised group by 1;
