"""Per-layer states of the three prototype variants, read from the dumps p19_description_inheritance_prototype.py wrote.

Usage: python3 p19_variant_stats.py <dump_v0.json> <dump_v1.json> <dump_v2.json>
"""
import collections, json, sys
for nome, caminho in zip(("N41 literal", "+ conventions (N44)", "+ constant branches neutral (N45)"), sys.argv[1:]):
    d = json.load(open(caminho))
    print(f"== {nome}")
    for layer in ("staging", "trusted", "snapshots", "analytics", "consumption", "quarantine"):
        c = collections.Counter(r["state"] for r in d if r["layer"] == layer)
        print(f"   {layer:12} total={sum(c.values()):5} " + " ".join(f"{k}={c[k]}" for k in ("inherited", "hand-equal", "hand-only", "hand-differs-overwritten", "undescribed")))
