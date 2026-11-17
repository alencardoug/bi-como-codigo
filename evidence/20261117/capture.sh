#!/usr/bin/env bash
# M55 — capture of the 16 views of `consumption` at eng_dados v2.1.0, in one
# REPEATABLE READ READ ONLY transaction, through the exporter's own login
# (consumption_reader, a member of analyst only).
#
# Prints to standard output what may enter Git: the warehouse provenance, each
# view's columns and types, its row count and a fingerprint (md5 of its rows as
# text, in text order). The rows themselves go to CAPTURE_DIR, one CSV per view,
# outside Git: no clear report data is committed (PLAN §6.2, stage 2.4).
#
# Usage: ENG_DADOS_DIR=<checkout of mvp_eng_dados_2> CAPTURE_DIR=<dir outside Git> capture.sh
# Nothing is fixed here: the login and database come from that checkout's .env,
# read without printing them.
set -euo pipefail
: "${ENG_DADOS_DIR:?set ENG_DADOS_DIR to a checkout of mvp_eng_dados_2}"
: "${CAPTURE_DIR:?set CAPTURE_DIR to a directory outside Git}"
here="$(cd "$(dirname "$0")" && pwd)"
env_file="$ENG_DADOS_DIR/.env"
val() { grep "^$1=" "$env_file" | cut -d= -f2-; }
user="$(val WAREHOUSE_READER_USER)"
db="$(val WAREHOUSE_DB_NAME)"
PGPASSWORD="$(val WAREHOUSE_READER_PASSWORD)"
export PGPASSWORD

psql_ro() {
  docker exec -i -e PGPASSWORD -e PGAPPNAME=bi_capture_m55 \
    -e PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=300s' \
    mvp_ed1_warehouse_db \
    psql -X -q -v ON_ERROR_STOP=1 -h 127.0.0.1 -U "$user" -d "$db" -P pager=off "$@"
}

# The view names, read first; the transaction below asserts there are 16.
mapfile -t views < <(psql_ro -At -c \
  "select table_name from information_schema.views where table_schema = 'consumption' order by 1")

{
  echo "begin isolation level repeatable read read only;"
  echo "\\echo '### transaction'"
  echo "copy (select now() as read_at, current_user as login,
                 current_setting('transaction_isolation') as isolation,
                 current_setting('transaction_read_only') as read_only,
                 (select count(*) from information_schema.views
                   where table_schema = 'consumption') as consumption_views)
        to stdout with (format csv, header);"
  echo "\\echo '### provenance'"
  echo "copy (select * from governance.warehouse_provenance) to stdout with (format csv, header);"
  echo "\\echo '### columns'"
  echo "copy (select table_name, ordinal_position, column_name, data_type,
                 numeric_precision, numeric_scale
            from information_schema.columns where table_schema = 'consumption'
           order by table_name, ordinal_position)
        to stdout with (format csv, header);"
  echo "\\echo '### fingerprints'"
  sep=""
  echo "copy ("
  for v in "${views[@]}"; do
    echo "$sep select '$v' as view_name, count(*) as row_count,
             md5(coalesce(string_agg(t::text, E'\\n' order by t::text), '')) as rows_md5
        from consumption.$v t"
    sep="union all"
  done
  echo "order by 1) to stdout with (format csv, header);"
  for v in "${views[@]}"; do
    echo "\\echo '### rows $v'"
    echo "copy (select t.* from consumption.$v t order by t::text) to stdout with (format csv, header);"
  done
  echo "commit;"
} | psql_ro | python3 -I "$here/capture_split.py" "$CAPTURE_DIR"
