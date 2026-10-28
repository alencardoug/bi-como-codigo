#!/usr/bin/env bash
# The project's containers as Docker reports them: name, state, restart policy
# and start time. Reads `docker inspect` only; starts, stops and changes nothing.
set -euo pipefail
date -u +%Y-%m-%dT%H:%M:%SZ
docker ps -a --filter name=mvp_ed1 --format '{{.Names}}' | sort | while read -r c; do
  docker inspect -f '{{.Name}} state={{.State.Status}} restart={{.HostConfig.RestartPolicy.Name}} started={{.State.StartedAt}}' "$c"
done
# Whether the warehouse saw a capture after M30 (2026-10-23): the certificate
# rows, their attempts, the newest attempt and the selected capture, read-only.
"$(dirname "$0")/../20261022/ro.sh" <<'SQL'
show default_transaction_read_only;
select count(*) as certificate_rows, count(distinct capture_attempt_id) as attempts,
       max(started_at) as newest_attempt, max(snapshot_id) filter (where status = 'complete') as newest_complete,
       (select snapshot_id from staging.legacy_selected_capture) as selected
from governance.legacy_captures;
SQL
