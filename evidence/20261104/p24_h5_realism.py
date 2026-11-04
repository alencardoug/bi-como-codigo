"""Runbook H5, M7 to M9 in the warehouse (D5): the probes of the three generator fixes.

Run from the eng_dados root, with its .venv, the databases up:

    .venv/bin/python <bi-como-codigo>/evidence/20261104/p24_h5_realism.py

Every query goes through `evidence/20261022/ro.sh`, a read-only session. The declared tree
and price ranges are read from eng_dados' own `geracao.yml` through its loader, which
validates them, so the probe compares with the declaration of the checkout it runs in;
the legacy failure manifest is `data/legacy/manifesto.json`, the current batch's.

Expected values, each printed with PASS or FAIL:

* M7 — every leaf of `analytics.dim_category`, in both sources, on the root and middle the
  tree declares for it (N37): 0 off the tree;
* M8 — the items of `analytics.fact_sales_order_item` whose `unit_price` is outside the
  declared range of their leaf (N38): 0 in both sources. A legacy one is listed with the
  manifest's findings on its `unit_price`, to help find where the fix did not reach;
* M9 for retail — items sold before their product's launch, read as invariant 14 reads
  them (`trusted.order_items`, `orders`, `product_skus`): 0;
* M9 for legacy — the same items, each with the manifest finding that moves its date: a
  finding on the order's `placed_at` or the product's `launched_at` whose expected value
  after cleaning is not its original value (Legacy Source §3.2). 0 unexplained.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import pathlib
import subprocess
import sys

from mvp_ed1.generator.config import carregar

RO = pathlib.Path(__file__).resolve().parents[1] / "20261022" / "ro.sh"
MANIFEST = pathlib.Path("data/legacy/manifesto.json")


def query(sql: str) -> list[dict[str, str]]:
    out = subprocess.run([str(RO), "/dev/stdin", "--csv"], input=sql, capture_output=True, text=True, check=True)
    return list(csv.DictReader(io.StringIO(out.stdout)))


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def verdict(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def moves(finding: dict) -> bool:
    """A corrected finding whose cleaned value is another instant than the original."""
    if finding["resultado_esperado"] != "corrected" or finding["valor_esperado"] is None:
        return False
    try:
        return dt.datetime.fromisoformat(finding["valor_esperado"]) != dt.datetime.fromisoformat(
            finding["valor_original"]
        )
    except (TypeError, ValueError):
        return finding["valor_esperado"] != finding["valor_original"]


def main() -> int:
    config = carregar()
    tree = config.tabelas["product_categories"].processo["arvore"]
    ranges = config.tabelas["product_variants"].processo["faixa_de_preco_por_folha"]
    declared = ",\n        ".join(
        f"({literal(leaf)}, {literal(middle)}, {literal(root)})"
        for root, middles in tree.items()
        for middle, leaves in middles.items()
        for leaf in leaves
    )
    declared_ranges = ",\n        ".join(
        f"({literal(leaf)}, {low:.2f}::numeric, {high:.2f}::numeric)" for leaf, (low, high) in ranges.items()
    )
    findings: dict[tuple[str, int, str], list[dict]] = {}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for finding in manifest["achados"]:
        findings.setdefault((finding["tabela"], finding["legacy_row_id"], finding["coluna"]), []).append(finding)
    failed = False
    print(f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ} · legacy manifest batch "
          f"{manifest['lote']['hash']}")

    # ── M7 ──
    rows = query(f"""
with declared(leaf, middle, root) as (values
        {declared})
select c.source_system,
       count(*)                                                                as leaves,
       count(*) filter (where d.leaf is null)                                  as undeclared,
       count(*) filter (where d.leaf is not null and (c.sub_category_name, c.root_category_name)
                                                     is distinct from (d.middle, d.root))  as off_tree,
       string_agg(c.root_category_name || ' › ' || c.sub_category_name || ' › ' || c.category_name, '; '
                  order by c.category_name) filter (where d.leaf is null
                  or (c.sub_category_name, c.root_category_name) is distinct from (d.middle, d.root)) as examples
from analytics.dim_category c
left join declared d on d.leaf = c.category_name
group by 1 order by 1
""")
    print("\n== M7 — leaves of analytics.dim_category against the declared tree (expected 0 off it)")
    for row in rows:
        bad = int(row["undeclared"]) + int(row["off_tree"])
        failed |= bad > 0
        print(f"   {verdict(bad == 0)} {row['source_system']}: {row['leaves']} leaves, "
              f"{row['undeclared']} undeclared, {row['off_tree']} on another root or middle"
              + (f" — {row['examples']}" if row["examples"] else ""))

    # ── M8 ──
    rows = query(f"""
with ranges(leaf, low, high) as (values
        {declared_ranges})
select f.source_system, f.order_item_id, c.category_name, f.unit_price, r.low, r.high
from analytics.fact_sales_order_item f
join analytics.dim_category c using (category_key)
left join ranges r on r.leaf = c.category_name
where r.leaf is null or f.unit_price < r.low or f.unit_price > r.high
order by 1, 2
""")
    totals = query("select source_system, count(*) as items from analytics.fact_sales_order_item group by 1 order by 1")
    print("\n== M8 — fact items outside the declared range of their leaf (expected 0 in both sources)")
    for total in totals:
        outside = [r for r in rows if r["source_system"] == total["source_system"]]
        failed |= bool(outside)
        print(f"   {verdict(not outside)} {total['source_system']}: {len(outside)} of {total['items']} items")
    legacy_outside = [r for r in rows if r["source_system"] == "legacy"]
    if legacy_outside:
        ids = ", ".join(literal(r["order_item_id"]) for r in legacy_outside)
        physical = {}
        for r in query(f"select id, legacy_row_id from staging.stg_legacy__order_items where id in ({ids})"):
            physical.setdefault(r["id"], []).append(int(r["legacy_row_id"]))
        with_findings = 0
        for n, r in enumerate(legacy_outside):
            codes = [f["codigo"] for rid in physical.get(r["order_item_id"], [])
                     for f in findings.get(("order_items", rid, "unit_price"), [])]
            with_findings += bool(codes)
            if n < 10:
                print(f"      legacy item {r['order_item_id']} · {r['category_name']} · {r['unit_price']} "
                      f"outside [{r['low']}, {r['high']}] · findings: {', '.join(codes) or 'none'}")
        print(f"      legacy: {with_findings} of {len(legacy_outside)} with a finding on unit_price"
              + (" (first 10 listed)" if len(legacy_outside) > 10 else ""))

    # ── M9 ──
    rows = query("""
select i.source_system, i.order_item_id, i.order_id, s.product_id, s.launched_at, o.placed_at
from trusted.order_items i
join trusted.orders o on o.source_system = i.source_system and o.order_id = i.order_id
join trusted.product_skus s on s.source_system = i.source_system and s.product_variant_id = i.product_variant_id
where s.launched_at > o.placed_at
order by 1, 2
""")
    items = {r["source_system"]: r["items"] for r in query(
        "select source_system, count(*) as items from trusted.order_items group by 1 order by 1")}
    retail = [r for r in rows if r["source_system"] == "retail"]
    legacy = [r for r in rows if r["source_system"] == "legacy"]
    print("\n== M9 — items sold before their product's launch (retail expected 0; legacy expected 0 unexplained)")
    failed |= bool(retail)
    print(f"   {verdict(not retail)} retail: {len(retail)} of {items.get('retail', 0)} items")
    unexplained = 0
    explained_by: dict[str, int] = {}
    if legacy:
        orders = ", ".join(sorted({literal(r["order_id"]) for r in legacy}))
        products = ", ".join(sorted({literal(r["product_id"]) for r in legacy}))
        order_rows: dict[str, list[int]] = {}
        for r in query(f"select id, legacy_row_id from staging.stg_legacy__orders where id in ({orders})"):
            order_rows.setdefault(r["id"], []).append(int(r["legacy_row_id"]))
        product_rows: dict[str, list[int]] = {}
        for r in query(f"select id, legacy_row_id from staging.stg_legacy__products where id in ({products})"):
            product_rows.setdefault(r["id"], []).append(int(r["legacy_row_id"]))
        for r in legacy:
            codes = sorted(
                {f["codigo"] for rid in order_rows.get(r["order_id"], [])
                 for f in findings.get(("orders", rid, "placed_at"), []) if moves(f)}
                | {f["codigo"] for rid in product_rows.get(r["product_id"], [])
                   for f in findings.get(("products", rid, "launched_at"), []) if moves(f)}
            )
            if codes:
                for code in codes:
                    explained_by[code] = explained_by.get(code, 0) + 1
            else:
                unexplained += 1
    failed |= unexplained > 0
    print(f"   {verdict(unexplained == 0)} legacy: {len(legacy)} of {items.get('legacy', 0)} items, "
          f"{unexplained} unexplained" + (f"; explained by {explained_by}" if explained_by else ""))

    print("\nresult: " + ("every expected value met" if not failed else "FAILED — the fix did not reach the warehouse"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
