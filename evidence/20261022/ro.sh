#!/usr/bin/env bash
# Consulta somente leitura no armazém do eng_dados: sessão read-only, sem imprimir credencial.
# Uso: ro.sh <arquivo.sql>   (ou SQL pela entrada padrão)
# O checkout do eng_dados vem de ENG_DADOS_DIR (padrão: ~/Projetos/mvp_eng_dados_1).
set -euo pipefail
sql="${1:-/dev/stdin}"
[ "$sql" = /dev/stdin ] || sql="$(realpath "$sql")"
cd "${ENG_DADOS_DIR:-$HOME/Projetos/mvp_eng_dados_1}"
u=$(grep '^WAREHOUSE_DB_USER=' .env | cut -d= -f2)
d=$(grep '^WAREHOUSE_DB_NAME=' .env | cut -d= -f2)
docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=120s' \
  -e PGAPPNAME=sonda_revisao mvp_ed1_warehouse_db \
  psql -X -v ON_ERROR_STOP=1 -U "$u" -d "$d" -P pager=off "${@:2}" < "$sql"
