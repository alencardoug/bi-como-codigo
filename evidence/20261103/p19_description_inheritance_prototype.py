"""Prototype of the conservative description inheritance (stage 1.7, N40–N42).

Run from the eng_dados checkout: .venv/bin/python <this file> [--dump PATH]
Reads dbt/target/manifest.json only; writes nothing in the repository.
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys
from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import Scope, traverse_scope

from mvp_ed1.legacy import ponte
from mvp_ed1.legacy import schema as legacy_schema
from mvp_ed1.models import Base
from mvp_ed1.models import sensitivity as S


@dataclass(frozen=True)
class Carry:
    leaves: frozenset          # {(schema, relation, column)}


@dataclass(frozen=True)
class Computed:
    kind: str


def unparen(e):
    while isinstance(e, exp.Paren):
        e = e.this
    return e


def sa_type_sql(col) -> str:
    return sqlglot.parse_one(f"cast(x as {col.type.compile(dialect=__import__('sqlalchemy.dialects.postgresql', fromlist=['dialect']).dialect())})", read="postgres").to.sql("postgres")


# ── Declared texts at the sources ───────────────────────────────────────────────
TECH = {  # placeholder: technical columns by name, as sensitivity treats them
    **{c: "[tech airbyte]" for c in S.AIRBYTE_COLUMNS},
    **{c: "[tech stream]" for c in S.STREAM_COLUMNS},
    **{c: "[tech dbt snapshot]" for c in S.SNAPSHOT_COLUMNS},
    legacy_schema.IDENTIDADE: "[tech legacy identity]",
}


def source_texts_and_types():
    texts, types = {}, {}
    for table in Base.metadata.tables.values():
        dec = {c.name: c for c in table.columns}
        for layer in ("raw", "raw_legacy"):
            names = legacy_schema.colunas(table.name) if layer == "raw_legacy" else list(dec)
            for c in names:
                texts[(layer, table.name, c)] = dec[c].info["description"]
                types[(layer, table.name, c)] = sa_type_sql(dec[c])
            for c in S.AIRBYTE_COLUMNS:
                texts[(layer, table.name, c)] = TECH[c]
            if layer == "raw_legacy":
                texts[(layer, table.name, legacy_schema.IDENTIDADE)] = TECH[legacy_schema.IDENTIDADE]
    for sink, origin in S.STREAM_SINKS.items():
        t = Base.metadata.tables[f"oltp.{origin}"]
        for c in t.columns:
            texts[("raw", sink, c.name)] = c.info["description"]
            types[("raw", sink, c.name)] = sa_type_sql(c)
        for c in S.STREAM_COLUMNS:
            texts[("raw", sink, c)] = TECH[c]
    return texts, types


# ── Carry classification, scope by scope ────────────────────────────────────────

def carry_by_output(query, propria, origin_type):
    saidas: dict[int, dict] = {}

    def resolve(col: exp.Column, escopo: Scope):
        atual = escopo
        while atual is not None:
            fonte = atual.sources.get(col.table)
            if isinstance(fonte, exp.Table):
                if not fonte.db or (fonte.db, fonte.name) == propria:
                    return Computed("self-or-function")
                return Carry(frozenset({(fonte.db, fonte.name, col.name)}))
            if isinstance(fonte, Scope):
                known = saidas.get(id(fonte), saidas.get(id(fonte.expression), {}))
                if col.name in known:
                    return known[col.name]
                return Computed("table-function" if "*" in known else "unresolved")
            if fonte is not None:
                return Computed("unnest-or-values")
            atual = atual.parent
        return Computed("unresolved")

    def classify(proj, escopo):
        e = unparen(proj.this if isinstance(proj, exp.Alias) else proj)
        if isinstance(e, exp.Column):
            return resolve(e, escopo)
        if isinstance(e, exp.Cast) and isinstance(unparen(e.this), exp.Column):
            r = resolve(unparen(e.this), escopo)
            if isinstance(r, Carry):
                target = e.to.sql("postgres")
                if all(origin_type(leaf) == target for leaf in r.leaves):
                    return r
                return Computed(f"cast:{target}")
            return r if isinstance(r, Computed) else Computed("cast")
        if isinstance(e, exp.Cast) and isinstance(unparen(e.this), (exp.Literal, exp.Null)):
            return Computed("Cast:literal")
        return Computed(type(e).__name__)

    for escopo in traverse_scope(query):
        consulta = escopo.expression
        while isinstance(consulta, (exp.Lateral, exp.Subquery)):
            consulta = consulta.this
        if isinstance(consulta, exp.SetOperation):
            ramos = [saidas.get(id(r), saidas.get(id(r.expression), {})) for r in (escopo.union_scopes or [])]
            nomes = [list(r.keys()) for r in ramos]
            combinado = {}
            for pos, nome in enumerate(nomes[0] if nomes else []):
                partes = [ramo[rn[pos]] for ramo, rn in zip(ramos, nomes) if pos < len(rn)]
                if LITERAL_NEUTRAL and any(isinstance(p, Carry) for p in partes) and all(
                        isinstance(p, Carry) or p.kind in ("Literal", "Null", "Boolean", "Neg", "Cast:literal") for p in partes):
                    combinado[nome] = Carry(frozenset().union(*(p.leaves for p in partes if isinstance(p, Carry))))
                elif all(isinstance(p, Carry) for p in partes):
                    combinado[nome] = Carry(frozenset().union(*(p.leaves for p in partes)))
                else:
                    kinds = sorted({p.kind for p in partes if isinstance(p, Computed)})
                    combinado[nome] = Computed("union[" + ",".join(kinds) + "]")
            for k in (id(escopo), id(escopo.expression), id(consulta)):
                saidas[k] = combinado
            if isinstance(consulta.parent, exp.Subquery):
                saidas[id(consulta.parent)] = combinado
            continue
        if isinstance(consulta, exp.Query):
            res = {p.alias_or_name: classify(p, escopo) for p in consulta.selects}
        else:
            res = {"*": Computed("table-function")}
        for k in (id(escopo), id(escopo.expression), id(consulta)):
            saidas[k] = res
        if isinstance(consulta.parent, exp.Subquery):
            saidas[id(consulta.parent)] = res
    return saidas.get(id(query), {})


# ── The bridge declaration (N41), simulated from ponte.py's own rule ────────────

def bridge_pairs(manifest):
    """legado__X.col → stg_retail__X.col when the bridge reproduces the retail projection.

    Simulated: same output name in the retail staging model, minus the outputs whose
    retail expression is one of `FORA_DA_ORIGEM` (the legacy puts something else there).
    """
    retail = {n["name"]: n for n in manifest["nodes"].values() if n["resource_type"] == "model" and n["name"].startswith("stg_retail__")}
    pairs = {}
    excluded = set()
    for n in manifest["nodes"].values():
        if n["resource_type"] != "model" or not n["name"].startswith("legado__"):
            continue
        tabela = n["name"].removeprefix("legado__")
        r = retail.get("stg_retail__" + tabela)
        if not r:
            continue
        # outputs of the retail `renomeado` whose expression is a FORA_DA_ORIGEM key
        tree = sqlglot.parse_one(r["compiled_code"], read="postgres")
        fora = set()
        for sel in tree.find_all(exp.Select):
            for proj in sel.selects:
                inner = unparen(proj.this if isinstance(proj, exp.Alias) else proj)
                if any(isinstance(c, exp.Column) and c.name in ponte.FORA_DA_ORIGEM for c in inner.find_all(exp.Column)) or (isinstance(inner, exp.Column) and inner.name in ponte.FORA_DA_ORIGEM):
                    fora.add(proj.alias_or_name)
        pairs[n["name"]] = ("stg_retail__" + tabela, fora)
    return pairs


def main(argv):
    global LITERAL_NEUTRAL, CONVENTIONS
    LITERAL_NEUTRAL = '--literal-neutral' in argv
    CONVENTIONS = '--conventions' in argv
    manifest = json.loads(S.MANIFEST.read_text(encoding="utf-8"))
    deriv = S.derive(manifest)
    assert not deriv.problems, deriv.problems[:3]
    esquema, _ = S.source_leaves()
    for fonte in manifest["sources"].values():
        for c in fonte.get("columns", {}).values():
            esquema[fonte["schema"]].setdefault(fonte["identifier"], {})[c["name"]] = "text"
    nos = {k: v for k, v in manifest["nodes"].items() if v["resource_type"] in ("model", "seed", "snapshot")}
    for node_id, cols in deriv.levels.items():
        no = nos[node_id]
        esquema[no["schema"]][no.get("alias") or no["name"]] = {c: "text" for c in cols}
    banco = next(iter(nos.values()))["database"]
    catalogo = {banco: {s: dict(t) for s, t in esquema.items()}}

    texts, types = source_texts_and_types()
    for fonte in manifest["sources"].values():
        if fonte["schema"] in ("raw", "raw_legacy"):
            continue
        for c in fonte.get("columns", {}).values():
            if (c.get("description") or "").strip():
                texts[(fonte["schema"], fonte["identifier"], c["name"])] = c["description"].strip()
    origin = dict(types)      # (schema, rel, col) → declared origin type, carried transitively

    def origin_type(leaf):
        return origin.get(leaf)

    pairs = bridge_pairs(manifest)
    stats = collections.defaultdict(collections.Counter)
    undescribed_names = collections.defaultdict(collections.Counter)
    computed_kinds = collections.defaultdict(collections.Counter)
    samples = collections.defaultdict(list)
    dump = []

    for node_id in S._topological(nos):
        no = nos[node_id]
        rel = (no["schema"], no.get("alias") or no["name"])
        hand = {c["name"]: c for c in no.get("columns", {}).values()}
        cols = deriv.levels[node_id]
        if no["resource_type"] == "seed":
            result = {c: Computed("seed") for c in cols}
        else:
            tree = qualify(sqlglot.parse_one(no["compiled_code"], read="postgres"), schema=catalogo, dialect="postgres", validate_qualify_columns=False)
            result = carry_by_output(tree, rel, origin_type)
            if no["resource_type"] == "snapshot":
                result.update({c: Computed("snapshot-tech") for c in S.SNAPSHOT_COLUMNS})
        layer = no["schema"]
        for col in cols:
            r = result.get(col, Computed("missing"))
            h = hand.get(col, {})
            htext = (h.get("description") or "").strip()
            reason = (h.get("meta") or {}).get("description_reason")
            inherited = None
            how = None
            if no["name"] in pairs and col not in pairs[no["name"]][1]:
                partner = ("staging", pairs[no["name"]][0], col)
                if partner in texts:
                    inherited, how = texts[partner], "bridge-pair"
                    origin.setdefault((layer, rel[1], col), origin.get(partner))
                else:
                    how = "bridge-pair-missing"
            elif isinstance(r, Carry):
                ts = [texts.get(l) for l in r.leaves]
                if all(ts) and len(set(ts)) == 1:
                    inherited, how = ts[0], ("union-same" if len(r.leaves) > 1 else "carry")
                    ots = {origin.get(l) for l in r.leaves}
                    if len(ots) == 1:
                        origin[(layer, rel[1], col)] = ots.pop()
                elif all(ts):
                    how = "union-differs"
                else:
                    how = "carry-upstream-blank"
            elif col in TECH:
                inherited, how = TECH[col], "tech-by-name"
            elif CONVENTIONS and col in ("source_system", "is_deleted") and isinstance(r, Computed):
                inherited, how = f"[convention {col}]", "convention"
            else:
                how = "computed:" + r.kind.split("[")[0]
                computed_kinds[layer][r.kind] += 1

            if inherited and htext and htext != inherited:
                state = "hand-differs-reason" if reason else "hand-differs-overwritten"
                final = htext if reason else inherited
            elif inherited:
                state, final = ("hand-equal" if htext else "inherited"), inherited
            elif htext:
                state, final = "hand-only", htext
            else:
                state, final = "undescribed", None
                undescribed_names[layer][col] += 1
            stats[layer][state] += 1
            stats[layer]["total"] += 1
            stats[layer]["how:" + how] += 1
            if final:
                texts[(layer, rel[1], col)] = final
            if len(samples[(layer, state)]) < 6:
                samples[(layer, state)].append(f"{rel[1]}.{col} [{how}]")
            dump.append({"layer": layer, "relation": rel[1], "column": col, "how": how, "state": state,
                         "leaves": sorted(map(".".join, r.leaves)) if isinstance(r, Carry) else None,
                         "text": final})

    print('variant:', 'literal-neutral' if LITERAL_NEUTRAL else '-', 'conventions' if CONVENTIONS else '-')
    order = ("staging", "trusted", "snapshots", "analytics", "consumption", "quarantine")
    for layer in order:
        st = stats[layer]
        print(f"\n== {layer}: {st['total']} columns")
        print("   " + "  ".join(f"{k}={st[k]}" for k in ("inherited", "hand-equal", "hand-only", "hand-differs-overwritten", "undescribed")))
        print("   how:", {k[4:]: v for k, v in sorted(st.items()) if k.startswith("how:")})
        print("   undescribed by name (top):", undescribed_names[layer].most_common(12))
    print("\n== computed kinds, analytics+consumption:", (computed_kinds["analytics"] + computed_kinds["consumption"]).most_common(15))
    for key in [("consumption", "inherited"), ("consumption", "undescribed"), ("analytics", "hand-differs-overwritten"), ("consumption", "hand-differs-overwritten"), ("trusted", "undescribed")]:
        print(key, samples[key])
    if "--dump" in argv:
        pathlib.Path(argv[argv.index("--dump") + 1]).write_text(json.dumps(dump, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main(sys.argv[1:])
