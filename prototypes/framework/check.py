"""The browser check of stage 2.3 (docs/framework_prototype.md §2.6).

The oracle is the page's queries run by Python's DuckDB over the clear
fixture, formatted in `pt-BR`; `browser/check.mjs` reads the page through the
DevTools protocol; `compare` judges what it read against the oracle, cell by
cell: a wrong password that opens nothing, the summary under every filter and
the detail under every filter and month, G and Z told apart, the notice of
the last month, `order_count` only native, logout, and the third-party URLs
the page requested. Every refusal names its reason.

The check is proved to fail (`prove_comparator`): its comparator refuses
altered copies of what it read — G's cell turned to `R$ 0,00`, G's notice
blanked, Z's cell turned to the notice, a summed count in a summary cell —,
each for that reason; and B served with the G mutant must open it, its detail
equal to the mutant's rows, and be refused on G and nothing else
(`expected(..., canonical_g=...)`).
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import re
import subprocess
import tempfile
from decimal import Decimal

import fixture as fx_mod
import serve

HERE = fx_mod.HERE
DRIVER = HERE / "browser" / "check.mjs"
EMPTY = "Sem vendas neste recorte."
NOTICE = "Mês em curso: os números ainda vão mudar."
ALL = "todos"
SUMMARY_HEADER = ["Mês", "Categoria raiz", "Receita líquida", "Unidades"]
DETAIL_HEADER = ["Canal", "Categoria", "Pedidos", "Unidades", "Receita líquida"]
PASSWORD = "senha_complexa_123"  # the showcase's public password (N22), declared in release/profiles.json
WRONG = "senha_errada_000"
THIRD_PARTY_HOSTS = ("cdn.jsdelivr.net", "extensions.duckdb.org")


def brl(value: Decimal) -> str:
    """`Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'})`, its
    no-break space read as a space."""
    grouped = f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {grouped}"


def integer(value: int) -> str:
    return f"{value:,}".replace(",", ".")


@dataclasses.dataclass(frozen=True)
class Oracle:
    summary: dict[str, list[list[str]]]  # filter → rows
    detail: dict[str, dict[str, list[list[str]]]]  # filter → month → rows
    months: list[str]  # the fifth, the seventh and the last
    last: str
    g: tuple[str, str, str]  # (filter, year_month, root) of G's cell
    z: tuple[str, str, str]
    order_sums: frozenset[str]  # every order_count summed over a summary cell, as the page would spell it


def _duck(fx: fx_mod.Fixture):
    import duckdb

    tmp = tempfile.TemporaryDirectory()
    path = pathlib.Path(tmp.name) / "p01.parquet"
    path.write_bytes(fx_mod.parquet(fx.rows()))
    con = duckdb.connect(":memory:")
    con.execute(f"create view p01 as select * from read_parquet('{path.as_posix()}')")
    return con, tmp


def expected(fx: fx_mod.Fixture, *, canonical_g: fx_mod.Fixture | None = None) -> Oracle:
    """The page's queries over the fixture. With `canonical_g`, G's summary
    cell keeps that fixture's expectation: the mutant's proof (FPROTO-5-06)."""
    con, tmp = _duck(fx)
    try:
        channels = [r[0] for r in con.execute("select distinct sales_channel_name from p01 order by 1").fetchall()]
        months_all = [r[0] for r in con.execute("select distinct year_month from p01 order by 1").fetchall()]
        filters = [ALL, *channels]
        summary, detail = {}, {}
        for f in filters:
            where = "true" if f == ALL else "sales_channel_name = $1"
            args = [] if f == ALL else [f]
            rows = con.execute(
                "with cells as (select m.year_month, r.root_category_name from (select distinct year_month from p01) m "
                "cross join (select distinct root_category_name from p01) r), "
                f"filtered as (select year_month, root_category_name, sum(net_revenue_amount) n, sum(unit_count) u from p01 where {where} group by all) "
                "select c.year_month, c.root_category_name, f.n, f.u from cells c left join filtered f using (year_month, root_category_name) "
                "order by 1, 2", args).fetchall()
            summary[f] = [[m, r, EMPTY if n is None else brl(n), EMPTY if u is None else integer(u)] for m, r, n, u in rows]
            detail[f] = {}
            for month in (fx.year_month(4), fx.year_month(6), fx.year_month(fx_mod.PARTIAL)):
                rows = con.execute(
                    f"select sales_channel_name, category_name, order_count, unit_count, net_revenue_amount from p01 where {where} "
                    f"and year_month = ${len(args) + 1} order by 1, 2", [*args, month]).fetchall()
                detail[f][month] = [[c, cat, integer(o), integer(u), brl(n)] for c, cat, o, u, n in rows]
    finally:
        con.close()
        tmp.cleanup()
    g = (fx_mod.G[1], fx.year_month(fx_mod.G[0]), fx_mod.G[2])
    z = (fx_mod.Z[1], fx.year_month(fx_mod.Z[0]), fx_mod.Z[2])
    if canonical_g is not None:
        canon = expected(canonical_g)
        for i, row in enumerate(summary[g[0]]):
            if (row[0], row[1]) == g[1:]:
                summary[g[0]][i] = next(r for r in canon.summary[g[0]] if (r[0], r[1]) == g[1:])
    summed = [s for s in fx_mod.order_sums(fx).values() if s > 0]  # the mutant's zeros sum to zero: no sign of summing
    sums = {integer(s) for s in summed} | {str(s) for s in summed}
    return Oracle(summary, detail, [fx.year_month(4), fx.year_month(6), fx.year_month(fx_mod.PARTIAL)],
                  months_all[-1], g, z, frozenset(sums))


# --- the comparator -------------------------------------------------------------------


def _label(o: Oracle, f: str, row: list[str] | None) -> str:
    if row and (f, row[0], row[1]) == o.g:
        return "G"
    if row and (f, row[0], row[1]) == o.z:
        return "Z"
    return "summary"


def compare(seen: dict, o: Oracle, *, cdn_urls: frozenset[str] = frozenset()) -> list[dict]:
    """Every refusal of what the page showed, each with its reason; none means
    the page passed the check."""
    out: list[dict] = []

    def refuse(reason: str, **where) -> None:
        out.append({"reason": reason, **where})

    if seen.get("error"):
        refuse("driver", detail=seen["error"][:500])
    wrong = seen.get("wrong") or {}
    if wrong.get("opened") or wrong.get("error_ms") is None:
        refuse("wrong password", detail=wrong)
    if sorted(seen.get("by_filter", {})) != sorted(o.summary) or seen.get("duplicate_filters", []):
        refuse("filters", seen=sorted(seen.get("by_filter", {})), expected=sorted(o.summary), duplicates=seen.get("duplicate_filters"))
    for f, expected_rows in o.summary.items():
        page = (seen.get("by_filter") or {}).get(f)
        if not page or not page.get("summary"):
            refuse("summary missing", filter=f)
            continue
        table = page["summary"]
        if table["header"] != SUMMARY_HEADER or any(any(c for c in row) for row in table.get("header_rows", [])[:-1]):
            refuse("summary header", filter=f, seen=table.get("header_rows", table["header"]))
        _no_other_text(refuse, table, f, "summary")
        rows = table["rows"]
        if len(rows) != len(expected_rows):
            refuse("summary rows", filter=f, seen=len(rows), expected=len(expected_rows))
        by_key = {(r[0], r[1]): r for r in rows if len(r) >= 2}
        for want in expected_rows:
            got = by_key.get((want[0], want[1]))
            if got != want:
                refuse(_label(o, f, want), filter=f, cell=want[:2], seen=got, expected=want)
        for r in rows:
            for text in r[2:]:
                if text.replace("R$ ", "") in o.order_sums:
                    refuse("order_count summed", filter=f, cell=r[:2])
        # No summary element holds a summed count, beside the table either (§2.6, CMP-2-04): every
        # pt-BR number the wrapper shows, whole, decimals and all.
        for text in table.get("shown", []):
            for number in _NUMBER.findall(text):
                if number in o.order_sums:
                    refuse("order_count summed", filter=f, shown=text[:200])
        if not any(n["text"] == NOTICE for n in table["notices"]):
            refuse("notice", filter=f, table="summary")
        for month in o.months:
            got = (page.get("detail") or {}).get(month)
            want = o.detail[f][month]
            if not got:
                refuse("detail missing", filter=f, month=month)
                continue
            if (got["rows"] or got["header"]) and (got["header"] != DETAIL_HEADER
                                                   or any(any(c for c in row) for row in got.get("header_rows", [])[:-1])):
                refuse("detail header", filter=f, month=month, seen=got.get("header_rows", got["header"]))  # an empty detail may have no table
            _no_other_text(refuse, got, f, "detail", month=month)
            data = [r for r in got["rows"]]
            if data != want and not (not want and not data):
                refuse("detail", filter=f, month=month, seen=len(data), expected=len(want),
                       first=next(({"seen": a, "expected": b} for a, b in zip(data, want) if a != b), None))
            if not want and not any(n["text"] == EMPTY for n in got["notices"]):
                refuse("detail empty", filter=f, month=month)
            has_notice = any(n["text"] == NOTICE for n in got["notices"])
            if has_notice != (month == o.last):
                refuse("notice", filter=f, table="detail", month=month)
    for name, cell in (("G", o.g), ("Z", o.z)):
        f, month, root = cell
        row = next((r for r in o.summary[f] if (r[0], r[1]) == (month, root)), None)
        page = ((seen.get("by_filter") or {}).get(f) or {}).get("summary") or {"rows": []}
        got = next((r for r in page["rows"] if r[:2] == [month, root]), None)
        if got is None or row is None or got[2:] != row[2:]:
            refuse(name, filter=f, cell=[month, root], seen=got, expected=row, check="explicit")
    after = seen.get("after_logout") or {}
    back = after.get("back") or {}
    # §2.3 item 7: a full navigation — no object of the session's document left — and no worker the
    # session started alive (CMP-2-04).
    if (after.get("summary") or after.get("login_ms") is None or seen.get("history_at_login") is None
            or after.get("history") != seen.get("history_at_login") or back.get("summary") is not False
            or after.get("same_document") is not False or after.get("session_workers") is None
            or any(w.get("alive") for w in after["session_workers"])):
        refuse("logout", detail=after, history_at_login=seen.get("history_at_login"))
    hosts = seen.get("hosts")
    if hosts is None or seen.get("page_urls") is None:
        refuse("network unobserved", detail=seen.get("net_log_error"))
    else:
        for url in seen.get("third_party_urls", []):
            host = url.split("/")[2]
            if host in THIRD_PARTY_HOSTS and url not in cdn_urls:
                refuse("undeclared third-party URL", url=url)
        # What the page and its workers requested: the local origin, or a declared URL exactly, query
        # and all — any other origin is refused, even one Chrome could not resolve (CMP-1-09).
        local = "/".join(seen.get("url", "").split("/")[:3]) + "/"
        for url in seen["page_urls"]:
            # a WebSocket to anything but the local origin is another origin (CMP-2-06)
            if not url.startswith(local) and url not in cdn_urls:
                refuse("undeclared URL", url=url)
    return out


def _no_other_text(refuse, table: dict, f: str, name: str, **where) -> None:
    """A table shows its cells and the contract's notices, nothing else: a footer
    or a row of one cell with any other text is refused (CMP-1-08)."""
    for n in table.get("notices", []):
        if n["text"] not in (NOTICE, EMPTY, ""):  # an empty cell shows nothing (CMP-2-04)
            refuse("other text in a table", filter=f, table=name, text=n["text"][:200], **where)


def blocked_hosts(seen: dict) -> list[str]:
    """Hosts Chrome requested that do not resolve in the check — its own
    services, or a page request that failed —, listed beside the result."""
    origin = seen.get("url", "").split("/")[2] if seen.get("url") else ""
    return sorted(h for h in seen.get("hosts") or [] if h != origin and h not in THIRD_PARTY_HOSTS)


# --- the proofs -----------------------------------------------------------------------


def _set(seen: dict, f: str, key: tuple[str, str], column: int, text: str) -> dict:
    out = copy.deepcopy(seen)
    for r in out["by_filter"][f]["summary"]["rows"]:
        if r[:2] == list(key):
            r[column] = text
    return out


#: §2.6's altered readings, every one of which the comparator must refuse for its own reason.
PROOFS = ("G's cell turned to R$ 0,00", "G's notice blanked", "Z's cell turned to the notice", "a summed count in a summary cell")
_NUMBER = re.compile(r"(?<![\d.,])\d(?:[\d.]*\d)?(?:,\d+)?(?![\d,])")


def prove_comparator(seen: dict, o: Oracle, **kw) -> dict[str, dict]:
    """§2.6: each altered copy refused, for its own reason."""
    if compare(seen, o, **kw):
        raise ValueError("the proof needs a reading the comparator accepts")
    g_f, g_m, g_r = o.g
    z_f, z_m, z_r = o.z
    some = next(r for r in seen["by_filter"][ALL]["summary"]["rows"] if r[2] != EMPTY)
    a_sum = sorted(o.order_sums)[0] if o.order_sums else "0"
    cases = {
        "G's cell turned to R$ 0,00": (_set(seen, g_f, (g_m, g_r), 2, "R$ 0,00"), "G"),
        "G's notice blanked": (_set(seen, g_f, (g_m, g_r), 2, ""), "G"),
        "Z's cell turned to the notice": (_set(seen, z_f, (z_m, z_r), 2, EMPTY), "Z"),
        "a summed count in a summary cell": (_set(seen, ALL, (some[0], some[1]), 3, a_sum), "order_count summed"),
    }
    out = {}
    for name, (altered, reason) in cases.items():
        refusals = compare(altered, o, **kw)
        out[name] = {"refused": bool(refusals), "for_its_reason": any(r["reason"] == reason for r in refusals),
                     "reasons": sorted({r["reason"] for r in refusals})}
    return out


# --- the run ----------------------------------------------------------------------------


def read(artifact: pathlib.Path, months: list[str], out: pathlib.Path, *, timeout: float = 900) -> dict:
    """The page served on 127.0.0.1 and read by the driver."""
    with serve.Server(artifact) as server, tempfile.TemporaryDirectory(prefix="bice-check-") as tmp:
        config = {"url": server.url, "out": str(out), "password": PASSWORD, "wrong": WRONG, "months": months}
        path = pathlib.Path(tmp) / "config.json"
        path.write_text(json.dumps(config))
        subprocess.run(["node", str(DRIVER), str(path)], capture_output=True, timeout=timeout, check=False)
    return json.loads(out.read_text(encoding="utf-8"))


def cdn_urls(candidate: str) -> frozenset[str]:
    declared = json.loads((HERE / candidate / "cdn.json").read_text(encoding="utf-8"))
    return frozenset(f["url"] for f in declared["files"])


def mutant_proof(artifact: pathlib.Path, mutant: fx_mod.Fixture, canonical: fx_mod.Fixture, out: pathlib.Path, *,
                 cdn: frozenset[str] = frozenset()) -> dict:
    """B served with the G mutant: it must open, its detail equal the mutant's
    rows, and the check — the canonical expectation kept for G's summary cell
    alone — refuse it on G and on nothing else (§2.6, FPROTO-5-06)."""
    o = expected(mutant, canonical_g=canonical)
    seen = read(artifact, o.months, out)
    refusals = compare(seen, o, cdn_urls=cdn)
    reasons = sorted({r["reason"] for r in refusals})
    opened = bool((seen.get("by_filter") or {}).get(ALL, {}).get("summary"))
    return {"opened": opened, "reasons": reasons, "refused_on_g_alone": opened and reasons == ["G"],
            "detail_is_the_mutants": not any(r["reason"].startswith("detail") for r in refusals)}


def _passed(candidate: str, result: dict) -> tuple[bool, list[str]]:
    """The check passes only with its proofs (CMP-1-08): the page read as the
    oracle says, every altered reading refused for its own reason, and — for
    B — the G mutant opened, its detail the mutant's and refused on G alone."""
    why = [] if result["page_passed"] else ["the page's reading was refused"]
    proof = result.get("comparator_proof")
    if not proof or set(proof) != set(PROOFS) or not all(p["refused"] and p["for_its_reason"] for p in proof.values()):
        why.append("the comparator's proof is missing or failed")
    if candidate == "own":
        m = result.get("mutant_proof")
        if not m or not (m["opened"] and m["refused_on_g_alone"] and m["detail_is_the_mutants"]):
            why.append("B's G mutant proof is missing or failed")
    return not why, why


def run(candidate: str, artifact: pathlib.Path, fx: fx_mod.Fixture, out: pathlib.Path, *,
        mutant_artifact: pathlib.Path | None = None, mutant: fx_mod.Fixture | None = None) -> dict:
    """The browser check of one artifact, its comparator's proof, and — for B —
    the mutant's."""
    out.mkdir(parents=True, exist_ok=False)
    o = expected(fx)
    cdn = cdn_urls(candidate)
    seen = read(artifact, o.months, out / "seen.json")
    refusals = compare(seen, o, cdn_urls=cdn)
    result = {"candidate": candidate, "page_passed": not refusals, "refusals": refusals, "blocked_hosts": blocked_hosts(seen),
              "third_party_urls": [u for u in seen.get("third_party_urls", []) if u.split("/")[2] in THIRD_PARTY_HOSTS],
              "login_ms": seen.get("login_ms"), "summary_ms": seen.get("summary_ms"), "seconds": seen.get("seconds")}
    if not refusals:
        result["comparator_proof"] = prove_comparator(seen, o, cdn_urls=cdn)
    if mutant_artifact is not None and mutant is not None:
        result["mutant_proof"] = mutant_proof(mutant_artifact, mutant, fx, out / "mutant-seen.json", cdn=cdn)
    result["passed"], result["why_not"] = _passed(candidate, result)
    (out / "check.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return result
