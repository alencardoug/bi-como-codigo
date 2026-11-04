-- Runbook H5, M3 on the views (D5): the order count of P01, P02, P05 and P06 recounted from
-- the fact at each view's grain and filter with the composite identity (source_system,
-- order_id), and compared with the view row by row, both ways (`except all`, nulls equal).
-- Read-only (ro.sh).
-- Expected: differing_rows 0 and view_groups = recounted_groups in every view. A group whose
-- count differs gives two rows, one that only one side has gives one.
-- groups_a_count_without_source_would_miss shows the probe is not vacuous: where it is above 0,
-- a view counting order_id alone would differ there (M3 found 1 group in P05 and 1 in P06 on
-- 2026-10-22, fixed by stage 1.1 in eng_dados 9c9ff9c).

\echo '== P01 — consumption.monthly_revenue_by_channel_and_category'
with recount as (
    select d.year_month, ch.sales_channel_name, ch.channel_type, cat.root_category_name, cat.category_name,
           count(distinct (f.source_system, f.order_id)) as with_source,
           count(distinct f.order_id)                    as without_source
    from analytics.fact_sales_order_item f
    join analytics.dim_date d using (date_key)
    join analytics.dim_sales_channel ch using (sales_channel_key)
    join analytics.dim_category cat using (category_key)
    where f.is_realised
    group by 1, 2, 3, 4, 5
),
in_view as (select year_month, sales_channel_name, channel_type, root_category_name, category_name, order_count from consumption.monthly_revenue_by_channel_and_category),
recounted as (select year_month, sales_channel_name, channel_type, root_category_name, category_name, with_source as order_count from recount),
differing as (
    (select * from in_view except all select * from recounted)
    union all
    (select * from recounted except all select * from in_view)
)
select 'P01' as view,
       (select count(*) from in_view)                                      as view_groups,
       (select count(*) from recount)                                      as recounted_groups,
       (select count(*) from differing)                                    as differing_rows,
       (select count(*) from recount where with_source <> without_source)  as groups_a_count_without_source_would_miss;

\echo '== P02 — consumption.average_order_value_by_channel_and_segment'
with recount as (
    select d.year_month, ch.sales_channel_name, c.customer_segment_name,
           count(distinct (f.source_system, f.order_id)) as with_source,
           count(distinct f.order_id)                    as without_source
    from analytics.fact_sales_order_item f
    join analytics.dim_date d using (date_key)
    join analytics.dim_sales_channel ch using (sales_channel_key)
    join analytics.dim_customer c using (customer_key)
    where f.is_realised
    group by 1, 2, 3
),
in_view as (select year_month, sales_channel_name, customer_segment_name, order_count from consumption.average_order_value_by_channel_and_segment),
recounted as (select year_month, sales_channel_name, customer_segment_name, with_source as order_count from recount),
differing as (
    (select * from in_view except all select * from recounted)
    union all
    (select * from recounted except all select * from in_view)
)
select 'P02' as view,
       (select count(*) from in_view)                                      as view_groups,
       (select count(*) from recount)                                      as recounted_groups,
       (select count(*) from differing)                                    as differing_rows,
       (select count(*) from recount where with_source <> without_source)  as groups_a_count_without_source_would_miss;

\echo '== P05 — consumption.revenue_by_delivery_region'
with recount as (
    select d.year_number, d.quarter_number, g.region, g.state_code, g.state_name, ch.sales_channel_name,
           count(distinct (f.source_system, f.order_id)) as with_source,
           count(distinct f.order_id)                    as without_source
    from analytics.fact_sales_order_item f
    join analytics.dim_date d using (date_key)
    join analytics.dim_geography g using (geography_key)
    join analytics.dim_sales_channel ch using (sales_channel_key)
    where f.is_realised
    group by 1, 2, 3, 4, 5, 6
),
in_view as (select year_number, quarter_number, region, state_code, state_name, sales_channel_name, order_count from consumption.revenue_by_delivery_region),
recounted as (select year_number, quarter_number, region, state_code, state_name, sales_channel_name, with_source as order_count from recount),
differing as (
    (select * from in_view except all select * from recounted)
    union all
    (select * from recounted except all select * from in_view)
)
select 'P05' as view,
       (select count(*) from in_view)                                      as view_groups,
       (select count(*) from recount)                                      as recounted_groups,
       (select count(*) from differing)                                    as differing_rows,
       (select count(*) from recount where with_source <> without_source)  as groups_a_count_without_source_would_miss;

\echo '== P06 — consumption.discount_share_by_channel'
with recount as (
    select d.year_month, ch.sales_channel_name, ch.channel_type, cat.root_category_name,
           count(distinct (f.source_system, f.order_id)) as with_source,
           count(distinct f.order_id)                    as without_source
    from analytics.fact_sales_order_item f
    join analytics.dim_date d using (date_key)
    join analytics.dim_sales_channel ch using (sales_channel_key)
    join analytics.dim_category cat using (category_key)
    where f.is_realised
    group by 1, 2, 3, 4
),
in_view as (select year_month, sales_channel_name, channel_type, root_category_name, order_count from consumption.discount_share_by_channel),
recounted as (select year_month, sales_channel_name, channel_type, root_category_name, with_source as order_count from recount),
differing as (
    (select * from in_view except all select * from recounted)
    union all
    (select * from recounted except all select * from in_view)
)
select 'P06' as view,
       (select count(*) from in_view)                                      as view_groups,
       (select count(*) from recount)                                      as recounted_groups,
       (select count(*) from differing)                                    as differing_rows,
       (select count(*) from recount where with_source <> without_source)  as groups_a_count_without_source_would_miss;
