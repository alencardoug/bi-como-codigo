#!/usr/bin/env bash
# RR-24: what Airbyte's persisted job records give for the legacy connection,
# read through eng_dados' own client (`airbyte.jobs`, a GET of the listing),
# and how they reconcile with the job ids the warehouse holds — certificate
# attempts and raw `sync_id`s. Read-only: the API is only listed (the token
# request creates no job and changes no data), and the warehouse is read through
# ro.sh. The credentials come from `abctl local credentials` as the Makefile's
# CREDENCIAIS takes them, into the environment only; nothing prints them.
# Needs ENG_DADOS_DIR, the Airbyte cluster up and the eng_dados `.venv`.
set -uo pipefail
here="$(dirname "$(realpath "$0")")"
cd "$ENG_DADOS_DIR"
eval "$(.tools/abctl local credentials 2>/dev/null \
    | sed 's/\x1b\[[0-9;]*m//g' \
    | sed -n 's/.*Client-Id: \(\S*\).*/AIRBYTE_CLIENT_ID=\1/p; s/.*Client-Secret: \(\S*\).*/AIRBYTE_CLIENT_SECRET=\1/p' \
    | sed 's/^/export /')"

echo "== 1. The listing, through airbyte.jobs: fields and the legacy connection's jobs"
PYTHONPATH=src .venv/bin/python - <<'PY'
from mvp_ed1 import airbyte
jwt = airbyte.token()
legada = airbyte.conexao("legacy_para_raw_legacy", jwt)
dados = airbyte.jobs(jwt, 100).get("data", [])
print("listed", len(dados), "| fields", sorted(dados[0]) if dados else None)
print("oldest listed", min((d.get("startTime") for d in dados), default=None))
do_legado = [d for d in dados if d.get("connectionId") == legada]
print("legacy connection jobs listed", len(do_legado))
for d in sorted(do_legado, key=lambda d: int(d["jobId"])):
    print(" ", d["jobId"], d.get("jobType"), d.get("status"), d.get("startTime"), d.get("rowsSynced"))
PY
echo "[exit $?]"

echo "== 2. The warehouse: job ids of certificate attempts and raw sync_ids"
"$here/../20261022/ro.sh" <<'SQL'
show default_transaction_read_only;
select count(distinct capture_attempt_id) as attempts,
       count(distinct capture_attempt_id) filter (where job_id is null) as attempts_without_job,
       string_agg(distinct job_id::text, ',' order by job_id::text) as certificate_job_ids
from governance.legacy_captures;
select string_agg(distinct j, ',' order by j) as raw_sync_ids
from (select _airbyte_meta->>'sync_id' as j from raw_legacy.shipments
      union select _airbyte_meta->>'sync_id' from raw_legacy.orders) s;
SQL
echo "[exit $?]"
