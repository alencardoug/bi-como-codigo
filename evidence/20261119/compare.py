"""M59 — the 16 views at v2.3.0 against M55, the capture at v2.1.0.

Reads two outputs of `evidence/20261117/capture.sh` — the sections that enter
Git, not the rows — and the rows of P08, P11 and P12 at v2.3.0, which stay
outside Git. Prints, per view, whether the row count and the fingerprint
are the same; whether any view's columns or types changed; and, for P12, the
distribution of `reorder_point` and of `quantity_available` in the new rows;
for P08 and P11, the sums and the turnover `mvp_eng_dados_2`'s Consumidores §5
publishes for them on 2026-11-18. Files only, no database.

Usage: python -I compare.py <capture.out.txt at v2.1.0> <capture.out.txt at v2.3.0> <CAPTURE_DIR at v2.3.0>
"""

import collections
import csv
import datetime
import io
import pathlib
import sys

print("# compare.py — "
      + datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
      + " — files only, no database")


def sections(path):
    out, name = {}, None
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            out[name] = []
        elif name is not None and line:
            out[name].append(line)
    return out


def table(lines):
    return list(csv.DictReader(io.StringIO("\n".join(lines))))


before, after = sections(sys.argv[1]), sections(sys.argv[2])
capture_dir = pathlib.Path(sys.argv[3])

print("\n## provenance")
for label, s in (("v2.1.0", before), ("v2.3.0", after)):
    p = table(s["provenance"])[0]
    print(f"{label}: {p['status']}, invocation {p['invocation_id']}, from {p['built_from_commit'][:7]}, at {p['built_at']}")

print("\n## fingerprints: v2.1.0 -> v2.3.0")
fb = {r["view_name"]: r for r in table(before["fingerprints"])}
fa = {r["view_name"]: r for r in table(after["fingerprints"])}
assert set(fb) == set(fa) and len(fa) == 16, (sorted(fb), sorted(fa))
same = 0
for v in sorted(fa):
    b, a = fb[v], fa[v]
    if b["rows_md5"] == a["rows_md5"]:
        same += 1
        print(f"same     {v}: {a['row_count']} rows")
    else:
        print(f"CHANGED  {v}: {b['row_count']} -> {a['row_count']} rows")
print(f"{same} of 16 identical, {16 - same} changed")

print("\n## columns: v2.1.0 -> v2.3.0")
cb, ca = before["columns"], after["columns"]
print("identical: every view's columns, order and types" if cb == ca else "DIFFERENT")
if cb != ca:
    for line in sorted(set(cb) ^ set(ca)):
        print(("only v2.1.0 " if line in cb else "only v2.3.0 ") + line)

print("\n## P12 at v2.3.0: reorder_point x quantity_available")
rows = list(csv.DictReader((capture_dir / "skus_below_reorder_point.csv").open(encoding="utf-8")))
pairs = collections.Counter((r["reorder_point"], r["quantity_available"]) for r in rows)
for (point, available), n in sorted(pairs.items()):
    print(f"reorder_point {point}, quantity_available {available}: {n} rows")
print(f"is_stockout: {dict(collections.Counter(r['is_stockout'] for r in rows))}")

print("\n## P08 at v2.3.0: sums, and months after the last realised order")
rows = list(csv.DictReader((capture_dir / "gross_margin_by_category.csv").open(encoding="utf-8")))
total = {k: sum(float(r[k] or 0) for r in rows) for k in
         ("net_revenue_amount", "cost_of_goods_sold", "gross_profit_amount", "dispatched_unit_count")}
for k, v in total.items():
    print(f"{k}: {v:,.2f}")
print(f"last year_month: {max(r['year_month'] for r in rows)}")

print("\n## P11 at v2.3.0: quarterly turnover")
rows = list(csv.DictReader((capture_dir / "inventory_turnover_by_sku_and_warehouse.csv").open(encoding="utf-8")))
turn = sorted(float(r["inventory_turnover"]) for r in rows if r["inventory_turnover"])
median = (turn[(len(turn) - 1) // 2] + turn[len(turn) // 2]) / 2
print(f"rows {len(rows)}, defined {len(turn)}, undefined {len(rows) - len(turn)}")
print(f"median {median:.2f}, p90 {turn[int(0.9 * (len(turn) - 1))]:.2f}")
print(f"last year_quarter: {max(r['year_quarter'] for r in rows)}")
