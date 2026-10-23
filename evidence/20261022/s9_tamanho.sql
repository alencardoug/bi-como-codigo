-- S9: quanto o armazém ocupa, por schema, e quantas linhas tem o produto analítico.
select pg_size_pretty(pg_database_size(current_database())) as banco_inteiro;
select n.nspname as schema,
       count(*) filter (where c.relkind in ('r', 'p')) as tabelas,
       count(*) filter (where c.relkind = 'v') as views,
       count(*) filter (where c.relkind = 'm') as views_materializadas,
       pg_size_pretty(sum(pg_total_relation_size(c.oid)) filter (where c.relkind in ('r', 'p', 'm'))) as tamanho
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname in ('raw', 'raw_legacy', 'staging', 'trusted', 'analytics', 'consumption',
                    'quarantine', 'snapshots', 'governance')
  and c.relkind in ('r', 'p', 'v', 'm')
group by 1 order by sum(pg_total_relation_size(c.oid)) filter (where c.relkind in ('r', 'p', 'm')) desc nulls last;
-- linhas das tabelas do analytics (estatística exata por count)
select 'analytics' as camada, table_name, (xpath('/row/n/text()',
       query_to_xml(format('select count(*) as n from analytics.%I', table_name), false, true, '')))[1]::text::bigint as linhas
from information_schema.tables where table_schema = 'analytics' and table_type = 'BASE TABLE'
union all
select 'consumption', table_name, (xpath('/row/n/text()',
       query_to_xml(format('select count(*) as n from consumption.%I', table_name), false, true, '')))[1]::text::bigint
from information_schema.views where table_schema = 'consumption'
order by 1, 3 desc;
