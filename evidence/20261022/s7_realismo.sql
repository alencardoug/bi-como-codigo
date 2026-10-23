-- S7: afinidade categoria × preço (Geração de Dados §5) e lançamento × venda (D65), no varejo.
select cat.category_name, cat.root_category_name,
       count(*) as itens, round(avg(f.unit_price), 2) as preco_medio,
       round(min(f.unit_price), 2) as preco_min, round(max(f.unit_price), 2) as preco_max
from analytics.fact_sales_order_item f
join analytics.dim_category cat using (category_key)
where f.source_system = 'retail'
group by 1, 2 order by preco_medio;
select count(*) as itens_retail,
       count(*) filter (where f.placed_at < p.launched_at) as vendidos_antes_do_lancamento
from analytics.fact_sales_order_item f
join analytics.dim_product p using (product_key)
where f.source_system = 'retail';
