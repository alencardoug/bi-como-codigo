"""The browser check's oracle and comparator (docs/framework_prototype.md
§2.6), on readings made from the oracle itself: what equals the oracle passes,
and each alteration §2.6 names is refused for its own reason. The page itself
is read by `browser/check.mjs`, run against an artifact (`check.run`)."""

from __future__ import annotations

import copy

import pytest

import check
import fixture as fx_mod


@pytest.fixture(scope="module")
def fx():
    return fx_mod.generate(99)[0]


@pytest.fixture(scope="module")
def oracle(fx):
    return check.expected(fx)


def _seen(o: check.Oracle) -> dict:
    """A reading the page of §2.3 would give: every cell as the oracle has it."""
    def detail(f, m):
        rows = o.detail[f][m]
        notices = ([{"at": 0, "text": check.EMPTY, "empty_table": True}] if not rows else []) + \
                  ([{"at": "foot", "text": check.NOTICE}] if m == o.last else [])
        return {"header": list(check.DETAIL_HEADER), "rows": copy.deepcopy(rows), "notices": notices}
    return {
        "url": "http://127.0.0.1:1/", "wrong": {"error_ms": 10, "opened": False},
        "by_filter": {f: {"summary": {"header": list(check.SUMMARY_HEADER), "rows": copy.deepcopy(rows),
                                      "notices": [{"at": len(rows) - 5, "text": check.NOTICE}], "shown": []},
                          "detail": {m: detail(f, m) for m in o.months}} for f, rows in o.summary.items()},
        "history_at_login": 2, "history_before_logout": 2,
        "after_logout": {"login_ms": 5, "summary": False, "history": 2, "back": {"summary": False, "url": "about:blank"},
                         "same_document": False, "session_workers": [{"type": "worker", "url": "blob:x", "alive": False}]},
        "hosts": ["127.0.0.1:1", "cdn.jsdelivr.net"], "third_party_urls": ["https://cdn.jsdelivr.net/npm/x@1/a.js"],
        "page_urls": ["http://127.0.0.1:1/", "http://127.0.0.1:1/app.js", "https://cdn.jsdelivr.net/npm/x@1/a.js"],
    }


def test_the_oracle_has_g_empty_z_zero_and_the_partial_month(oracle):
    f, m, r = oracle.g
    assert next(x for x in oracle.summary[f] if x[:2] == [m, r])[2:] == [check.EMPTY, check.EMPTY]
    f, m, r = oracle.z
    assert next(x for x in oracle.summary[f] if x[:2] == [m, r])[2] == "R$ 0,00"
    assert oracle.months[-1] == oracle.last and not oracle.detail["fixture_canal_c"][oracle.last]
    assert check.brl(fx_mod.Decimal("1234.50")) == "R$ 1.234,50" and check.integer(20000) == "20.000"


def test_a_reading_equal_to_the_oracle_passes_and_each_alteration_is_refused_for_its_reason(oracle):
    seen = _seen(oracle)
    cdn = frozenset(seen["third_party_urls"])
    assert check.compare(seen, oracle, cdn_urls=cdn) == []
    proof = check.prove_comparator(seen, oracle, cdn_urls=cdn)
    assert proof and all(p["refused"] and p["for_its_reason"] for p in proof.values()), proof


@pytest.mark.parametrize("alter, reason", [
    (lambda s: s["wrong"].update(opened=True), "wrong password"),
    (lambda s: s["after_logout"].update(summary=True), "logout"),
    (lambda s: s["third_party_urls"].append("https://cdn.jsdelivr.net/npm/y@2/b.js"), "undeclared third-party URL"),
    (lambda s: s["by_filter"]["todos"]["summary"]["notices"].clear(), "notice"),
    (lambda s: s["by_filter"]["todos"]["summary"]["header"].append("Pedidos"), "summary header"),
    (lambda s: next(iter(s["by_filter"]["todos"]["detail"].values()))["rows"][0].__setitem__(2, "1"), "detail"),
])
def test_each_part_of_the_check_refuses_on_its_own(oracle, alter, reason):
    seen = _seen(oracle)
    alter(seen)
    assert reason in {r["reason"] for r in check.compare(seen, oracle, cdn_urls=frozenset(["https://cdn.jsdelivr.net/npm/x@1/a.js"]))}


def test_the_mutants_oracle_keeps_the_canonical_g_cell_alone(fx, oracle):
    m = fx_mod.mutant(fx)
    mo = check.expected(m, canonical_g=fx)
    mutant_plain = check.expected(m)
    f, month, root = oracle.g
    assert next(x for x in mo.summary[f] if x[:2] == [month, root]) == next(x for x in oracle.summary[f] if x[:2] == [month, root])
    assert mo.detail[f][month] == mutant_plain.detail[f][month] != oracle.detail[f][month]
    seen = _seen(mutant_plain)  # the page shows the mutant as it is
    assert {r["reason"] for r in check.compare(seen, mo, cdn_urls=frozenset(seen["third_party_urls"]))} == {"G"}


# --- CMP-1-08: what a pass needs ------------------------------------------------------


@pytest.mark.parametrize("alter, reason", [
    (lambda s: s["by_filter"]["todos"]["summary"]["notices"].append({"at": "foot", "text": "Pedidos: 20.000"}), "other text in a table"),
    (lambda s: s["by_filter"]["todos"]["summary"].update(header_rows=[["Total"], list(check.SUMMARY_HEADER)]), "summary header"),
    (lambda s: s.update(duplicate_filters=["todos"]), "filters"),
    (lambda s: s.update(history_at_login=1), "logout"),  # the session pushed an entry that logout left behind
    (lambda s: s["after_logout"]["back"].update(summary=True), "logout"),
])
def test_a_visible_extra_or_a_session_left_reachable_is_refused(oracle, alter, reason):
    seen = _seen(oracle)
    alter(seen)
    assert reason in {r["reason"] for r in check.compare(seen, oracle, cdn_urls=frozenset(seen["third_party_urls"]))}


def test_the_check_passes_only_with_its_proofs():
    good = {"page_passed": True, "comparator_proof": {p: {"refused": True, "for_its_reason": True} for p in check.PROOFS}}
    mutant = {"opened": True, "refused_on_g_alone": True, "detail_is_the_mutants": True}
    assert check._passed("evidence", good) == (True, [])
    assert check._passed("own", {**good, "mutant_proof": mutant}) == (True, [])
    assert not check._passed("own", good)[0]  # B with no mutant proof
    assert not check._passed("own", {**good, "mutant_proof": {**mutant, "refused_on_g_alone": False}})[0]
    assert not check._passed("evidence", {**good, "comparator_proof": {**good["comparator_proof"],
                                                                       check.PROOFS[0]: {"refused": True, "for_its_reason": False}}})[0]
    one = {check.PROOFS[0]: {"refused": True, "for_its_reason": True}}
    assert not check._passed("evidence", {**good, "comparator_proof": one})[0]  # one proof of four (CMP-2-04)
    assert not check._passed("evidence", {"page_passed": True})[0]


@pytest.mark.parametrize("url, refused", [
    ("https://example.org/x.js", True),  # an origin no one declared, even unresolved
    ("https://cdn.jsdelivr.net/npm/x@1/a.js?v=2", True),  # a query on a pinned path
    ("http://127.0.0.1:1/package/P01.bice", False),
])
def test_the_page_may_request_only_its_origin_and_declared_urls(oracle, url, refused):
    """CMP-1-09: attributed to the page or its workers; Chrome's background hosts are listed apart."""
    seen = _seen(oracle)
    seen["page_urls"].append(url)
    seen["hosts"].append("clients2.google.com")
    reasons = {r["reason"] for r in check.compare(seen, oracle, cdn_urls=frozenset(seen["third_party_urls"]))}
    assert ("undeclared URL" in reasons) == refused, reasons


# --- CMP-2-04: every summary element, the logout's document and workers, an empty cell ------


def _a_sum(oracle) -> str:
    return sorted(s for s in oracle.order_sums if "." in s)[0]


@pytest.mark.parametrize("alter, reason", [
    (lambda s, o: s["by_filter"]["todos"]["summary"].update(shown=[f"Total de pedidos: {_a_sum(o)}"]), "order_count summed"),
    (lambda s, o: s["after_logout"].update(same_document=True), "logout"),
    (lambda s, o: s["after_logout"]["session_workers"][0].update(alive=True), "logout"),
    (lambda s, o: s["after_logout"].pop("session_workers"), "logout"),
])
def test_a_sum_beside_the_table_or_a_session_kept_by_logout_is_refused(oracle, alter, reason):
    seen = _seen(oracle)
    alter(seen, oracle)
    assert reason in {r["reason"] for r in check.compare(seen, oracle, cdn_urls=frozenset(seen["third_party_urls"]))}


def test_an_empty_footer_cell_and_an_amount_beside_the_table_are_accepted(oracle):
    seen = _seen(oracle)
    seen["by_filter"]["todos"]["summary"]["notices"].append({"at": "foot", "text": ""})
    seen["by_filter"]["todos"]["summary"]["shown"] = [f"R$ {_a_sum(oracle)},00", "Mostrando 60 linhas"]
    assert check.compare(seen, oracle, cdn_urls=frozenset(seen["third_party_urls"])) == []


def test_a_summary_whose_rendered_text_was_not_read_is_refused(oracle):
    """CMP-3-04: a reading with no rendered text cannot say no sum is shown."""
    seen = _seen(oracle)
    del seen["by_filter"]["todos"]["summary"]["shown"]
    assert "summary unread" in {r["reason"] for r in check.compare(seen, oracle, cdn_urls=frozenset(seen["third_party_urls"]))}
