"""Protótipo somente leitura: caminho por coluna das colunas da P01 até as fontes.

Percorre as folhas imediatas que `mvp_ed1.models.lineage` já calcula — não
reimplementa a linhagem. Precisa de `dbt/target/manifest.json` completo.
Uso, da raiz do projeto: `.venv/bin/python data/medicoes/caminho_dos_dados_20261022/linhagem_p01.py`
"""
import json
import time

from mvp_ed1.models import lineage

inicio = time.time()
lin = lineage.build(json.loads(lineage.MANIFEST.read_text()))
print(f"build: {time.time() - inicio:.1f}s, relações: {len(lin.leaves)}, problemas: {len(lin.problems)}")


def caminho(alvo):
    arestas, vistos, fila = [], set(), [alvo]
    while fila:
        no = fila.pop()
        if no in vistos:
            continue
        vistos.add(no)
        for folha in sorted(lin.leaves.get((no[0], no[1]), {}).get(no[2], set())):
            arestas.append((folha, no))
            fila.append(folha)
    return vistos, arestas


P01 = ("consumption", "monthly_revenue_by_channel_and_category")
vistos, arestas = caminho((*P01, "net_revenue_amount"))
print(f"net_revenue_amount — nós: {len(vistos)}, arestas: {len(arestas)}")
for origem, destino in sorted(arestas, key=lambda a: (a[1], a[0])):
    print(f"  {'.'.join(origem):60s} -> {'.'.join(destino)}")
for alvo in [(*P01, "year_month"), (*P01, "sales_channel_name"), (*P01, "category_name"),
             ("analytics", "fact_sales_order_item", "is_realised"),
             ("analytics", "fact_sales_order_item", "category_key"),
             ("analytics", "fact_sales_order_item", "date_key")]:
    v, a = caminho(alvo)
    origens = sorted(".".join(o) for o in lin.origins(*alvo))
    print(f"{'.'.join(alvo)} — nós {len(v)}, arestas {len(a)}; origens: {origens}")
