-- Stage 1.7: does the text reach the database? persist_docs writes each dbt
-- description as the column's comment; count, per layer, the columns that
-- exist and the ones with a comment. Read-only (ro.sh).
show default_transaction_read_only;
select now();

select n.nspname                                                     as layer,
       count(*)                                                      as columns,
       count(*) filter (where col_description(c.oid, a.attnum) is not null) as with_comment
from pg_attribute a
join pg_class c on c.oid = a.attrelid and c.relkind in ('r', 'v', 'm', 'p')
join pg_namespace n on n.oid = c.relnamespace
where n.nspname in ('raw', 'raw_legacy', 'staging', 'trusted', 'analytics', 'consumption', 'quarantine', 'snapshots', 'governance')
  and a.attnum > 0 and not a.attisdropped
  and c.relname not like '%\_\_dbt\_%'
group by 1 order by 1;

-- A sample: P01's columns as whoever opens the database sees them.
select a.attname as column, left(col_description(c.oid, a.attnum), 70) as comment
from pg_attribute a
join pg_class c on c.oid = a.attrelid
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'consumption' and c.relname = 'monthly_revenue_by_channel_and_category'
  and a.attnum > 0 and not a.attisdropped
order by a.attnum;
