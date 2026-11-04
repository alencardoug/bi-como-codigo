-- Runbook H4: the checks stage 1.5 adds that run on the warehouse, against today's
-- data, read-only (ro.sh). eng_dados at c272104. Each section is the dbt test's own SQL
-- with every ref() resolved from eng_dados' manifest; nothing is built, and no dbt
-- command runs — `dbt test` would run the on-run-end grants hook, which writes.
-- 1. invariante_14_lancamento_antes_da_venda (0b8a33c; severity error).
-- 2. p09_capturado_reconcilia_com_a_fato (94e0d09; severity error), with stage 1.5's
--    P09 view inlined in place of the deployed one — what a rebuild would test —,
--    and both totals.
-- 3. The same test against the view deployed today, built before 94e0d09.

\echo '== 1. invariante_14_lancamento_antes_da_venda: failing rows'
select count(*) as failing_rows, count(distinct product_id) as products
from (
select
    i.source_system,
    i.order_item_id,
    i.order_id,
    s.product_id,
    s.launched_at,
    o.placed_at
from "trusted"."order_items" i
join "trusted"."orders" o
    on o.source_system = i.source_system and o.order_id = i.order_id
join "trusted"."product_skus" s
    on s.source_system = i.source_system and s.product_variant_id = i.product_variant_id
where i.source_system = 'retail'
  and s.launched_at > o.placed_at
) t;

\echo '== 2. p09_capturado_reconcilia_com_a_fato, stage 1.5 view inlined: failing rows, then both totals'
select count(*) as failing_rows from (
with na_view as (

    select coalesce(sum(captured_amount), 0) as captured_amount
    from (
with capturado as (

    select source_system, payment_id, sum(captured_amount) as captured_amount
    from "analytics"."fact_payment_transaction"
    where transaction_type = 'capture'
    group by 1, 2

),

autorizacoes as (

    select
        f.*,
        f.approved_authorization_count = 1
        and row_number() over (
            partition by f.source_system, f.payment_id, f.approved_authorization_count
            order by f.occurred_at, f.payment_transaction_id
        ) = 1                                       as is_first_approval
    from "analytics"."fact_payment_transaction" f
    where f.transaction_type = 'authorization'

)

select
    d.year_month,
    d.year_number,
    d.month_number,
    pm.payment_method_name,
    pm.method_type,
    a.installments,
    a.is_instalment_plan,

    sum(a.authorization_count)                      as authorization_attempt_count,
    sum(a.approved_authorization_count)             as approved_authorization_count,
    round(
        100.0 * sum(a.approved_authorization_count)
        / nullif(sum(a.authorization_count), 0), 2
    )                                               as approval_rate_pct,
    sum(a.authorized_amount)                        as authorized_amount,
    coalesce(sum(c.captured_amount) filter (where a.is_first_approval), 0)
                                                    as captured_amount
from autorizacoes a
join "analytics"."dim_date" d using (date_key)
join "analytics"."dim_payment_method" pm using (payment_method_key)
left join capturado c
    on c.source_system = a.source_system and c.payment_id = a.payment_id
group by 1, 2, 3, 4, 5, 6, 7
) as p09_v1_1_0

),

na_fato as (

    select coalesce(sum(captured_amount), 0) as captured_amount
    from "analytics"."fact_payment_transaction"
    where transaction_type = 'capture'

)

select v.captured_amount as na_view, f.captured_amount as na_fato
from na_view v cross join na_fato f
where v.captured_amount <> f.captured_amount
) t;
select (select sum(captured_amount) from (
with capturado as (

    select source_system, payment_id, sum(captured_amount) as captured_amount
    from "analytics"."fact_payment_transaction"
    where transaction_type = 'capture'
    group by 1, 2

),

autorizacoes as (

    select
        f.*,
        f.approved_authorization_count = 1
        and row_number() over (
            partition by f.source_system, f.payment_id, f.approved_authorization_count
            order by f.occurred_at, f.payment_transaction_id
        ) = 1                                       as is_first_approval
    from "analytics"."fact_payment_transaction" f
    where f.transaction_type = 'authorization'

)

select
    d.year_month,
    d.year_number,
    d.month_number,
    pm.payment_method_name,
    pm.method_type,
    a.installments,
    a.is_instalment_plan,

    sum(a.authorization_count)                      as authorization_attempt_count,
    sum(a.approved_authorization_count)             as approved_authorization_count,
    round(
        100.0 * sum(a.approved_authorization_count)
        / nullif(sum(a.authorization_count), 0), 2
    )                                               as approval_rate_pct,
    sum(a.authorized_amount)                        as authorized_amount,
    coalesce(sum(c.captured_amount) filter (where a.is_first_approval), 0)
                                                    as captured_amount
from autorizacoes a
join "analytics"."dim_date" d using (date_key)
join "analytics"."dim_payment_method" pm using (payment_method_key)
left join capturado c
    on c.source_system = a.source_system and c.payment_id = a.payment_id
group by 1, 2, 3, 4, 5, 6, 7
) v) as captured_in_stage_1_5_view,
(select sum(captured_amount) from analytics.fact_payment_transaction where transaction_type = 'capture') as captured_in_fact;

\echo '== 3. p09_capturado_reconcilia_com_a_fato against the view deployed today'
select * from (
with na_view as (

    select coalesce(sum(captured_amount), 0) as captured_amount
    from "consumption"."payment_approval_rate_by_method"

),

na_fato as (

    select coalesce(sum(captured_amount), 0) as captured_amount
    from "analytics"."fact_payment_transaction"
    where transaction_type = 'capture'

)

select v.captured_amount as na_view, f.captured_amount as na_fato
from na_view v cross join na_fato f
where v.captured_amount <> f.captured_amount
) t;
