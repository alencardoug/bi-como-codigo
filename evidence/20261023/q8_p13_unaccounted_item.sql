-- RR-20, negative case: q7's item-level check must reject an excluded shipment
-- with a raw item that no classification explains — the case q6 accepts. Read-only
-- (ro.sh): q7's section 4, with one synthetic raw item added in a CTE.
-- Expected: unaccounted_items 1.
show default_transaction_read_only;

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
    -- The counterexample of RR-20: one more raw item of an excluded shipment,
    -- with no classification. Nothing is written: it exists only in this CTE.
    union all
    select -1, (select min(shipment_id) from excluded)
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
