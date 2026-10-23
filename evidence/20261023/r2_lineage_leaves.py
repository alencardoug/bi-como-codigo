"""Reproduction of E3: lineage leaves do not tell a copy from an aggregation or a calculation.

Run from the eng_dados root with its .venv and its .env loaded.
"""
from mvp_ed1.models import sensitivity as s

schema = {"raw": {"orders": {"total_amount": "numeric"}}}
levels = {("raw", "orders", "total_amount"): "confidential"}
for expr in ["total_amount", "sum(total_amount)", "round(total_amount, 2)", "total_amount * 100",
             "cast(total_amount as numeric(12,2))"]:
    node = {"unique_id": "model.probe.x", "schema": "consumption", "name": "x",
            "compiled_code": f"select {expr} as total_amount from wh.raw.orders"}
    problems, warnings = [], []
    leaves = s._derive_node(node, schema, levels, "wh", problems, warnings)
    print(f"{expr:40s} => {sorted(leaves['total_amount'])}")
