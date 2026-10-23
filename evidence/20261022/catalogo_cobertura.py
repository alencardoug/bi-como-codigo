"""Prontidão do catálogo para um portal de leitura: descrições, domain/owner e testes no manifest.

Só lê arquivos. Uso, da raiz do eng_dados: `.venv/bin/python <este arquivo>`
"""
import collections
import json

m = json.load(open("dbt/target/manifest.json"))


def vazio(texto):
    return not (texto or "").strip()


por_camada = collections.defaultdict(collections.Counter)
for n in m["nodes"].values():
    if n["resource_type"] not in ("model", "seed", "snapshot"):
        continue
    c = por_camada[n["schema"]]
    c["objetos"] += 1
    c["objetos_com_descricao"] += not vazio(n.get("description"))
    meta = {**(n.get("config", {}).get("meta") or {}), **(n.get("meta") or {})}
    c["com_domain"] += bool(meta.get("domain"))
    c["com_owner"] += bool(meta.get("owner"))
    for col in n.get("columns", {}).values():
        c["colunas_declaradas"] += 1
        c["colunas_com_descricao"] += not vazio(col.get("description"))
for s in m["sources"].values():
    c = por_camada[s["schema"]]
    c["objetos"] += 1
    c["objetos_com_descricao"] += not vazio(s.get("description"))
    for col in s.get("columns", {}).values():
        c["colunas_declaradas"] += 1
        c["colunas_com_descricao"] += not vazio(col.get("description"))
testes = collections.Counter(
    "singular" if n.get("test_metadata") is None else n["test_metadata"]["name"]
    for n in m["nodes"].values() if n["resource_type"] == "test"
)
print(f"{'schema':12s} {'obj':>4s} {'c/desc':>6s} {'domain':>6s} {'owner':>6s} {'cols decl':>9s} {'c/desc':>7s}")
for s, c in sorted(por_camada.items()):
    print(f"{s:12s} {c['objetos']:4d} {c['objetos_com_descricao']:6d} {c['com_domain']:6d} {c['com_owner']:6d}"
          f" {c['colunas_declaradas']:9d} {c['colunas_com_descricao']:7d}")
print("testes de dados:", sum(testes.values()), dict(testes.most_common(8)))
print("blocos {% docs %} do projeto:", sum(1 for d in m.get("docs", {}).values() if d["package_name"] == "mvp_ed1"))
