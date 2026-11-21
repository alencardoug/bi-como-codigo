"""The fixture of §2.1: its shape checks, its totals, its coverage, the G
mutant, the package, and the draw's response to each class of rejection."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

import fixture as f
from bi_como_codigo import contract as c, envelope as e, release

SEED = 20261120  # a throwaway seed (§7 step 1)


@pytest.fixture(scope="module")
def drawn():
    fx, _ = f.generate(SEED)
    return fx


@pytest.fixture(scope="module")
def rows(drawn):
    return drawn.rows()


def _col(name):
    return f.COLUMNS.index(name)


def _replace(row, **changes):
    out = list(row)
    for name, value in changes.items():
        out[_col(name)] = value
    return tuple(out)


def test_the_drawn_fixture_has_the_shape(drawn, rows):
    f.check_shape(rows, drawn.k)
    assert 10_848 <= len(rows) <= 10_908
    assert len(rows) == f.row_count(drawn.k)
    assert drawn.k in f.K_VALUES


def test_the_draw_is_deterministic_from_its_seed(drawn):
    again, _ = f.generate(SEED)
    assert again.rows() == drawn.rows()
    other, _ = f.generate(SEED + 1)
    assert other.rows() != drawn.rows()


@pytest.mark.parametrize("damage, reason", [
    ("drop_a_row", "rows, not"),
    ("fill_g", "rows, not"),
    ("break_z", "Z is not"),
    ("repeat_a_count", "a count repeats"),
    ("repeat_an_amount", "an amount repeats"),
    ("partial_on_c", "partial month"),
    ("wrong_type", "wrong type"),
    ("gap_in_months", "not consecutive"),
    ("four_digit_count", "fewer than five"),
    ("slashed_months", "not YYYY-MM"),
    ("fractional_count", "not an integer"),
    ("larger_partial_amount", "smaller ones"),
])
def test_each_shape_property_is_checked(drawn, rows, damage, reason):
    rows = list(rows)
    k = drawn.k
    if damage == "drop_a_row":
        rows.pop(100)
    elif damage == "fill_g":
        donor = next(r for r in rows if r[_col("sales_channel_name")] == "fixture_canal_c" and r[_col("root_category_name")] == "fixture_raiz_3")
        rows.append(_replace(donor, year_month=drawn.year_month(f.G[0]), year_number=drawn.month(f.G[0])[0], month_number=drawn.month(f.G[0])[1]))
    elif damage == "break_z":
        n = next(i for i, r in enumerate(rows) if r[_col("year_month")] == drawn.year_month(f.Z[0])
                 and r[_col("sales_channel_name")] == f.Z[1] and r[_col("root_category_name")] == f.Z[2])
        rows[n] = _replace(rows[n], net_revenue_amount=Decimal("0.01"))
    elif damage == "repeat_a_count":
        rows[1] = _replace(rows[1], order_count=rows[0][_col("order_count")])
    elif damage == "repeat_an_amount":
        rows[1] = _replace(rows[1], gross_revenue_amount=rows[0][_col("net_revenue_amount")])
    elif damage == "partial_on_c":
        last = drawn.year_month(f.PARTIAL)
        channel, root = drawn.partial[0]
        rows = [_replace(r, sales_channel_name="fixture_canal_c", channel_type="fixture_tipo_2")
                if (r[_col("year_month")], r[_col("sales_channel_name")], r[_col("root_category_name")]) == (last, channel, root) else r
                for r in rows]
    elif damage == "wrong_type":
        rows[0] = _replace(rows[0], channel_type="fixture_tipo_2" if rows[0][_col("channel_type")] == "fixture_tipo_1" else "fixture_tipo_1")
    elif damage == "gap_in_months":
        first = drawn.year_month(0)
        y, m = drawn.month(0)
        earlier = f"{y - 1:04d}-{m:02d}"
        rows = [_replace(r, year_month=earlier, year_number=y - 1) if r[_col("year_month")] == first else r for r in rows]
    elif damage == "four_digit_count":
        rows[0] = _replace(rows[0], order_count=9_999)
    elif damage == "slashed_months":
        rows = [_replace(r, year_month=r[_col("year_month")].replace("-", "/")) for r in rows]
    elif damage == "fractional_count":
        rows[0] = _replace(rows[0], order_count=Decimal(rows[0][_col("order_count")]) + Decimal("0.5"))
    elif damage == "larger_partial_amount":
        last = drawn.year_month(f.PARTIAL)
        n = next(i for i, r in enumerate(rows) if r[_col("year_month")] == last)
        r = rows[n]
        gross = r[_col("unit_count")] * Decimal("399.99")
        rows[n] = _replace(r, gross_revenue_amount=gross, net_revenue_amount=gross - r[_col("discount_amount")])
    with pytest.raises(f.ShapeError, match=reason):
        f.check_shape(rows, k)


def test_a_summed_order_count_equal_to_a_displayed_number_is_refused(drawn, rows):
    """§2.1: a summary count invented by summing must be told apart."""
    month0 = drawn.year_month(0)
    cell = [n for n, r in enumerate(rows) if r[_col("year_month")] == month0
            and r[_col("sales_channel_name")] == "fixture_canal_a" and r[_col("root_category_name")] == "fixture_raiz_1"]
    rest = sum(rows[n][_col("order_count")] for n in cell[1:])
    taken = {r[_col(n)] for r in rows for n in ("order_count", "unit_count")}
    shown = sorted(units for _, units in f.summary(drawn).values())
    target = next(t for t in shown if 10_000 <= t - rest <= 999_999 and t - rest not in taken)
    rows = list(rows)
    rows[cell[0]] = _replace(rows[cell[0]], order_count=target - rest)
    with pytest.raises(f.ShapeError, match="sum of order_count"):
        f.check_shape(rows, drawn.k)


def test_g_is_empty_and_z_is_zero_in_the_summary(drawn):
    cells = f.summary(drawn)
    assert ("fixture_canal_c", f.G[0], f.G[2]) not in cells
    assert ("todos", f.G[0], f.G[2]) in cells
    net, units = cells[(f.Z[1], f.Z[0], f.Z[2])]
    assert net == Decimal("0.00") and units > 0


def test_the_mutant_has_its_own_shape(drawn):
    m = f.mutant(drawn)
    f.check_shape(m.rows(), m.k, mutant=True)
    with pytest.raises(f.ShapeError):
        f.check_shape(m.rows(), m.k)
    with pytest.raises(f.ShapeError):
        f.check_shape(drawn.rows(), drawn.k, mutant=True)
    assert f.summary(m)[("fixture_canal_c", f.G[0], f.G[2])] == (Decimal("0.00"), 0)


@pytest.fixture(scope="module")
def payload(drawn):
    return f.payload(drawn)


def test_the_totals_are_the_gates_and_the_payload_passes_its_checks(payload):
    """Python's `decimal` totals agree with the gate's DuckDB query (§3, §4)."""
    totals_raw, parquet_raw = payload
    con = f.contract()
    values = c.check_payload(con, con.reports["P01"], totals_raw, parquet_raw)
    assert str(json.loads(totals_raw)["rows"]) in values.numbers
    assert "order_count" not in json.loads(totals_raw)["sums"]


def test_the_coverage_assertion_holds_and_can_fail(drawn, payload, monkeypatch):
    count = f.coverage(drawn, *payload)
    assert count > 30_000
    real = c.needles
    monkeypatch.setattr(c, "needles", lambda values, public: real(values, public)[:-1])
    with pytest.raises(f.ShapeError, match="coverage"):
        f.coverage(drawn, *payload)


def test_coverage_fails_when_a_public_value_excludes_a_fixture_needle(drawn, payload):
    with pytest.raises(f.ShapeError, match="excluded by a public declaration"):
        f.coverage(drawn, *payload, public={"fixture_canal_a"})


def test_coverage_fails_when_a_spelling_is_missing(drawn, payload, monkeypatch):
    real = c.spellings
    monkeypatch.setattr(c, "spellings", lambda canonical: real(canonical)[:1])
    with pytest.raises(f.ShapeError, match="coverage"):
        f.coverage(drawn, *payload)


def test_the_package_opens_to_the_payload_under_the_declared_profile(payload):
    """§2.2, repeated from round 1: one profile, Diretoria, entitled to P01."""
    manifest_raw, files = f.seal(*payload)
    manifest = e.validate_manifest(manifest_raw)
    assert set(manifest.profiles) == {"diretoria"} and set(manifest.reports) == {"P01"}
    declared = release.profiles(f.HERE)
    e.check_package(manifest_raw, files, {p.id: p.password for p in declared}, expected={"P01": payload})


# --- the draw ------------------------------------------------------------------------


def _script(*answers):
    """A collision search that answers from a list, then finds nothing."""
    seen = []

    def collides(fx):
        seen.append(f.Fixture(fx.seed, fx.start, fx.k, fx.partial, dict(fx.cells)))
        return list(answers[len(seen) - 1]) if len(seen) <= len(answers) else []

    return collides, seen


def test_each_class_of_rejection_moves_what_it_names(drawn):
    a_key = next(iter(sorted(drawn.cells)))
    collides, seen = _script(
        [f.Rejection("row_count", "contract.inspect", "a.js")],
        [f.Rejection("calendar", "carrier", "b.js")],
        [f.Rejection("value", "carrier", "c.wasm", (a_key,))],
    )
    fx, record = f.draw(SEED, collides)
    assert record["draws"] == 4 and len(record["rejections"]) == 3
    assert seen[1].k != seen[0].k
    assert seen[2].start != seen[1].start
    assert seen[3].cells[a_key] != seen[2].cells[a_key]
    f.check_shape(fx.rows(), fx.k)
    assert {r["class"] for r in record["rejections"]} == {"row_count", "calendar", "value"}
    assert all("value" not in r or r["class"] for r in record["rejections"])  # the record names no value


def test_a_draw_that_never_comes_clean_is_exhausted(drawn):
    key = next(iter(sorted(drawn.cells)))
    with pytest.raises(f.DrawExhausted) as raised:
        f.draw(SEED, lambda fx: [f.Rejection("value", "carrier", "x.js", (key,))], limit=3)
    assert raised.value.record["draws"] == 3
    with pytest.raises(f.DrawExhausted):
        f.draw(SEED, lambda fx: [f.Rejection("label", "contract.inspect", "x.js")])


def test_the_provenance_names_every_needle_value(drawn, payload):
    """Every needle of the gate maps back to something the draw can move, or
    to a fixed label."""
    con = f.contract()
    values = c.check_payload(con, con.reports["P01"], *payload)
    known = f.provenance(drawn)
    assert all(v in known for v in values.texts | values.numbers if len(v) >= 3 or c.eligible_number(v))
