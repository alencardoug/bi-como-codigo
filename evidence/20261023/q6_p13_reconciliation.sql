-- The P13 check of runbook lines E1 and E11 (RR-09), read-only (ro.sh).
-- 1. P13's digest at its grain: E11 must give E1's.
-- 2. P13 counts each delivered shipment of its fact once.
-- 3. trusted.shipments against the fact, by (source_system, shipment_id).
-- 4. Every delivered shipment the fact leaves out, traced to the quarantine of
--    the selected capture: no item in trusted, at least one rejected item.
-- Expected at E1 and E11: p13_grain_ok t; fact_only 0; retail_trusted_only 0;
-- untraced 0. The digest and the counts are recorded, not fixed here.
show default_transaction_read_only;

select count(*) as p13_rows,
       encode(sha256(convert_to(string_agg(
           concat_ws('|', year_number, month_number, year_month, carrier_name, service_level,
                     warehouse_name, warehouse_region, p::text),
           E'\n' order by year_number, month_number, carrier_name, service_level, warehouse_name, p::text
       ), 'UTF8')), 'hex') as p13_digest
from consumption.on_time_delivery_rate_by_carrier p;

with f as (
    select distinct source_system, shipment_id from analytics.fact_shipment_item where is_delivered
)
select (select sum(delivered_count) from consumption.on_time_delivery_rate_by_carrier) as p13_delivered,
       (select count(*) from f) as fact_delivered,
       (select sum(delivered_count) from consumption.on_time_delivery_rate_by_carrier)
           = (select count(*) from f) as p13_grain_ok;

with t as (
    select source_system, shipment_id from trusted.shipments where is_delivered and not is_deleted
), f as (
    select distinct source_system, shipment_id from analytics.fact_shipment_item where is_delivered
)
select (select count(*) from t) as trusted_delivered,
       (select count(*) from t left join f using (source_system, shipment_id)
         where f.shipment_id is null and t.source_system = 'retail') as retail_trusted_only,
       (select count(*) from t left join f using (source_system, shipment_id)
         where f.shipment_id is null and t.source_system = 'legacy') as legacy_trusted_only,
       (select count(*) from f left join t using (source_system, shipment_id)
         where t.shipment_id is null) as fact_only;

with sel as (
    select snapshot_id from staging.legacy_selected_capture
), t as (
    select source_system, shipment_id from trusted.shipments where is_delivered and not is_deleted
), f as (
    select distinct source_system, shipment_id from analytics.fact_shipment_item where is_delivered
), so as (
    select t.source_system, t.shipment_id from t left join f using (source_system, shipment_id)
    where f.shipment_id is null
), q as (
    select distinct r.source_system, (r.original_payload->>'shipment_id')::bigint as shipment_id
    from quarantine.rejected_legacy_records r, sel
    where r.snapshot_id = sel.snapshot_id and r.source_table = 'shipment_items'
      and r.classification = 'rejected'
)
select (select snapshot_id from sel) as selected_capture,
       count(*) as trusted_only,
       count(*) filter (
           where q.shipment_id is not null
             and not exists (select 1 from trusted.shipment_items i
                             where i.source_system = so.source_system and i.shipment_id = so.shipment_id)
       ) as traced,
       count(*) filter (
           where q.shipment_id is null
              or exists (select 1 from trusted.shipment_items i
                         where i.source_system = so.source_system and i.shipment_id = so.shipment_id)
       ) as untraced
from so left join q using (source_system, shipment_id);
