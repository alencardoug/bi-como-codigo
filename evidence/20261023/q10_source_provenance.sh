#!/usr/bin/env bash
# The provenance of today's source_db: what records its generation, and whether
# its size is that of a recorded load plus the producer. Reads files and opens a
# read-only session; writes nothing. Uses ENG_DADOS_DIR (default ~/Projetos/mvp_eng_dados_1).
set -euo pipefail
cd "${ENG_DADOS_DIR:-$HOME/Projetos/mvp_eng_dados_1}"
env_of() { grep "^$1=" .env | cut -d= -f2; }
echo "== data/source"; ls -1 data/source
echo "== the record set aside by B5's restore"; cat data/source/geracao.json.anterior-a-restauracao-*
echo "== the approved package's manifest: corte, max_event_sequence, geracao.source_db"
.venv/bin/python -I -c '
import json
m = json.load(open("data/recovery/aprovado/manifesto.json"))
print("corte", m["corte"]); print("max_event_sequence", m["max_event_sequence"])
print("geracao.source_db", m["geracao"]["source_db"]); print("motivo", m["geracao"].get("source_db_motivo"))
print("oltp rows in the manifest", sum(m["contagens"]["source_db"].values()))'
echo "== the cursor"; cat .stream/producer_state.json
echo "== source_db today"
docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=120s' \
  -e PGAPPNAME=sonda_revisao mvp_ed1_source_db \
  psql -X -v ON_ERROR_STOP=1 -U "$(env_of SOURCE_DB_USER)" -d "$(env_of SOURCE_DB_NAME)" -P pager=off <<'SQL'
show default_transaction_read_only;
select sum((xpath('/row/n/text()',
           query_to_xml(format('select count(*) as n from oltp.%I', table_name), false, true, '')))[1]::text::bigint)
       as oltp_rows
from information_schema.tables where table_schema = 'oltp' and table_type = 'BASE TABLE';
SQL
echo "== source_db today against the cut's manifest, table by table (only the differences)"
set -a; . ./.env; set +a
.venv/bin/python -I -c '
import json
import sqlalchemy as sa
from mvp_ed1.db import SOURCE, database_url
m = json.load(open("data/recovery/aprovado/manifesto.json"))["contagens"]["source_db"]
e = sa.create_engine(database_url(SOURCE))
with e.connect() as c:
    c.execute(sa.text("set transaction read only"))
    for chave, antes in sorted(m.items()):
        agora = c.execute(sa.text(f"select count(*) from {chave}")).scalar_one()
        if agora != antes:
            print(f"{chave}: {antes} -> {agora} ({agora - antes:+d})")
print("tables in the manifest", len(m))'
