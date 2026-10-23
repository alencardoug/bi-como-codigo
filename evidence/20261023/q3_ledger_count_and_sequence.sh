#!/usr/bin/env bash
# RR-11: the stock ledger's row count and max(event_sequence), in the source and
# in both warehouse paths — read-only sessions; no credential printed.
# Uses ENG_DADOS_DIR (default ~/Projetos/mvp_eng_dados_1).
set -euo pipefail
cd "${ENG_DADOS_DIR:-$HOME/Projetos/mvp_eng_dados_1}"
env_of() { grep "^$1=" .env | cut -d= -f2; }
ro='-c default_transaction_read_only=on -c statement_timeout=120s'
echo "== source_db, oltp.inventory_movements"
docker exec -i -e PGOPTIONS="$ro" -e PGAPPNAME=sonda_revisao mvp_ed1_source_db \
  psql -X -v ON_ERROR_STOP=1 -U "$(env_of SOURCE_DB_USER)" -d "$(env_of SOURCE_DB_NAME)" -P pager=off <<'SQL'
show default_transaction_read_only;
select count(*) as rows, max(event_sequence) as max_seq,
       max(event_sequence) - count(*) as gap
from oltp.inventory_movements;
SQL
echo "== warehouse_db, the two paths"
docker exec -i -e PGOPTIONS="$ro" -e PGAPPNAME=sonda_revisao mvp_ed1_warehouse_db \
  psql -X -v ON_ERROR_STOP=1 -U "$(env_of WAREHOUSE_DB_USER)" -d "$(env_of WAREHOUSE_DB_NAME)" -P pager=off <<'SQL'
show default_transaction_read_only;
select 'raw.inventory_movements' as path, count(*) as rows, max(event_sequence) as max_seq from raw.inventory_movements
union all
select 'raw.inventory_movements_stream', count(*), max(event_sequence) from raw.inventory_movements_stream;
SQL
