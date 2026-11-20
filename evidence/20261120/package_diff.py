"""M61 — the metadata package at `b0ef66e` against `v2.3.0` (`2bceb47`).

Reads the two packages as `git show <commit>:docs/pacote_de_metadados.json`
writes them and walks them key by key: it prints every difference outside
`checks`, and for `checks` only a summary — ids added or removed, results whose
status changed, and the dates of the runs. Files only.

Usage: python -I package_diff.py <package at 2bceb47> <package at b0ef66e>
"""

import collections
import datetime
import json
import sys

old, new = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:3])
print("# package_diff.py — "
      + datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
      + " — files only, no database")


def walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}.{k}: only in {'b0ef66e' if k in b else '2bceb47'}")
            else:
                walk(a[k], b[k], f"{path}.{k}", out)
    elif a != b:
        out.append(f"{path}: {json.dumps(a, ensure_ascii=False)[:160]} -> {json.dumps(b, ensure_ascii=False)[:160]}")


diffs = []
for top in sorted(set(old) | set(new)):
    if top != "checks":
        walk(old.get(top), new.get(top), top, diffs)
sections = collections.Counter(d.split(".")[0].split(":")[0] for d in diffs)
print(f"## top-level sections that differ, outside checks: {dict(sections)}")
for d in diffs:
    if not d.startswith("open_items"):
        print(d)
ids = lambda p: [(i["id"], i["state"]) for i in p["open_items"]]  # noqa: E731
print(f"open_items: {ids(old)} -> {ids(new)}")

co, cn = old["checks"], new["checks"]
status = lambda c: (c.get("result") or {}).get("status")  # noqa: E731
print("\n## checks")
print(f"ids: {len(co)} -> {len(cn)}; added {sorted(set(cn) - set(co))}; removed {sorted(set(co) - set(cn))}")
changed = [i for i in set(co) & set(cn) if status(co[i]) != status(cn[i])]
print(f"status changed: {sorted(changed)}")
print(f"status at b0ef66e: {dict(collections.Counter(status(c) for c in cn.values()))}")
runs = lambda cs: sorted({(c.get('result') or {}).get('executed_at') for c in cs.values() if c.get('result')})  # noqa: E731
print(f"runs: {runs(co)} -> {runs(cn)}")
