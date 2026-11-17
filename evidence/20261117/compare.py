"""M56 — the views at v2.1.0 against every "before" that survives.

This repository never captured the views at the old pin, `4da9e60`, and the
shared warehouse no longer holds that state. What survives of it is what
mvp_eng_dados_2 measured on 2026-11-14 in its Bloco 1 and 1b, outside its Git:
the rows of four views right after their last change before `4da9e60`, and
the counts its Consumidores §5 publishes. This script sets the capture of M55
against those, by the grain the package declares for each view
(`view_rules.*.columns.*.role == "grain"` at `eb11709`).

It prints counts only — rows, keys gained and lost, cells changed per column,
the additive totals that eng_dados' §5 already publishes —, never a row.

Usage: python -I compare.py <ENG_DADOS_DIR> <CAPTURE_DIR> <package eb11709.json>
"""

import csv
import datetime
import json
import pathlib
import statistics
import sys
from decimal import Decimal

eng, capture, package = (pathlib.Path(a) for a in sys.argv[1:4])
measured = eng / "data/medicoes/base_consumidores"
print("# compare.py — "
      + datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
      + " — files only, no database")
rules = json.loads(package.read_text(encoding="utf-8"))["view_rules"]

# view -> (before file, what that file is, the additive columns whose totals §5 publishes)
BEFORE = {
    "support_tickets_per_hundred_orders": (
        "bloco1/f1_depois.csv",
        "after F1 (9aeea8d), before F21 (0471f6a) — not exactly the state at 4da9e60",
        ["ticket_count"],
    ),
    "on_time_delivery_rate_by_carrier": (
        "bloco1/p13_depois.csv",
        "after D66 (745fe6a), the last change before 4da9e60",
        ["delivered_count", "on_time_count", "late_count"],
    ),
    "new_and_repeat_customers_by_month": (
        "bloco1b/new_and_repeat_customers_by_month_depois.csv",
        "after F18 (12677a3), the last change before 4da9e60",
        ["new_customer_count"],
    ),
    "order_to_delivery_time_by_region": (
        "bloco1b/order_to_delivery_time_by_region_depois.csv",
        "after F17 (12677a3), the last change before 4da9e60",
        ["order_count", "shipment_count"],
    ),
}


def read(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def number(text):
    return Decimal(text) if text not in ("", None) else None


for view, (before_file, what, totals) in BEFORE.items():
    grain = sorted(c for c, d in rules[f"consumption.{view}"]["columns"].items() if d["role"] == "grain")
    before = read(measured / before_file)
    after = read(capture / f"{view}.csv")
    key = lambda r: tuple(r[c] for c in grain)  # noqa: E731
    b = {key(r): r for r in before}
    a = {key(r): r for r in after}
    assert len(b) == len(before) and len(a) == len(after), f"{view}: grain is not a key"
    common = b.keys() & a.keys()
    measures = [c for c in after[0] if c not in grain]
    changed_rows = sum(1 for k in common if any(number(b[k][c]) != number(a[k][c]) for c in measures))
    print(f"\n## {view}\nbefore: {before_file} — {what}")
    print(f"rows: {len(before)} -> {len(after)}; keys only before: {len(b.keys() - a.keys())}; "
          f"only after: {len(a.keys() - b.keys())}; common: {len(common)}, "
          f"of which with a changed value: {changed_rows}")
    for c in measures:
        n = sum(1 for k in common if number(b[k][c]) != number(a[k][c]))
        print(f"  {c}: {n} of {len(common)} common rows changed")
    for c in totals:
        tb = sum(number(r[c]) or 0 for r in before)
        ta = sum(number(r[c]) or 0 for r in after)
        print(f"  total {c}: {tb} -> {ta}")

# The counts §5 publishes for views with no "before" rows here.
print("\n## inventory_turnover_by_sku_and_warehouse (P11)")
p11 = read(capture / "inventory_turnover_by_sku_and_warehouse.csv")
undefined = sum(1 for r in p11 if r["inventory_turnover"] == "")
print(f"rows: 6990 (Consumidores §5, 14/11) -> {len(p11)}; undefined turnover: 1216 -> {undefined}")
turnover = sorted(Decimal(r["inventory_turnover"]) for r in p11 if r["inventory_turnover"] != "")
print(f"median turnover per quarter, defined rows: {statistics.median(turnover)}")

print("\n## support_tickets_per_hundred_orders (P15), the F1 case")
p15 = read(capture / "support_tickets_per_hundred_orders.csv")
case = [r for r in p15 if (r["year_month"], r["sales_channel_name"], r["support_category_name"])
        == ("2024-01", "Aplicativo", "Conta")]
print("Jan/2024, Aplicativo, Conta: 4.3478 (23 orders, after F1) -> "
      + (f"{case[0]['tickets_per_hundred_orders']} ({case[0]['channel_order_count']} orders)"
         if case else "no row"))

# The schema: each captured view's columns, in order, against the package's relation at eb11709.
print("\n## schema: captured header against the package's relations at eb11709")
relations = json.loads(package.read_text(encoding="utf-8"))["relations"]
for path in sorted(capture.glob("*.csv")):
    with path.open(encoding="utf-8", newline="") as f:
        header = next(csv.reader(f))
    declared = list(relations[f"consumption.{path.stem}"]["columns"])
    # The package keys its columns alphabetically, so only the set compares.
    state = "same set of columns" if sorted(header) == sorted(declared) else "DIFFERENT"
    print(f"{path.stem}: {len(header)} columns — {state}")
