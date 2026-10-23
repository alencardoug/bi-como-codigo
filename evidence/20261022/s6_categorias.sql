set role analyst;
select root_category_name, category_name, count(*) as linhas_na_view, sum(net_revenue_amount) as liquida
from consumption.monthly_revenue_by_channel_and_category
group by 1, 2 order by 1, 2;
