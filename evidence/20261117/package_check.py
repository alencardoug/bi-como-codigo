"""M57 — the metadata package at the new pin against the last one announced.

Reads the package at `eb11709` (tag v2.1.0) and at `19c0e80` (the pin of the
notice of 2026-11-15), as `git show <commit>:docs/pacote_de_metadados.json`
writes them, and checks what the notice of 2026-11-17 says changed. Files only.

Usage: python -I package_check.py <package at eb11709> <package at 19c0e80>
"""

import collections
import datetime
import json
import sys

new, old = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:3])
print("# package_check.py — "
      + datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
      + " — files only, no database")
print(f"format: {old['format']} -> {new['format']}")
print(f"top-level keys added: {sorted(set(new) - set(old))}; removed: {sorted(set(old) - set(new))}")
m = new["metrics"]
print(f"metrics: {len(m)}; on_zero_denominator: "
      f"{dict(collections.Counter(str(v.get('on_zero_denominator')) for v in m.values()))}; "
      f"zero_denominator kept: {dict(collections.Counter(str(v.get('zero_denominator')) for v in m.values()))}")
ids = lambda p: sorted(i["id"] for i in p["open_items"])  # noqa: E731
print(f"open_items: {ids(old)} -> {ids(new)}")
print(f"provenance.warehouse: {json.dumps(new['provenance']['warehouse'], sort_keys=True)}")
print(f"provenance.dbt.manifest_invocation_id: {new['provenance']['dbt']['manifest_invocation_id']}")
gw = new["relations"]["analytics.fact_payment_transaction"]["columns"]["gateway_response_code"]["meta"]
print(f"gateway_response_code values: {json.dumps(gw.get('values'), ensure_ascii=False, sort_keys=True)}")
va = new["view_audits"]
print(f"view_audits: {len(va)}; status {dict(collections.Counter(v['status'] for v in va.values()))}; "
      f"commit {dict(collections.Counter(v['commit'] for v in va.values()))}")
audit = {k: v for k, v in new["checks"].items() if k.startswith("tests/test_auditoria_das_views.py::")}
print(f"checks of tests/test_auditoria_das_views.py: {len(audit)}; "
      f"status {dict(collections.Counter((v['result'] or {}).get('status') for v in audit.values()))}; "
      f"executed {sorted({(v['result'] or {}).get('executed_at') for v in audit.values()})}")
