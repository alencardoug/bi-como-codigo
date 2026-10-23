-- RR-09: where did the items of the 12 delivered legacy shipments go?
-- Read-only (ro.sh). Traces each trusted-only shipment to the legacy quarantine
-- of the selected capture, by the shipment_id in the item payload.
show default_transaction_read_only;

with sel as (
    select snapshot_id from staging.legacy_selected_capture
), t as (
    select source_system, shipment_id from trusted.shipments where is_delivered and not is_deleted
), f as (
    select distinct source_system, shipment_id from analytics.fact_shipment_item where is_delivered
), so as (
    select t.shipment_id from t left join f using (source_system, shipment_id)
    where f.shipment_id is null and t.source_system = 'legacy'
), q as (
    select (original_payload->>'shipment_id')::bigint as shipment_id,
           rejection_origin,
           (select string_agg(distinct e->>'code', ',') from jsonb_array_elements(findings) e) as codes
    from quarantine.rejected_legacy_records r, sel
    where r.snapshot_id = sel.snapshot_id and r.source_table = 'shipment_items'
)
select so.shipment_id,
       count(q.shipment_id) as quarantined_items,
       string_agg(distinct q.rejection_origin, ',') as origins,
       string_agg(distinct q.codes, ',') as finding_codes
from so left join q using (shipment_id)
group by 1 order by 1;

-- Summary: trusted-only legacy shipments with and without a quarantined item.
with sel as (
    select snapshot_id from staging.legacy_selected_capture
), t as (
    select source_system, shipment_id from trusted.shipments where is_delivered and not is_deleted
), f as (
    select distinct source_system, shipment_id from analytics.fact_shipment_item where is_delivered
), so as (
    select t.shipment_id from t left join f using (source_system, shipment_id)
    where f.shipment_id is null and t.source_system = 'legacy'
), q as (
    select distinct (original_payload->>'shipment_id')::bigint as shipment_id
    from quarantine.rejected_legacy_records r, sel
    where r.snapshot_id = sel.snapshot_id and r.source_table = 'shipment_items'
)
select count(*) as trusted_only_legacy,
       count(*) filter (where q.shipment_id is not null) as traced_to_quarantine,
       count(*) filter (where q.shipment_id is null) as untraced
from so left join q using (shipment_id);
