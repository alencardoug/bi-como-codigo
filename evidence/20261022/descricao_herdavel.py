"""Estimativa: colunas sem descrição que poderiam herdar a da origem pela linhagem.

"Herdaria" = uma folha só, com o mesmo nome. É estimativa: mesmo nome não garante mesma
semântica (`round(x, 2) as x`), e o `union` das duas origens aparece como "várias folhas".
Uso, da raiz do eng_dados, com o .env carregado: `.venv/bin/python <este arquivo>`
"""
import collections
import json

from mvp_ed1.models import lineage
from mvp_ed1.models.base import Base

m = json.loads(lineage.MANIFEST.read_text())
lin = lineage.build(m)
origem = {(t.name, c.name): (c.info or {}).get("description") for t in Base.metadata.sorted_tables for c in t.columns}
print("origem (SQLAlchemy): colunas", len(origem), "| com descrição declarada:", sum(1 for v in origem.values() if v))
desc = {}
for n in m["nodes"].values():
    if n["resource_type"] in ("model", "seed", "snapshot"):
        rel = (n["schema"], n.get("alias") or n["name"])
        for col in n.get("columns", {}).values():
            desc[(rel, col["name"])] = (col.get("description") or "").strip()
cont = collections.Counter()
for (schema, rel), colunas in lin.leaves.items():
    if schema not in ("trusted", "analytics", "consumption"):
        continue
    for col, folhas in colunas.items():
        if desc.get(((schema, rel), col)):
            cont[(schema, "já descrita")] += 1
        elif len(folhas) == 1 and next(iter(folhas))[2] == col:
            cont[(schema, "herdaria: 1 folha, mesmo nome")] += 1
        elif len(folhas) == 1:
            cont[(schema, "1 folha, nome novo")] += 1
        elif not folhas:
            cont[(schema, "sem folha (gerada)")] += 1
        else:
            cont[(schema, "várias folhas")] += 1
for k in sorted(cont):
    print(f"  {k[0]:12s} {k[1]:32s} {cont[k]:5d}")
