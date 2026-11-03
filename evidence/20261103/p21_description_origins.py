"""Stage 1.7, as implemented: where each column's text comes from, per layer, and the text roots left for 1.8.

Run from the eng_dados checkout, after `make check`: .venv/bin/python <this file>
Reads the manifest and the .yml files through eng_dados' own modules; writes nothing.
"""
import collections

from mvp_ed1.models import descriptions, sensitivity
from mvp_ed1.models.transport import Carry

manifest, derivacao = sensitivity.load()
textos = descriptions.derive_texts(manifest, derivacao)
camadas = ("raw", "raw_legacy", "governance", "staging", "trusted", "snapshots", "analytics", "consumption", "quarantine")
por_camada = collections.defaultdict(collections.Counter)
for (schema, _, _), origem in textos.origin.items():
    por_camada[schema][origem] += 1
for chave, motivo in textos.undescribed.items():
    por_camada[chave[0]]["undescribed"] += 1
print("origin of each column's text (declared | inherited | bridge | convention | written | generator | undescribed)")
for camada in camadas:
    print(f"  {camada:12}", dict(por_camada[camada]))
print("problems:", textos.problems, "changes:", textos.changes)

# Text roots: an undescribed column that computes, or whose carried leaves are themselves undescribed roots.
transporte = {}
for node_id, colunas in derivacao.carries.items():
    no = manifest["nodes"][node_id]
    for coluna, t in colunas.items():
        transporte[(no["schema"], no.get("alias") or no["name"], coluna)] = t


def raizes(chave, vistas):
    if chave in vistas or chave not in textos.undescribed:
        return set()
    vistas.add(chave)
    t = transporte.get(chave)
    if textos.undescribed[chave] in ("upstream_blank", "union_differs") and isinstance(t, Carry):
        saida = set()
        for folha in t.leaves:
            saida |= raizes(folha, vistas) if folha in textos.undescribed else set()
        return saida or ({chave} if textos.undescribed[chave] == "union_differs" else set())
    return {chave}


alvo = set()
for chave in textos.undescribed:
    if chave[0] in ("analytics", "consumption"):
        alvo |= raizes(chave, set())
print("text roots for analytics and consumption to reach zero:", len(alvo), dict(collections.Counter(c[0] for c in alvo)))
print("  by reason:", collections.Counter(textos.undescribed[c] for c in alvo).most_common(10))
