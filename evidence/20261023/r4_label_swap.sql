-- RV2-03: trocar dois rótulos de canal preserva contagem e somas globais; só a comparação linha a linha acusa.
begin isolation level repeatable read read only;
set role analyst;
with v as (select * from consumption.monthly_revenue_by_channel_and_category),
trocada as (
  select case sales_channel_name when 'Aplicativo' then 'Loja física' when 'Loja física' then 'Aplicativo'
              else sales_channel_name end as sales_channel_name,
         year_month, category_name, net_revenue_amount, unit_count
  from v)
select 'original' as pacote, count(*) as linhas, sum(net_revenue_amount) as liquida, sum(unit_count) as unidades from v
union all
select 'rotulos trocados', count(*), sum(net_revenue_amount), sum(unit_count) from trocada;
with v as (select * from consumption.monthly_revenue_by_channel_and_category),
trocada as (
  select case sales_channel_name when 'Aplicativo' then 'Loja física' when 'Loja física' then 'Aplicativo'
              else sales_channel_name end as sales_channel_name,
         year_month, category_name, root_category_name, channel_type, net_revenue_amount from v)
select count(*) as linhas_que_divergem_da_view
from (select sales_channel_name, year_month, category_name, net_revenue_amount from trocada
      except select sales_channel_name, year_month, category_name, net_revenue_amount from v) x;
rollback;
