"""M60 — the metadata package at v2.3.0 against the one at v2.1.0.

Reads the package at `2bceb47` (tag v2.3.0) and at `eb11709` (tag v2.1.0), as
`git show <commit>:docs/pacote_de_metadados.json` writes them, and checks what
the notices of 2026-11-18 and 2026-11-19 say changed: format, relations, keys
and foreign keys, the view audits and the run of their checks, the open items
and the provenance. Files only.

Usage: python -I package_check.py <package at 2bceb47> <package at eb11709>
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

ro, rn = old["relations"], new["relations"]
layer = lambda rels: collections.Counter(n.split(".")[0] for n in rels)  # noqa: E731
print(f"relations: {len(ro)} -> {len(rn)}; added {sorted(set(rn) - set(ro))}; removed {sorted(set(ro) - set(rn))}")
print(f"analytics: {layer(ro)['analytics']} -> {layer(rn)['analytics']}; "
      f"consumption: {layer(ro)['consumption']} -> {layer(rn)['consumption']}")
keys = lambda rels: set().union(*(set(v) for v in rels.values()))  # noqa: E731
print(f"relation keys added: {sorted(keys(rn) - keys(ro))}")
an = {n: v for n, v in rn.items() if n.startswith("analytics.")}
print(f"analytics primary keys: {sum(1 for v in an.values() if v.get('primary_key'))}; "
      f"foreign keys: {sum(len(v.get('foreign_keys') or []) for v in an.values())}")
changed = [n for n in rn if n.startswith("consumption.") and list(rn[n]["columns"]) != list(ro[n]["columns"])]
print(f"consumption relations whose columns changed: {changed}")
print("dim_sku_location: primary_key "
      f"{rn['analytics.dim_sku_location'].get('primary_key')}; foreign_keys "
      f"{json.dumps(rn['analytics.dim_sku_location'].get('foreign_keys'), sort_keys=True)}")

va = new["view_audits"]
print(f"view_audits: {len(va)}; status x commit: "
      f"{dict(collections.Counter((v['status'], v['commit']) for v in va.values()))}")
ids = [i for v in va.values() for i in v.get("checks") or []]
dts = [i for v in va.values() for i in v.get("data_tests") or []]
results = [new["checks"][i]["result"] for i in ids]
print(f"view_audits checks: {len(ids)}, results {dict(collections.Counter(r['status'] for r in results))}, "
      f"executed_at {sorted({r['executed_at'] for r in results})}")
print(f"view_audits data_tests: {len(dts)}: {dts}")
p12 = va["consumption.skus_below_reorder_point"]
print(f"P12 audit: status {p12['status']}, commit {p12['commit']}, reference {p12['reference']}")
print(f"open_items: {sorted(i['id'] for i in old['open_items'])} -> "
      f"{sorted((i['id'], i['state']) for i in new['open_items'])}")
print(f"provenance.dbt.manifest_invocation_id: {new['provenance']['dbt']['manifest_invocation_id']}")
print(f"provenance.warehouse: {json.dumps(new['provenance']['warehouse'], sort_keys=True)}")
