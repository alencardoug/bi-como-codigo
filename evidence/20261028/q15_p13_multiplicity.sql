-- RR-30, the negative cases: q14's section 4 on CTE scenarios, read-only
-- (ro.sh). Nothing is written: each scenario changes the selected capture's raw
-- items or its classifications only inside CTEs, keyed by the scenario's name;
-- trusted, the fact and the quarantine are read as they are.
--   today                     — the warehouse as it is.
--   duplicate_classification  — the lowest eligible classification of a
--                               delivered legacy shipment repeated by UNION ALL,
--                               Codex's model of RR-30.
--   duplicate_raw             — the raw row of that same item repeated.
-- Expected: the multiplicity counters 0 only for today, each scenario flagged by
-- its own counter; every loss counter 0 in every scenario — q11's anti-joins
-- accept both duplicates, which is the hole q14 closes.
show default_transaction_read_only;

with cases(name) as (
    values ('today'), ('duplicate_classification'), ('duplicate_raw')
), sel as (
    select snapshot_id from staging.legacy_selected_capture
), cur as (
    select distinct source_system, snapshot_id, catalog_version, treatment_fingerprint
    from trusted.legacy_classifications
), cls_today as (
    select c.*
    from trusted.legacy_classifications c
    join cur using (source_system, snapshot_id, catalog_version, treatment_fingerprint)
    join sel using (snapshot_id)
    where c.source_system = 'legacy' and c.source_table = 'shipment_items'
), t as (
    select shipment_id from trusted.shipments
    where source_system = 'legacy' and is_delivered and not is_deleted
), target as (
    -- The lowest eligible classification of a delivered legacy shipment.
    select min(c.legacy_row_id) as legacy_row_id
    from cls_today c
    join t on pg_input_is_valid(c.cleaned_payload->>'shipment_id', 'bigint')
          and t.shipment_id = (c.cleaned_payload->>'shipment_id')::bigint
    where c.classification in ('accepted', 'corrected')
),
-- ── The relations, per scenario ─────────────────────────────────────────────
raw_items as (
    select k.name, r.legacy_row_id
    from cases k cross join raw_legacy.shipment_items r, sel
    where r._airbyte_meta->>'sync_id' = sel.snapshot_id::text
    union all
    select 'duplicate_raw', r.legacy_row_id
    from raw_legacy.shipment_items r, sel
    where r._airbyte_meta->>'sync_id' = sel.snapshot_id::text
      and r.legacy_row_id = (select legacy_row_id from target)
), cls as (
    select k.name, c.*
    from cases k cross join cls_today c
    union all
    select 'duplicate_classification', c.*
    from cls_today c
    where c.legacy_row_id = (select legacy_row_id from target)
),
-- ── q14's section 4, verbatim but for the scenario key ──────────────────────
excluded as (
    select t.shipment_id from t
    where not exists (select 1 from analytics.fact_shipment_item f
                       where f.source_system = 'legacy' and f.shipment_id = t.shipment_id and f.is_delivered)
), items as (
    select c.name, c.legacy_row_id, t.shipment_id, c.classification,
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
select k.name as scenario,
       (select count(*) from (select legacy_row_id from raw_items r where r.name = k.name
                               group by legacy_row_id having count(*) > 1) d) as nonunique_raw_identities,
       (select count(*) from (select 1 from cls c where c.name = k.name
                               group by source_system, snapshot_id, source_table, legacy_row_id,
                                        catalog_version, treatment_fingerprint
                               having count(*) > 1) d) as nonunique_classification_identities,
       (select count(*) from raw_items r
         where r.name = k.name
           and not exists (select 1 from cls c where c.name = k.name and c.legacy_row_id = r.legacy_row_id)) as raw_without_classification,
       (select count(*) from cls c
         where c.name = k.name
           and not exists (select 1 from raw_items r where r.name = k.name and r.legacy_row_id = c.legacy_row_id)) as classification_without_raw,
       (select count(*) from items i where i.name = k.name) as delivered_items,
       (select count(*) from items i where i.name = k.name and i.classification in ('accepted', 'corrected')) as eligible_items,
       (select count(*) from items i where i.name = k.name
           and i.classification in ('accepted', 'corrected') and not i.own_trusted_item) as eligible_trusted_missing,
       (select count(*) from items i where i.name = k.name
           and i.classification in ('accepted', 'corrected') and not i.own_fact_item) as eligible_fact_missing,
       (select count(*) from items i where i.name = k.name
           and i.classification = 'rejected' and not i.in_current_quarantine) as rejected_quarantine_stale,
       (select count(*) from items i where i.name = k.name
           and i.in_excluded_shipment and i.classification <> 'rejected') as unexplained_exclusion_items
from cases k
order by array_position(array['today', 'duplicate_classification', 'duplicate_raw'], k.name);
