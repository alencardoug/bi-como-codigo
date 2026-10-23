-- RR-06: what a content baseline of the retained legacy memory has to cover.
-- Read-only (ro.sh): the retained captures in raw_legacy, by the job that wrote
-- them, and the certificate rows in governance.legacy_captures.
show default_transaction_read_only;

select pg_size_pretty(sum(pg_total_relation_size(c.oid))) as raw_legacy_size,
       count(*) as tables
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'raw_legacy' and c.relkind = 'r';

-- One table stands for all 40: every capture writes all of them.
select count(distinct _airbyte_meta->>'sync_id') as retained_captures,
       count(*) filter (where _airbyte_generation_id < 0) as rows_rebased,
       count(*) filter (where _airbyte_generation_id >= 0) as rows_not_rebased
from raw_legacy.shipments;

select status, count(distinct snapshot_id) as captures, count(*) as certificate_rows
from governance.legacy_captures
group by 1 order by 1;

-- Retained captures with no complete certificate: the uncertified attempts.
select count(*) as retained_without_complete_certificate
from (select distinct (_airbyte_meta->>'sync_id')::bigint as sync_id from raw_legacy.shipments) r
where r.sync_id not in (
    select snapshot_id from governance.legacy_captures
    where status = 'complete' and snapshot_id is not null
    group by snapshot_id having count(distinct source_table) = 40
);
