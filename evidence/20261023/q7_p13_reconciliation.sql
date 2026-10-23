-- The P13 check of runbook lines E1 and E11 (RR-09, RR-20), read-only (ro.sh).
-- Supersedes q6 as the runbook's command; q6 stays as the record of M27.
-- 1. P13's digest at its grain: E11 must give E1's.
-- 2. P13's grain unique, and each delivered shipment of its fact counted once.
-- 3. trusted.shipments against the fact, by (source_system, shipment_id).
-- 4. Every delivered shipment the fact leaves out, item by item: every raw item
--    of the selected capture classified, every rejected one in the quarantine,
--    and none accepted or corrected missing from trusted.
-- Expected at E1 and E11: duplicate_p13_groups 0, p13_counts_each_once t,
-- fact_only 0, retail_trusted_only 0, shipments_without_raw_items 0,
-- unaccounted_items 0. Digest, counts and reasons are recorded, not fixed here.
show default_transaction_read_only;

select count(*) as p13_rows,
       encode(sha256(convert_to(string_agg(
           concat_ws('|', year_number, month_number, year_month, carrier_name, service_level,
                     warehouse_name, warehouse_region, p::text),
           E'\n' order by year_number, month_number, carrier_name, service_level, warehouse_name, p::text
       ), 'UTF8')), 'hex') as p13_digest
from consumption.on_time_delivery_rate_by_carrier p;

-- 2. Grain: the five columns the view groups by identify one row; and the counts add up.
with f as (
    select distinct source_system, shipment_id from analytics.fact_shipment_item where is_delivered
)
select (select count(*) - count(distinct (year_number, month_number, carrier_name, service_level, warehouse_name))
          from consumption.on_time_delivery_rate_by_carrier) as duplicate_p13_groups,
       (select sum(delivered_count) from consumption.on_time_delivery_rate_by_carrier) as p13_delivered,
       (select count(*) from f) as fact_delivered,
       (select sum(delivered_count) from consumption.on_time_delivery_rate_by_carrier)
           = (select count(*) from f) as p13_counts_each_once;

-- 3. Both ways, by key.
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

-- 4. Item by item, for every legacy shipment the fact leaves out.
with sel as (
    select snapshot_id from staging.legacy_selected_capture
), t as (
    select source_system, shipment_id from trusted.shipments where is_delivered and not is_deleted
), f as (
    select distinct source_system, shipment_id from analytics.fact_shipment_item where is_delivered
), excluded as (
    select t.shipment_id from t left join f using (source_system, shipment_id)
    where f.shipment_id is null and t.source_system = 'legacy'
), raw_items as (
    select r.legacy_row_id, r.shipment_id::bigint as shipment_id
    from raw_legacy.shipment_items r, sel
    where r._airbyte_meta->>'sync_id' = sel.snapshot_id::text
      and r.shipment_id::bigint in (select shipment_id from excluded)
), items as (
    select ri.shipment_id, ri.legacy_row_id, c.classification, c.rejection_origin,
           exists (select 1 from quarantine.rejected_legacy_records q, sel
                   where q.snapshot_id = sel.snapshot_id and q.source_table = 'shipment_items'
                     and q.legacy_row_id = ri.legacy_row_id) as in_quarantine,
           exists (select 1 from trusted.shipment_items i
                   where i.source_system = 'legacy' and i.shipment_id = ri.shipment_id) as shipment_has_trusted_item
    from raw_items ri
    left join trusted.legacy_classifications c
      on c.snapshot_id = (select snapshot_id from sel) and c.source_table = 'shipment_items'
     and c.legacy_row_id = ri.legacy_row_id
)
select (select count(*) from excluded) as excluded_shipments,
       (select count(*) from excluded e
         where not exists (select 1 from raw_items ri where ri.shipment_id = e.shipment_id)) as shipments_without_raw_items,
       count(*) as raw_items,
       count(*) filter (where classification = 'rejected' and in_quarantine) as rejected_in_quarantine,
       count(*) filter (
           where classification is null
              or (classification = 'rejected' and not in_quarantine)
              or (classification in ('accepted', 'corrected') and not shipment_has_trusted_item)
       ) as unaccounted_items,
       string_agg(distinct rejection_origin, ',') as rejection_origins
from items;
