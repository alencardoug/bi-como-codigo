-- O6 / D66: which parent of the 17 rejected items of P13's 12 excluded legacy
-- shipments was rejected? shipment_items has two parents, shipments and
-- order_items. Read-only (ro.sh), on the selected capture.
show default_transaction_read_only;
select now();

with sel as (
    select snapshot_id from staging.legacy_selected_capture
), t as (
    select source_system, shipment_id from trusted.shipments where is_delivered and not is_deleted
), f as (
    select distinct source_system, shipment_id from analytics.fact_shipment_item where is_delivered
), so as (
    select t.shipment_id from t left join f using (source_system, shipment_id)
    where f.shipment_id is null and t.source_system = 'legacy'
), itens as (
    select (r.original_payload->>'shipment_id')::bigint as shipment_id,
           r.original_payload->>'order_item_id' as order_item_id
    from quarantine.rejected_legacy_records r, sel
    where r.snapshot_id = sel.snapshot_id and r.source_table = 'shipment_items'
      and (r.original_payload->>'shipment_id')::bigint in (select shipment_id from so)
), pais_oi as (
    select r.original_payload->>'id' as order_item_id, r.rejection_origin,
           (select string_agg(distinct e->>'code', ',') from jsonb_array_elements(r.findings) e) as codes
    from quarantine.rejected_legacy_records r, sel
    where r.snapshot_id = sel.snapshot_id and r.source_table = 'order_items'
)
select count(*)                                              as rejected_items,
       count(distinct i.shipment_id)                          as shipments,
       count(*) filter (where p.order_item_id is not null)    as order_item_parent_rejected,
       count(*) filter (where p.order_item_id is null)        as order_item_parent_not_rejected,
       string_agg(distinct p.rejection_origin, ',')           as parent_origins,
       string_agg(distinct p.codes, ',')                      as parent_codes,
       count(*) filter (where ts.shipment_id is not null)     as shipment_parent_in_trusted
from itens i
left join pais_oi p using (order_item_id)
left join trusted.shipments ts on ts.source_system = 'legacy' and ts.shipment_id = i.shipment_id;

-- The cascade, followed by the findings themselves: each PARENT_REJECTED
-- finding names its parent table and row. Walk up from the 17 items until a
-- record whose rejection is its own (own_invalid or duplicate_excess).
with recursive sel as (
    select snapshot_id from staging.legacy_selected_capture
), t as (
    select source_system, shipment_id, order_id from trusted.shipments where is_delivered and not is_deleted
), f as (
    select distinct source_system, shipment_id from analytics.fact_shipment_item where is_delivered
), so as (
    select t.shipment_id, t.order_id from t left join f using (source_system, shipment_id)
    where f.shipment_id is null and t.source_system = 'legacy'
), rq as (
    select r.source_table, r.original_payload->>'id' as row_id, r.rejection_origin, r.findings
    from quarantine.rejected_legacy_records r, sel
    where r.snapshot_id = sel.snapshot_id
), cadeia(level, source_table, row_id, rejection_origin, findings) as (
    select 0, q.source_table, q.row_id, q.rejection_origin, q.findings
    from rq q
    where q.source_table = 'shipment_items'
      and q.row_id in (
        select r.original_payload->>'id' from quarantine.rejected_legacy_records r, sel
        where r.snapshot_id = sel.snapshot_id and r.source_table = 'shipment_items'
          and (r.original_payload->>'shipment_id')::bigint in (select shipment_id from so))
    union all
    select c.level + 1, p.source_table, p.row_id, p.rejection_origin, p.findings
    from cadeia c
    cross join lateral jsonb_array_elements(c.findings) e
    join rq p on p.source_table = e->'context'->>'parent_table'
             and p.row_id = e->'context'->>'parent_row_id'
    where e->>'code' = 'PARENT_REJECTED' and c.level < 6
)
select level, source_table, rejection_origin,
       count(distinct row_id) as records,
       (select string_agg(distinct e->>'code', ',') from cadeia c2, jsonb_array_elements(c2.findings) e
         where c2.level = c.level and c2.source_table = c.source_table) as codes
from cadeia c
group by 1, 2, 3 order by 1, 2;

-- And the shipments' own orders: in trusted?
with t as (
    select source_system, shipment_id, order_id from trusted.shipments where is_delivered and not is_deleted
), f as (
    select distinct source_system, shipment_id from analytics.fact_shipment_item where is_delivered
), so as (
    select t.shipment_id, t.order_id from t left join f using (source_system, shipment_id)
    where f.shipment_id is null and t.source_system = 'legacy'
)
select count(*) as excluded_shipments,
       count(o.order_id) as with_order_in_trusted,
       count(*) filter (where o.item_count = 0 or o.item_count is null) as order_without_trusted_items
from so left join trusted.orders o on o.source_system = 'legacy' and o.order_id = so.order_id;
