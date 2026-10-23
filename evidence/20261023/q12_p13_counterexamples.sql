-- RR-23, the negative cases: q7's item predicate against q11's, on the same
-- scenarios, read-only (ro.sh). Nothing is written: each scenario changes the
-- relations only inside CTEs, keyed by the scenario's name.
--   today            — the warehouse as it is.
--   fact_missing     — a delivered legacy shipment T that is in the fact, with
--                      two or more eligible items, left out of the fact whole;
--                      its trusted items stay.
--   sibling          — as fact_missing, and one of T's trusted items missing
--                      too: one accepted sibling hides it from q7.
--   stale_treatment  — one rejected item of an excluded shipment whose only
--                      quarantine row is an older treatment of the same
--                      capture, with another origin and other findings.
-- Expected: q7 reports 0 in every scenario; q11 reports 0 only for today.
show default_transaction_read_only;

with recursive cases(name) as (
    values ('today'), ('fact_missing'), ('sibling'), ('stale_treatment')
), sel as (
    select snapshot_id from staging.legacy_selected_capture
), target_shipment as (
    -- The lowest delivered legacy shipment of the fact with two or more trusted items.
    select min(shipment_id) as shipment_id from (
        select f.shipment_id from analytics.fact_shipment_item f
        where f.source_system = 'legacy' and f.is_delivered
        group by f.shipment_id having count(*) >= 2
    ) s
), target_item as (
    select max(i.shipment_item_id) as shipment_item_id
    from trusted.shipment_items i, target_shipment ts
    where i.source_system = 'legacy' and i.shipment_id = ts.shipment_id
), excluded_today as (
    select t.shipment_id from trusted.shipments t
    where t.source_system = 'legacy' and t.is_delivered and not t.is_deleted
      and not exists (select 1 from analytics.fact_shipment_item f
                       where f.source_system = 'legacy' and f.shipment_id = t.shipment_id and f.is_delivered)
), target_rejected as (
    -- The lowest raw identity among today's rejected items of excluded shipments.
    select min(c.legacy_row_id) as legacy_row_id
    from trusted.legacy_classifications c
    where c.source_table = 'shipment_items' and c.classification = 'rejected'
      and (c.cleaned_payload->>'shipment_id')::bigint in (select shipment_id from excluded_today)
),
-- ── The relations, per scenario ─────────────────────────────────────────────
fact as (
    select k.name, f.source_system, f.shipment_id, f.shipment_item_id, f.is_delivered
    from cases k cross join analytics.fact_shipment_item f
    where not (k.name in ('fact_missing', 'sibling') and f.source_system = 'legacy'
               and f.shipment_id = (select shipment_id from target_shipment))
), titems as (
    select k.name, i.source_system, i.shipment_id, i.shipment_item_id
    from cases k cross join trusted.shipment_items i
    where not (k.name = 'sibling' and i.source_system = 'legacy'
               and i.shipment_item_id = (select shipment_item_id from target_item))
), quar as (
    select k.name, q.source_system, q.snapshot_id, q.source_table, q.legacy_row_id,
           q.catalog_version, q.treatment_fingerprint, q.classification, q.rejection_origin, q.findings
    from cases k cross join quarantine.rejected_legacy_records q
    where not (k.name = 'stale_treatment' and q.source_table = 'shipment_items'
               and q.legacy_row_id = (select legacy_row_id from target_rejected)
               and q.snapshot_id = (select snapshot_id from sel))
    union all
    -- The older treatment: catalogue 8, its fingerprint, another origin, no findings.
    select 'stale_treatment', q.source_system, q.snapshot_id, q.source_table, q.legacy_row_id,
           8, '8710ca3fbdcfce5b', q.classification, 'own_invalid', '[]'::jsonb
    from quarantine.rejected_legacy_records q
    where q.source_table = 'shipment_items'
      and q.legacy_row_id = (select legacy_row_id from target_rejected)
      and q.snapshot_id = (select snapshot_id from sel)
), tship as (
    select k.name, t.shipment_id
    from cases k cross join trusted.shipments t
    where t.source_system = 'legacy' and t.is_delivered and not t.is_deleted
), excluded as (
    select t.name, t.shipment_id from tship t
    where not exists (select 1 from fact f
                       where f.name = t.name and f.source_system = 'legacy'
                         and f.shipment_id = t.shipment_id and f.is_delivered)
),
-- ── q7's predicate, section 4, verbatim but for the scenario key ────────────
q7_raw as (
    select e.name, r.legacy_row_id, r.shipment_id::bigint as shipment_id
    from raw_legacy.shipment_items r, sel, excluded e
    where r._airbyte_meta->>'sync_id' = sel.snapshot_id::text
      and r.shipment_id::bigint = e.shipment_id
), q7_items as (
    select ri.name, ri.legacy_row_id, c.classification,
           exists (select 1 from quar q, sel
                   where q.name = ri.name and q.snapshot_id = sel.snapshot_id
                     and q.source_table = 'shipment_items' and q.legacy_row_id = ri.legacy_row_id) as in_quarantine,
           exists (select 1 from titems i
                   where i.name = ri.name and i.source_system = 'legacy'
                     and i.shipment_id = ri.shipment_id) as shipment_has_trusted_item
    from q7_raw ri
    left join trusted.legacy_classifications c
      on c.snapshot_id = (select snapshot_id from sel) and c.source_table = 'shipment_items'
     and c.legacy_row_id = ri.legacy_row_id
), q7 as (
    select k.name,
           count(i.legacy_row_id) filter (
               where i.classification is null
                  or (i.classification = 'rejected' and not i.in_quarantine)
                  or (i.classification in ('accepted', 'corrected') and not i.shipment_has_trusted_item)
           ) as q7_unaccounted_items
    from cases k left join q7_items i on i.name = k.name
    group by k.name
),
-- ── q11's predicate, section 4, verbatim but for the scenario key ───────────
cur as (
    select distinct source_system, snapshot_id, catalog_version, treatment_fingerprint
    from trusted.legacy_classifications
), cls as (
    select c.*
    from trusted.legacy_classifications c
    join cur using (source_system, snapshot_id, catalog_version, treatment_fingerprint)
    join sel using (snapshot_id)
    where c.source_system = 'legacy' and c.source_table = 'shipment_items'
), q11_items as (
    select t.name, c.legacy_row_id, t.shipment_id, c.classification,
           exists (select 1 from excluded e where e.name = t.name and e.shipment_id = t.shipment_id) as in_excluded_shipment,
           c.classification in ('accepted', 'corrected')
               and exists (select 1 from titems i
                            where i.name = t.name and i.source_system = 'legacy'
                              and i.shipment_item_id = (c.cleaned_payload->>'id')::bigint
                              and i.shipment_id = t.shipment_id) as own_trusted_item,
           c.classification in ('accepted', 'corrected')
               and exists (select 1 from fact f
                            where f.name = t.name and f.source_system = 'legacy'
                              and f.shipment_item_id = (c.cleaned_payload->>'id')::bigint
                              and f.shipment_id = t.shipment_id) as own_fact_item,
           c.classification = 'rejected'
               and exists (select 1 from quar q
                            where q.name = t.name
                              and q.source_system = c.source_system and q.snapshot_id = c.snapshot_id
                              and q.source_table = c.source_table and q.legacy_row_id = c.legacy_row_id
                              and q.catalog_version = c.catalog_version
                              and q.treatment_fingerprint = c.treatment_fingerprint
                              and q.classification = c.classification
                              and q.rejection_origin is not distinct from c.rejection_origin
                              and q.findings = c.findings) as in_current_quarantine
    from cls c
    join tship t on pg_input_is_valid(c.cleaned_payload->>'shipment_id', 'bigint')
                and t.shipment_id = (c.cleaned_payload->>'shipment_id')::bigint
), q11 as (
    select k.name,
           count(*) filter (where i.classification in ('accepted', 'corrected') and not i.own_trusted_item) as eligible_trusted_missing,
           count(*) filter (where i.classification in ('accepted', 'corrected') and not i.own_fact_item) as eligible_fact_missing,
           count(*) filter (where i.classification = 'rejected' and not i.in_current_quarantine) as rejected_quarantine_stale,
           count(*) filter (where i.in_excluded_shipment and i.classification <> 'rejected') as unexplained_exclusion_items
    from cases k left join q11_items i on i.name = k.name
    group by k.name
)
select q7.name as scenario,
       (select count(*) from excluded e where e.name = q7.name) as excluded_shipments,
       q7.q7_unaccounted_items,
       q11.eligible_trusted_missing, q11.eligible_fact_missing,
       q11.rejected_quarantine_stale, q11.unexplained_exclusion_items
from q7 join q11 using (name)
order by array_position(array['today', 'fact_missing', 'sibling', 'stale_treatment'], q7.name);
