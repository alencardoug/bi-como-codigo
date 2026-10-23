-- The P13 check of runbook lines E1 and E11 (RR-09, RR-20, RR-23), read-only (ro.sh).
-- Supersedes q7 as the runbook's command; q7 stays as the record of M32.
-- 1. P13's digest at its grain: E11 must give E1's.
-- 2. P13's grain unique, and each delivered shipment of its fact counted once.
-- 3. trusted.shipments against the fact, by (source_system, shipment_id), and
--    every trusted item of a delivered shipment in the fact, by
--    (source_system, shipment_item_id).
-- 4. The selected capture's shipment items, each resolved by itself: every raw
--    row has exactly one classification of the current treatment; every
--    accepted or corrected item of a delivered legacy shipment is its own
--    trusted item and its own fact item, by the cleaned key; every rejected one
--    is in the quarantine under the same treatment identity — source, capture,
--    table, raw identity, catalogue version, fingerprint — with the same
--    classification, origin and findings; and every delivered legacy shipment
--    the fact leaves out has items, all of them rejected that way.
-- Expected at E1 and E11: duplicate_p13_groups 0, p13_counts_each_once t,
-- fact_only 0, retail_trusted_only 0, trusted_items_missing_fact 0,
-- current_treatments 1, raw_without_classification 0,
-- classification_without_raw 0, and every count of section 4 named
-- *_missing, *_stale, *_without_* or unexplained_* 0. Digest, counts and
-- origins are recorded, not fixed here.
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

-- 3. Both ways, by shipment key; and every trusted item of a delivered shipment in the fact.
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
         where t.shipment_id is null) as fact_only,
       (select count(*) from trusted.shipment_items i
          join t using (source_system, shipment_id)
         where not exists (select 1 from analytics.fact_shipment_item x
                            where x.source_system = i.source_system
                              and x.shipment_item_id = i.shipment_item_id)) as trusted_items_missing_fact;

-- 4. The selected capture's shipment items, one by one.
with sel as (
    select snapshot_id from staging.legacy_selected_capture
), cur as (
    select distinct source_system, snapshot_id, catalog_version, treatment_fingerprint
    from trusted.legacy_classifications
), raw_items as (
    select r.legacy_row_id
    from raw_legacy.shipment_items r, sel
    where r._airbyte_meta->>'sync_id' = sel.snapshot_id::text
), cls as (
    select c.*
    from trusted.legacy_classifications c
    join cur using (source_system, snapshot_id, catalog_version, treatment_fingerprint)
    join sel using (snapshot_id)
    where c.source_system = 'legacy' and c.source_table = 'shipment_items'
), t as (
    select shipment_id from trusted.shipments
    where source_system = 'legacy' and is_delivered and not is_deleted
), excluded as (
    select t.shipment_id from t
    where not exists (select 1 from analytics.fact_shipment_item f
                       where f.source_system = 'legacy' and f.shipment_id = t.shipment_id and f.is_delivered)
), items as (
    -- Every classified item of a delivered legacy shipment, attributed by its cleaned shipment key.
    select c.legacy_row_id, t.shipment_id, c.classification, c.rejection_origin,
           (t.shipment_id in (select shipment_id from excluded)) as in_excluded_shipment,
           c.classification in ('accepted', 'corrected')
               and exists (select 1 from trusted.shipment_items i
                            where i.source_system = 'legacy'
                              and i.shipment_item_id = (c.cleaned_payload->>'id')::bigint
                              and i.shipment_id = t.shipment_id) as own_trusted_item,
           c.classification in ('accepted', 'corrected')
               and exists (select 1 from analytics.fact_shipment_item f
                            where f.source_system = 'legacy'
                              and f.shipment_item_id = (c.cleaned_payload->>'id')::bigint
                              and f.shipment_id = t.shipment_id) as own_fact_item,
           c.classification = 'rejected'
               and exists (select 1 from quarantine.rejected_legacy_records q
                            where q.source_system = c.source_system and q.snapshot_id = c.snapshot_id
                              and q.source_table = c.source_table and q.legacy_row_id = c.legacy_row_id
                              and q.catalog_version = c.catalog_version
                              and q.treatment_fingerprint = c.treatment_fingerprint
                              and q.classification = c.classification
                              and q.rejection_origin is not distinct from c.rejection_origin
                              and q.findings = c.findings) as in_current_quarantine
    from cls c
    join t on pg_input_is_valid(c.cleaned_payload->>'shipment_id', 'bigint')
          and t.shipment_id = (c.cleaned_payload->>'shipment_id')::bigint
)
select (select count(*) from cur) as current_treatments,
       (select count(*) from raw_items r
         where not exists (select 1 from cls c where c.legacy_row_id = r.legacy_row_id)) as raw_without_classification,
       (select count(*) from cls c
         where not exists (select 1 from raw_items r where r.legacy_row_id = c.legacy_row_id)) as classification_without_raw,
       (select count(*) from excluded) as excluded_shipments,
       (select count(*) from excluded e
         where not exists (select 1 from items i where i.shipment_id = e.shipment_id)) as excluded_without_items,
       count(*) as delivered_items,
       count(*) filter (where classification in ('accepted', 'corrected')) as eligible_items,
       count(*) filter (where classification in ('accepted', 'corrected') and not own_trusted_item) as eligible_trusted_missing,
       count(*) filter (where classification in ('accepted', 'corrected') and not own_fact_item) as eligible_fact_missing,
       count(*) filter (where classification = 'rejected') as rejected_items,
       count(*) filter (where classification = 'rejected' and not in_current_quarantine) as rejected_quarantine_stale,
       count(*) filter (where in_excluded_shipment and classification <> 'rejected') as unexplained_exclusion_items,
       string_agg(distinct rejection_origin, ',') filter (where in_excluded_shipment) as excluded_rejection_origins
from items;
