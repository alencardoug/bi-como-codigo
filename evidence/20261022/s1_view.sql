-- S1: a view da P01 lida pelo papel do consumidor (analyst), em sessão somente leitura.
set role analyst;
select current_user;
select count(*)                                   as linhas,
       count(distinct year_month)                 as meses,
       min(year_month)                            as primeiro_mes,
       max(year_month)                            as ultimo_mes,
       count(distinct sales_channel_name)         as canais,
       count(distinct channel_type)               as tipos_de_canal,
       count(distinct root_category_name)         as categorias_raiz,
       count(distinct category_name)              as categorias,
       sum(net_revenue_amount)                    as receita_liquida_total,
       sum(gross_revenue_amount)                  as receita_bruta_total,
       sum(discount_amount)                       as desconto_total,
       sum(unit_count)                            as unidades,
       max(scale(net_revenue_amount))             as escala_max_liquida,
       min(net_revenue_amount)                    as menor_liquida,
       max(net_revenue_amount)                    as maior_liquida
from consumption.monthly_revenue_by_channel_and_category;
select sales_channel_name, channel_type, count(*) as linhas
from consumption.monthly_revenue_by_channel_and_category group by 1, 2 order by 1;
select root_category_name, count(distinct category_name) as categorias, count(*) as linhas
from consumption.monthly_revenue_by_channel_and_category group by 1 order by 1;
-- tamanho aproximado de uma exportação CSV da view inteira
select pg_size_pretty(sum(octet_length(t::text))::bigint) as tamanho_texto_aprox
from consumption.monthly_revenue_by_channel_and_category t;
-- o analyst não lê a fato (contraprova do caminho de consumo)
