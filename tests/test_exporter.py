"""The exporter of stage 2.4 (docs/exporter.md), end to end over the fake
warehouse of §12: the honest run, then every mutation of §12's table with its
exact refusal code and its positive control through the same path."""

from __future__ import annotations

import functools
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

import exporter_world as xw  # noqa: E402
import fake_warehouse as fw  # noqa: E402
from bi_como_codigo import envelope as e  # noqa: E402
from bi_como_codigo.exporter import Refused  # noqa: E402
from bi_como_codigo.exporter import receipt as rc, run  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _memoized_kek():
    """PBKDF2 at 600,000 iterations is a pure function of (password, salt,
    iterations): memoized here, since `release.verify` derives per report."""
    original = e.derive_kek
    e.derive_kek = functools.cache(original)
    yield
    e.derive_kek = original


@pytest.fixture(scope="module")
def built(_memoized_kek):
    w = xw.make_world()
    yield w
    w.cleanup()


@pytest.fixture
def world(built):
    w = xw.copy_world(built)
    yield w
    w.cleanup()


def export(world, fake=None, metadata=None, environ=None, checked_only=False):
    """The run over the fake. With `checked_only`, it stops once every payload
    has passed the writer, the round trip and the gate's checks, before the
    sealing and the candidate, and returns the payloads."""
    fake = fake or world.fake()
    body = run.export(
        world.root,
        dict(environ or world.environ),
        connect=lambda _settings, _absent: fake,
        fetch_metadata=metadata or world.fetch_metadata(),
        diagnose=(lambda _contract, payloads, _run_dir: payloads) if checked_only else None,
    )
    return body, fake


def test_the_honest_run_writes_the_sealed_package_its_metadata_and_receipt(world):
    body, fake = export(world)
    out = world.out
    assert sorted(p.name for p in out.iterdir()) == ["metadata.json", "package", "run.json"]
    assert (out / "metadata.json").read_bytes() == world.metadata_raw
    assert rc.load((out / "run.json").read_bytes(), fake.contract) == json.loads((out / "run.json").read_bytes())
    manifest = e.validate_manifest((out / "package" / "manifest.json").read_bytes())
    assert len(manifest.reports) == 16
    assert manifest.entitled("P13") == {"diretoria", "logistica"}
    assert all(manifest.entitled(r) == {"diretoria"} for r in manifest.reports if r != "P13")
    assert [f["code"] for f in body["facts"]] == list(rc.FACT_ORDER)
    assert all(v["witness_equal"] for v in body["views"])
    assert [r["live"] == "none" for r in body["candidate"]["verify"]] == [True, False]
    assert fake.committed and fake.closed
    assert not any(world.staging.glob("run-*")), "the run directory is removed"


# --- helpers -------------------------------------------------------------------------------------

import datetime as dt  # noqa: E402
import os  # noqa: E402
import signal  # noqa: E402
from decimal import Decimal  # noqa: E402

from bi_como_codigo.exporter import (  # noqa: E402
    reference as R,
    source as S,
    views as V,
    writer as W,
)
import bi_como_codigo.exporter as X  # noqa: E402

P13 = "on_time_delivery_rate_by_carrier"
SKUS = "skus_below_reorder_point"


def refuse(world, code, fake=None, **kw):
    """The run refuses with exactly `code`, leaves no result and no run directory."""
    fake = fake or world.fake()
    with pytest.raises(Refused) as caught:
        export(world, fake, **kw)
    assert caught.value.code == code, caught.value
    assert not world.out.exists()
    assert not any(world.staging.glob("run-*"))
    return caught.value, fake


def col(fake, view, name):
    return fake.contract.by_view()[view].names.index(name)


def set_cell(fake, view, row, name, value):
    rows = [list(r) for r in fake.rows[view]]
    rows[row][col(fake, view, name)] = value
    fake.rows[view] = [tuple(r) for r in rows]


def passes(world, fake, *views):
    """The positive control: the same change, with its witness regenerated,
    passes the checks, the writer, the round trip and the gate's checks of every
    payload — the path its mutation is refused on. The sealing and the candidate
    are the honest run's and the candidate tests'. Returns the payloads."""
    for view in views:
        world.rewitness(fake, view)
    fresh = world.fake()
    fresh.rows = fake.rows
    payloads, _ = export(world, fresh, checked_only=True)
    assert len(payloads) == 16 and not any(world.staging.glob("run-*"))
    return payloads


# --- the connection --------------------------------------------------------------------------------


def test_the_reader_issues_the_protocol_in_order_and_commits_once(world):
    _payloads, fake = export(world, checked_only=True)
    assert [sql for sql, _ in fake.log] == fake.protocol()
    assert fake.committed


def test_statements_out_of_order_refuse_with_nothing_after(world, monkeypatch):
    original = S.facts

    def swapped(s, contract):
        S.check_login(s, contract.login)  # check 3 before check 2
        return original(s, contract)

    monkeypatch.setattr(S, "facts", swapped)
    refusal, fake = refuse(world, X.STATEMENT_FAILED)
    assert len(fake.log) == 1 and not fake.committed and refusal.cause == "RuntimeError" and refusal.check == "login"


#: What a failed statement names, by its place in the protocol.
_STATEMENT_NAMES = (["transaction", "provenance", "login", "memberships", "role_attributes", "inventory", "access",
                     "schema_access", "attributes", *["set_policy"] * 4, "policy", "collation"]
                    + ["count", "rows"] * 16)


@pytest.mark.parametrize("at", range(1, len(fw.Fake().protocol()) + 1))
def test_a_failure_at_each_statement_refuses_with_no_further_statement(built, at):
    world = xw.copy_world(built)
    try:
        fake = world.fake()
        fake.fail_at = at
        connections = []

        def connect(_s, _a):
            connections.append(1)
            return fake

        with pytest.raises(Refused) as caught:
            run.export(world.root, dict(world.environ), connect=connect, fetch_metadata=world.fetch_metadata())
        assert len(fake.log) == at, "nothing is issued after the failed statement"
        assert len(connections) == 1 and not fake.committed and fake.closed
        assert len(_STATEMENT_NAMES) == len(fake.protocol())
        assert (caught.value.code, caught.value.check, caught.value.cause) == (X.STATEMENT_FAILED, _STATEMENT_NAMES[at - 1], "RuntimeError")
        view_at = (at - 16) // 2 if at > 15 else None
        assert caught.value.view == (fake.contract.views[view_at].view if view_at is not None else None)
        assert "hunter2" not in str(caught.value)
        assert not any(world.staging.glob("run-*"))
    finally:
        world.cleanup()


def test_a_failed_commit_refuses(world):
    fake = world.fake()
    fake.fail_commit = True
    refuse(world, X.COMMIT_FAILED, fake)


# --- the facts ------------------------------------------------------------------------------------


@pytest.mark.parametrize("attr, value", [("isolation", "read committed"), ("read_only", "off")])
def test_check_1_the_transaction(world, attr, value):
    fake = world.fake()
    setattr(fake, attr, value)
    refuse(world, X.FACT_TRANSACTION, fake)


@pytest.mark.parametrize("change", [
    lambda f: f.set_override.update({"TimeZone": "America/Sao_Paulo"}),
    lambda f: f.collation.update({"datcollate": "en_US.utf8"}),
    lambda f: setattr(f, "collation_actual", "2.40"),
    lambda f: f.encodings.__setitem__(1, "LATIN1"),
    lambda f: f.encodings.__setitem__(0, "SQL_ASCII"),
], ids=["setting_read_back_differs", "collation_field", "effective_version_drifts", "client_encoding", "server_encoding"])
def test_check_8_the_text_form_policy(world, change):
    fake = world.fake()
    change(fake)
    refuse(world, X.FACT_POLICY, fake)


def test_check_8_two_accepted_builds_with_different_policies_each_run_under_its_own(world):
    body = world.views_json()
    second = json.loads(json.dumps(body["accepted_builds"][0]))
    second["provenance"] = {**second["provenance"], "sequence": 2}
    second["policy"] = {**second["policy"], "TimeZone": "America/Sao_Paulo", "DateStyle": "ISO, DMY"}
    body["accepted_builds"].append(second)
    world.write_views(body)
    first = world.fake()
    export(world, first, checked_only=True)
    assert [p for sql, p in first.log if sql == S.Q_SET_POLICY][0] == ("TimeZone", "UTC")
    fake = world.fake()
    fake.provenance = [{**fake.provenance[0], "sequence": 2}]
    fake.hash_policy = dict(second["policy"])
    export(world, fake, checked_only=True)
    assert [p for sql, p in fake.log if sql == S.Q_SET_POLICY][0] == ("TimeZone", "America/Sao_Paulo")
    wrong = world.fake()  # the second build's row, hashed under the first's policy
    wrong.provenance = [{**wrong.provenance[0], "sequence": 2}]
    refuse(world, X.WITNESS_MISMATCH, wrong)


@pytest.mark.parametrize("who", ["session_user", "current_user"])
def test_check_3_the_login(world, who):
    fake = world.fake()
    setattr(fake, who, "analyst")  # as after SET ROLE
    refuse(world, X.FACT_LOGIN, fake)


@pytest.mark.parametrize("change", [
    lambda f: f.memberships.clear(),
    lambda f: (f.memberships.append(("consumption_reader", "pg_read_all_data", False, True, True)),
               f.roles.update({"pg_read_all_data": {**f.roles["analyst"]}})),
    lambda f: (f.memberships.append(("analyst", "warehouse_owner", False, True, True)),
               f.roles.update({"warehouse_owner": {**f.roles["analyst"]}})),
    lambda f: f.memberships.__setitem__(0, f.memberships[0][:2] + (True,) + f.memberships[0][3:]),
    lambda f: f.memberships.__setitem__(0, f.memberships[0][:4] + (not f.memberships[0][4],)),
    lambda f: f.memberships.__setitem__(0, f.memberships[0][:3] + (not f.memberships[0][3],) + f.memberships[0][4:]),
    lambda f: f.roles["analyst"].update({"createrole": True}),
    lambda f: f.roles["consumption_reader"].update({"super": True}),
    lambda f: f.roles["analyst"].update({"canlogin": True}),
], ids=["missing", "extra", "nested", "admin_option", "set_option", "inherit_option", "createrole", "superuser", "canlogin"])
def test_check_4_the_roles(world, change):
    fake = world.fake()
    change(fake)
    refuse(world, X.FACT_ROLES, fake)


@pytest.mark.parametrize("change", [
    lambda f: f.inventory.pop(0),
    lambda f: f.inventory.append((99_001, "extra_view", "v")),
    lambda f: f.inventory.append((99_002, "staging_table", "r")),
    lambda f: f.inventory.__setitem__(0, f.inventory[0][:2] + ("m",)),
], ids=["view_missing", "extra_view", "extra_table_not_granted", "another_kind"])
def test_check_5_the_inventory(world, change):
    fake = world.fake()
    change(fake)
    refuse(world, X.FACT_INVENTORY, fake)


def _first_oid(fake):
    return sorted(fake.access)[0]


@pytest.mark.parametrize("change", [
    lambda f: f.access[_first_oid(f)].update({"SELECT": False}),
    lambda f: f.access[_first_oid(f)].update({"INSERT": True}),
    lambda f: f.access[_first_oid(f)].update({"col_UPDATE": True}),
    lambda f: f.access[_first_oid(f)].update({"owner": True}),
    lambda f: setattr(f, "schema_access", (True, True)),
    lambda f: setattr(f, "schema_access", (False, False)),
], ids=["select_refused", "table_insert", "column_update", "owner_reachable", "schema_create", "schema_usage_refused"])
def test_check_6_the_access(world, change):
    fake = world.fake()
    change(fake)
    refuse(world, X.FACT_ACCESS, fake)


def test_check_7_a_trailing_column_on_an_accepted_empty_view(world):
    body = world.views_json()
    entry = next(v for v in body["views"] if v["view"] == SKUS)
    entry["may_be_empty"] = True
    world.write_views(body)
    fake = world.fake()
    fake.rows[SKUS] = []
    world.rewitness(fake, SKUS)
    fake = world.fake()
    fake.rows[SKUS] = []
    oid = next(o for o, n, _k in fake.inventory if n == SKUS)
    fake.attributes[oid] = fake.attributes[oid] + [("added_later", 25, -1)]
    refuse(world, X.FACT_SCHEMA, fake)


@pytest.mark.parametrize("change", [
    lambda cols: cols.insert(0, cols.pop(1)),
    lambda cols: cols.__setitem__(next(i for i, c in enumerate(cols) if c[1] == 1700), (*cols[next(i for i, c in enumerate(cols) if c[1] == 1700)][:2], 655366)),
], ids=["moved", "numeric_modifier"])
def test_check_7_the_source_schema(world, change):
    fake = world.fake()
    oid = next(o for o, n, _k in fake.inventory if n == P13)
    change(fake.attributes[oid])
    refuse(world, X.FACT_SCHEMA, fake)


def test_a_modifier_changed_in_the_results_metadata_only(world):
    fake = world.fake()
    oid = next(o for o, n, _k in fake.inventory if n == P13)
    cols = list(fake.attributes[oid])
    i = next(i for i, c in enumerate(cols) if c[1] == 1700)
    cols[i] = (cols[i][0], cols[i][1], 655366)
    fake.fields_override[P13] = cols
    refusal, fake = refuse(world, X.RESULT_SCHEMA, fake)
    assert refusal.view == P13


@pytest.mark.parametrize("change", [
    lambda f: setattr(f, "provenance", []),
    lambda f: setattr(f, "provenance", f.provenance * 2),
    lambda f: f.provenance[0].update({"status": "stale"}),
    lambda f: f.provenance[0].update({"invocation_id": "00000000-0000-4000-8000-000000000002"}),
], ids=["no_row", "two_rows", "not_verified", "same_commit_other_invocation"])
def test_check_2_the_provenance(world, change):
    fake = world.fake()
    change(fake)
    refuse(world, X.FACT_PROVENANCE, fake)


def test_check_2_a_row_matching_two_accepted_entries():
    """The loader refuses two equal entries; the check refuses them too, on its
    own — reached in the protocol's order, and with one entry it passes (XIMPL-1-07)."""
    import dataclasses

    for builds, passes_ in ((None, True), (2, False)):
        fake = fw.Fake()
        contract = fake.contract if builds is None else dataclasses.replace(fake.contract, builds=fake.contract.builds * builds)
        s = S._Session(fake)
        S.check_transaction(s)
        if passes_:
            fact, build, _row = S.check_provenance(s, contract)
            assert fact.passed and build is contract.builds[0]
        else:
            with pytest.raises(Refused) as caught:
                S.check_provenance(s, contract)
            assert (caught.value.code, caught.value.cause) == (X.FACT_PROVENANCE, None), "the fact, not a statement's failure"
        assert [sql for sql, _ in fake.log] == [S.Q_TRANSACTION, S.Q_PROVENANCE]


def _one_row_more(f):
    extra = list(f.rows[P13][0])
    extra[col(f, P13, "carrier_name")] = "fixture_extra_row"
    f.rows[P13] = [*f.rows[P13], tuple(extra)]


@pytest.mark.parametrize("change", [
    lambda f: f.fingerprint_override.update({P13: "1" * 32}),
    _one_row_more,
], ids=["one_fingerprint_off", "one_count_off"])
def test_the_witness(world, change):
    fake = world.fake()
    change(fake)
    refusal, _ = refuse(world, X.WITNESS_MISMATCH, fake)
    assert refusal.view == P13


# --- the result ------------------------------------------------------------------------------------


@pytest.mark.parametrize("change", [
    lambda cols: cols.__setitem__(0, ("renamed", *cols[0][1:])),
    lambda cols: cols.__setitem__(0, (cols[0][0], 20, -1)),
    lambda cols: cols.insert(1, cols.pop(0)),
], ids=["renamed", "retyped", "moved"])
def test_the_results_description(world, change):
    fake = world.fake()
    oid = next(o for o, n, _k in fake.inventory if n == P13)
    cols = list(fake.attributes[oid])
    change(cols)
    fake.fields_override[P13] = cols
    refuse(world, X.RESULT_SCHEMA, fake)


def test_two_text_columns_swapped_between_the_raw_result_and_the_writer(world, monkeypatch):
    original = W.insert
    view = world.fake().contract.by_view()[P13]
    a, b = [i for i, c in enumerate(view.columns) if c.is_text][:2]

    def swapped(con, table, v, report, rows, **kw):
        if v.view == P13:
            rows = [tuple(r[b] if i == a else r[a] if i == b else x for i, x in enumerate(r)) for r in rows]
        return original(con, table, v, report, rows, **kw)

    monkeypatch.setattr(W, "insert", swapped)
    refusal, _ = refuse(world, X.ROUND_TRIP)
    assert refusal.view == P13


# --- the rows -------------------------------------------------------------------------------------


def test_a_count_over_max_rows_refuses_with_nothing_fetched_after_it(world):
    fake = world.fake()
    fake.count_override[P13] = fake.contract.by_view()[P13].max_rows + 1
    refusal, fake = refuse(world, X.SIZE_OVER, fake)
    assert fake.log[-1][0] == S.q_count(P13) and refusal.view == P13


def test_an_empty_view_refuses_and_one_declared_may_be_empty_passes_through_the_writer(world):
    fake = world.fake()
    fake.rows[SKUS] = []
    refuse(world, X.SIZE_EMPTY, fake)
    body = world.views_json()
    next(v for v in body["views"] if v["view"] == SKUS)["may_be_empty"] = True
    world.write_views(body)
    payloads = passes(world, fake, SKUS)
    assert json.loads(payloads[fake.contract.by_view()[SKUS].report][0])["rows"] == 0


@pytest.mark.parametrize("name", ["delivered_count", "carrier_name"], ids=["not_nullable", "grain"])
def test_a_null_where_not_nullable(world, name):
    fake = world.fake()
    set_cell(fake, P13, 0, name, None)
    refuse(world, X.NULL_REFUSED, fake)


def test_an_all_null_nullable_column_with_a_populated_grain_passes(world):
    fake = world.fake()
    for i in range(len(fake.rows[P13])):
        set_cell(fake, P13, i, "avg_delay_days_when_late", None)
    passes(world, fake, P13)


@pytest.mark.parametrize("value", [
    Decimal("0.12345"),
    Decimal("12345.1"),
    Decimal("NaN"),
    Decimal("Infinity"),
    Decimal("-Infinity"),
    Decimal("0." + "0" * 37 + "1"),
], ids=["fraction_beyond", "integer_beyond", "nan", "infinity", "minus_infinity", "digit_at_scale_38"])
def test_a_decimal_that_does_not_fit_refuses_before_any_binding(world, monkeypatch, value):
    monkeypatch.setattr(W, "insert", lambda *a, **k: pytest.fail("bound"))
    fake = world.fake()
    set_cell(fake, P13, 0, "on_time_rate", value)  # DECIMAL(8,4)
    refuse(world, X.DECIMAL_REFUSED, fake)


@pytest.mark.parametrize("value", [
    Decimal("9999.9999"),
    Decimal("-0.0000"),
    Decimal("0.00120000000000000000000000000000000000"),
], ids=["at_its_precision", "negative_zero", "trailing_zeros_only"])
def test_a_decimal_that_fits_passes_through_the_writer(world, value):
    fake = world.fake()
    set_cell(fake, P13, 0, "on_time_rate", value)
    passes(world, fake, P13)


def test_the_fit_writes_the_canonical_spelling():
    assert V.fit(Decimal("0.00123000000000000000000000000000000000"), 8, 5) == "0.00123"
    assert V.fit(Decimal("-0.0000"), 8, 4) == "0.0000"
    assert V.fit(Decimal("9999.9999"), 8, 4) == "9999.9999"


@pytest.mark.parametrize("value", [
    dt.datetime(2025, 3, 1, 10, 0),
    S.UNREPRESENTABLE,
], ids=["naive", "postgres_infinity"])
def test_an_instant_the_client_cannot_hold_refuses(world, value):
    fake = world.fake()
    set_cell(fake, SKUS, 0, "last_movement_at", value)
    refuse(world, X.INSTANT_REFUSED, fake)


def test_two_instants_with_the_same_wall_time_and_different_offsets_pass(world):
    fake = world.fake()
    set_cell(fake, SKUS, 0, "last_movement_at", dt.datetime(2025, 3, 1, 10, 0, 0, 123457, tzinfo=dt.timezone(dt.timedelta(hours=-3))))
    set_cell(fake, SKUS, 1, "last_movement_at", dt.datetime(2025, 3, 1, 10, 0, 0, 123457, tzinfo=dt.timezone.utc))
    passes(world, fake, SKUS)


def test_a_duplicated_grain_key(world):
    fake = world.fake()
    fake.rows[P13] = [fake.rows[P13][0], *fake.rows[P13]]
    refuse(world, X.GRAIN_REPEATED, fake)


@pytest.mark.parametrize("value", ["a\x00b", None], ids=["nul", "one_over"])
def test_a_text_that_does_not_fit(world, value):
    fake = world.fake()
    limit = fake.contract.by_view()[P13].column("carrier_name").max_length
    set_cell(fake, P13, 0, "carrier_name", value if value is not None else "ç" * (limit + 1))
    refuse(world, X.TEXT_REFUSED, fake)


def test_a_text_exactly_at_max_length_multibyte_passes(world):
    fake = world.fake()
    limit = fake.contract.by_view()[P13].column("carrier_name").max_length
    set_cell(fake, P13, 0, "carrier_name", "ç" * limit)
    passes(world, fake, P13)


def test_texts_json_must_escape_and_an_empty_text_pass_apart_from_null(world):
    fake = world.fake()
    view = fake.contract.by_view()[P13]
    limit = view.column("carrier_name").max_length
    hard = ('a"b\\c\nd\te🙂' + "x" * limit)[:limit]
    set_cell(fake, P13, 0, "carrier_name", hard)
    set_cell(fake, P13, 1, "service_level", "")
    payloads = passes(world, fake, P13)
    assert payloads[view.report]


# --- the write ------------------------------------------------------------------------------------


def test_m19_two_labels_swapped_in_the_parquet_between_write_and_retained_buffer(world, monkeypatch):
    original = W.copy_out
    view = world.fake().contract.by_report()["P01"]
    label = next(c.name for c in view.columns if c.is_text and c.name in view.grain)

    def m19(con, table, path):
        original(con, table, path)
        if table == "r_" + view.view:
            con.execute(f"CREATE TABLE m19 AS SELECT * FROM read_parquet('{path}')")
            a, b = [r[0] for r in con.execute(f'SELECT "{label}" FROM m19 LIMIT 2').fetchall()]
            con.execute(f'UPDATE m19 SET "{label}" = CASE WHEN "{label}" = ? THEN ? ELSE ? END WHERE "{label}" IN (?, ?)', [a, b, a, a, b])
            con.execute(f"COPY m19 TO '{path}' (FORMAT parquet)")

    monkeypatch.setattr(W, "copy_out", m19)
    refusal, _ = refuse(world, X.ROUND_TRIP)
    assert refusal.view == view.view


def test_a_writer_that_rounds_a_decimal(world, monkeypatch):
    original = W._cast
    monkeypatch.setattr(W, "_cast", lambda c, t, x: f"ROUND(CAST({x} AS {t}), 0)" if c.is_decimal else original(c, t, x))
    refuse(world, X.ROUND_TRIP)


def test_a_writer_that_drops_a_row(world, monkeypatch):
    original = W.insert
    monkeypatch.setattr(W, "insert", lambda con, table, v, report, rows, **kw: original(con, table, v, report, rows[:-1], **kw))
    refuse(world, X.ROUND_TRIP)


def test_the_retained_buffer_replaced_before_sealing(world, monkeypatch):
    monkeypatch.setattr(run, "hold", lambda view, totals, buffer: (totals, buffer + b"\0"))
    refuse(world, X.SEAL_TAMPERED)


def test_the_read_back_file_altered_after_the_read(world, monkeypatch):
    original = W.read_back

    def altered(con, view, report, path):
        rows = original(con, view, report, path)
        with open(path, "ab") as f:
            f.write(b"\0")
        return rows

    monkeypatch.setattr(W, "read_back", altered)
    refuse(world, X.READBACK_TAMPERED)


def test_accented_multi_column_grain_keys_in_different_orders_on_the_two_sides_pass(world, monkeypatch):
    fake = world.fake()
    for i, (carrier, warehouse) in enumerate([("Ávila", "Éden"), ("avila", "eden"), ("Çaçá", "Ôba")][: len(fake.rows[P13])]):
        set_cell(fake, P13, i, "carrier_name", carrier)
        set_cell(fake, P13, i, "warehouse_name", warehouse)
    original = W.insert
    monkeypatch.setattr(W, "insert", lambda con, table, v, report, rows, **kw: original(con, table, v, report, rows[::-1], **kw))
    passes(world, fake, P13)


# --- the metadata ---------------------------------------------------------------------------------


def _metadata(world, change):
    data = json.loads(world.metadata_raw)
    change(data)
    return world.fetch_metadata((json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def test_a_report_code_swapped_in_both_local_contracts(world):
    body = world.views_json()
    a, b = body["views"][0], body["views"][1]
    a["report"], b["report"] = b["report"], a["report"]
    world.write_views(body)
    refusal, fake = refuse(world, X.METADATA_MAPPING)
    assert fake.log == [], "refused before connecting"


@pytest.mark.parametrize("change, code", [
    (lambda d: d["questions"].pop("P05"), X.METADATA_MAPPING),
    (lambda d: d["questions"].update({"P17": {"view": "consumption.extra"}}), X.METADATA_MAPPING),
    (lambda d: d["questions"]["P02"].update({"view": d["questions"]["P01"]["view"]}), X.METADATA_MAPPING),
    (lambda d: next(iter(d["view_rules"].values()))["columns"].update(
        {k: {"role": "measure"} for k, v in next(iter(d["view_rules"].values()))["columns"].items() if v["role"] == "grain"}), X.METADATA_GRAIN),
    (lambda d: d.update({"format": 2}), X.METADATA_FORMAT),
    (lambda d: next(iter(d["view_rules"].values()))["columns"].update({"added": {"role": "measure"}}), X.METADATA_COLUMNS),
], ids=["missing_question", "extra_question", "two_codes_one_view", "grain_role_missing", "format_2", "column_added"])
def test_the_metadata(world, change, code):
    refusal, fake = refuse(world, code, metadata=_metadata(world, change))
    assert fake.log == []


def test_the_metadata_bound_to_the_pin_by_its_blob(world):
    import dataclasses
    from bi_como_codigo.exporter import metadata as M

    repo = world.base / "eng2"
    (repo / "docs").mkdir()
    (repo / "docs" / "pacote_de_metadados.json").write_bytes(world.metadata_raw)
    xw.git(repo, "init", "-q")
    xw.git(repo, "add", "-A")
    xw.git(repo, "commit", "-q", "-m", "package")
    pin = xw.git(repo, "rev-parse", "HEAD").strip()
    contract = dataclasses.replace(world.fake().contract, pin=pin)
    assert M.fetch(repo, contract).raw == world.metadata_raw
    (repo / "docs" / "pacote_de_metadados.json").write_bytes(world.metadata_raw + b" ")
    xw.git(repo, "commit", "-q", "-am", "another blob")
    other = xw.git(repo, "rev-parse", "HEAD").strip()
    with pytest.raises(Refused) as caught:
        M.fetch(repo, dataclasses.replace(contract, pin=other))
    assert caught.value.code == X.METADATA_BLOB
    with pytest.raises(Refused) as caught:
        M.fetch(repo, dataclasses.replace(contract, pin="0" * 40))
    assert caught.value.code == X.METADATA_PIN


# --- the declarations ------------------------------------------------------------------------------


def test_contract_json_edited_by_hand_refuses_before_connecting(world):
    path = world.root / "release" / "contract.json"
    path.write_bytes(path.read_bytes().replace(b'"nullable": false', b'"nullable": true', 1))
    _refusal, fake = refuse(world, X.CONTRACT_STALE)
    assert fake.log == []


def test_views_json_edited_in_a_generated_field_without_regenerating(world):
    body = world.views_json()
    body["views"][0]["version"] = 2
    world.write_views(body, regenerate=False)
    _refusal, fake = refuse(world, X.CONTRACT_STALE)
    assert fake.log == []


# --- the paths, end to end -------------------------------------------------------------------------


def test_a_leftover_run_directory_refuses_until_removed(world):
    (world.staging / "run-killed").mkdir()
    fake = world.fake()
    with pytest.raises(Refused) as caught:
        export(world, fake)
    assert caught.value.code == X.RUN_LEFTOVER and fake.log == []
    assert [p.name for p in world.staging.glob("run-*")] == ["run-killed"]
    (world.staging / "run-killed").rmdir()
    export(world, checked_only=True)


def test_an_existing_destination(world):
    world.out.mkdir()
    with pytest.raises(Refused) as caught:
        export(world)
    assert caught.value.code == X.PATH_EXISTS


@pytest.mark.parametrize("how", ["keyboard", "sigterm"])
def test_an_interrupt_mid_run_removes_the_run_directory(world, monkeypatch, how):
    original = W.write
    seen = []

    def interrupted(con, run_dir, view, report, rows):
        seen.append(run_dir)
        assert run_dir.is_dir() and pathlib.Path.cwd() == run_dir
        if how == "keyboard":
            raise KeyboardInterrupt
        os.kill(os.getpid(), signal.SIGTERM)
        return original(con, run_dir, view, report, rows)

    monkeypatch.setattr(W, "write", interrupted)
    expected = KeyboardInterrupt if how == "keyboard" else Refused
    with pytest.raises(expected) as caught:
        export(world)
    if how == "sigterm":
        assert caught.value.code == X.INTERRUPTED
    assert seen and not seen[0].exists() and not any(world.staging.glob("run-*"))
    assert pathlib.Path.cwd() != seen[0]


# --- the candidate ----------------------------------------------------------------------------------

import secrets  # noqa: E402

from bi_como_codigo import contract as C, release as REL  # noqa: E402


def seal_with(profiles, payloads, *, package_id=None, deks=None, ivs=None, totals=None):
    """A package sealed with `seal_report`, every input choosable — what
    `encrypt_package` refuses to make, so that `verify` is the one to catch it."""
    package_id = package_id or secrets.token_bytes(16)
    salts = {p.id: secrets.token_bytes(16) for p in profiles}
    keks = {p.id: e.derive_kek(p.password, salts[p.id], e.ITERATIONS) for p in profiles}
    files = {}
    for rid in sorted(payloads):
        t, parquet = payloads[rid]
        t = (totals or {}).get(rid, t)
        slots = [e.SlotInput(p.id, salts[p.id], e.ITERATIONS, keks[p.id]) for p in profiles if rid in p.reports]
        envelope = e.seal_report(package_id, rid, slots, (deks or {}).get(rid) or secrets.token_bytes(32),
                                 (ivs or {}).get(rid) or secrets.token_bytes(12), e.build_payload(t, parquet))
        files[e.file_name(rid, envelope)] = envelope
    return e._manifest_bytes(package_id, profiles, salts, files), files


def stand_in(world):
    package = world.root / "site" / "package"
    manifest = (package / "manifest.json").read_bytes()
    return manifest, {p.name: p.read_bytes() for p in package.glob("*.bice")}


def candidate_refused(world, monkeypatch, sealer, check):
    monkeypatch.setattr(run, "seal", sealer)
    refusal, _ = refuse(world, X.CANDIDATE_REFUSED)
    assert refusal.check == check, refusal


def test_a_clear_value_injected_into_an_included_file(world, monkeypatch):
    fake = world.fake()
    value = fake.rows[P13][0][col(fake, P13, "carrier_name")]
    index = world.root / "site" / "index.html"
    index.write_bytes(index.read_bytes() + value.encode("utf-8"))
    refusal, _ = refuse(world, X.CANDIDATE_REFUSED, fake)
    assert refusal.check == C.CLEAR_VALUE


def test_a_tampered_manifest(world, monkeypatch):
    def tampered(profiles, payloads):
        manifest, files = e.encrypt_package(profiles, payloads)
        import re
        first = re.search(rb'"size": ([0-9]+)', manifest)  # the file name binds the hash; the size is free
        return manifest[: first.start(1)] + str(int(first[1]) + 1).encode() + manifest[first.end(1):], files

    candidate_refused(world, monkeypatch, tampered, e.INTEGRITY_MISMATCH)


@pytest.mark.parametrize("which, check", [("deks", e.DEK_REUSED), ("ivs", e.IV_REUSED)])
def test_a_reused_key_or_iv(world, monkeypatch, which, check):
    same = secrets.token_bytes(32 if which == "deks" else 12)
    candidate_refused(world, monkeypatch, lambda profiles, payloads: seal_with(
        profiles, payloads, **{which: {"P01": same, "P02": same}}), check)


def test_mut15_mismatched_totals(world, monkeypatch):
    def mismatched(profiles, payloads):
        t = json.loads(payloads["P01"][0])
        name = next(iter(t["sums"]))
        value = t["sums"][name]
        t["sums"][name] = str(int(value) + 1) if "." not in value else value[:-1] + str((int(value[-1]) + 1) % 10)
        return seal_with(profiles, payloads, totals={"P01": json.dumps(t, separators=(",", ":")).encode("utf-8")})

    candidate_refused(world, monkeypatch, mismatched, C.TOTALS_SUMS)


def test_the_candidate_resealed_with_the_stand_ins_package_id(world, monkeypatch):
    live_id = e.validate_manifest(stand_in(world)[0]).package_id
    candidate_refused(world, monkeypatch, lambda profiles, payloads: seal_with(profiles, payloads, package_id=live_id), e.PACKAGE_ID_REUSED)


def test_a_fresh_id_with_a_dek_reused_from_the_stand_in(world, monkeypatch):
    manifest, files = stand_in(world)
    live = e.validate_manifest(manifest)
    dek = e._raw_deks(live, files, xw.PASSWORDS)[0]
    candidate_refused(world, monkeypatch, lambda profiles, payloads: seal_with(profiles, payloads, deks={"P05": dek}), e.DEK_REUSED)


def test_a_fresh_id_with_fresh_material_passes_against_the_stand_in(world):
    body, _ = export(world)
    live = body["candidate"]["verify"][1]["live"]
    assert live != "none" and len(live) == 64


# --- the collisions (N108) --------------------------------------------------------------------------


def _first_wide_decimal(fake):
    for view in fake.contract.views:
        for i, c in enumerate(view.columns):
            if c.is_decimal:
                for row in fake.rows[view.view]:
                    if row[i] is not None and abs(row[i]) >= 1000 and row[i] != row[i].to_integral_value():
                        return view, c, row[i]
    raise AssertionError("no wide decimal in the fixture")


def test_collisions_are_listed_approved_and_planted_values_never_printed(world):
    from bi_como_codigo.exporter import collisions

    fake = world.fake()
    set_cell(fake, P13, 0, "carrier_name", "Logística")  # equal to a committed profile label
    world.rewitness(fake, P13)
    text = fake.rows[P13][1][col(fake, P13, "warehouse_name")]
    _view, _c, number = _first_wide_decimal(fake)
    brazilian = C.spellings(f"{number:f}")[1]
    (world.root / "site" / "releases.md").write_text((world.root / "site" / "releases.md").read_text() + f"\n{text}\n")
    (world.root / "site" / "index.html").write_text((world.root / "site" / "index.html").read_text() + f"<!-- {brazilian} -->")
    xw.git(world.root, "commit", "-qam", "two public texts that hold report values")
    planted = fake.rows[SKUS][0][col(fake, SKUS, "sku_code")] if "sku_code" in fake.contract.by_view()[SKUS].names else \
        next(v for c, v in zip(fake.contract.by_view()[SKUS].columns, fake.rows[SKUS][0]) if c.is_text and len(v) >= 3)
    index = world.root / "site" / "index.html"
    committed_index = index.read_bytes()
    index.write_bytes(committed_index + planted.encode("utf-8"))  # in the working tree only: the candidate's copy
    profiles = world.root / "release" / "profiles.json"
    honest_profiles = profiles.read_bytes()
    label_value = next(v for c, v in zip(fake.contract.by_view()[SKUS].columns, fake.rows[SKUS][1]) if c.is_text and v != planted)
    profiles.write_bytes(honest_profiles.replace("Logística".encode("utf-8"), label_value.encode("utf-8")))  # a planted label

    def fresh():
        f = world.fake()
        f.rows = fake.rows
        return f

    lines = collisions.report(world.root, dict(world.environ), connect=lambda _s, _a: fresh(), fetch_metadata=world.fetch_metadata())
    joined = "\n".join(lines)
    assert "'Logística'" in joined and repr(text) in joined and repr(brazilian) in joined
    assert planted not in joined and label_value not in joined, "values planted in the candidate's copy are never printed"
    head = xw.git(world.root, "rev-parse", "HEAD").strip()
    assert lines[-1] == f"{len(lines) - 1} collision(s) at {head[:12]}" and len(lines) - 1 >= 3
    profiles.write_bytes(honest_profiles)

    # verify refuses the unapproved; approved, it refuses only what is planted
    public = world.root / "release" / "public_values.json"
    body = json.loads(public.read_bytes())
    body["values"] = [{"value": v, "reason": "a test: public on the site"} for v in ("Logística", text, f"{number:f}")]
    public.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n")
    refusal, _ = refuse(world, X.CANDIDATE_REFUSED, fresh())
    assert refusal.check == C.CLEAR_VALUE
    index.write_bytes(committed_index)
    profiles.write_bytes(honest_profiles.replace("Logística".encode("utf-8"), label_value.encode("utf-8")))
    refusal, _ = refuse(world, X.CANDIDATE_REFUSED, fresh())
    assert refusal.check == C.CLEAR_VALUE
    profiles.write_bytes(honest_profiles)
    body_out, _ = export(world, fresh())
    assert body_out["candidate"]["collisions_approved"] == {"used": [0, 1, 2], "unused": []}


def test_collisions_follow_the_gate_and_one_commit(world):
    """XIMPL-1-01: what the diagnostic prints is what the gate would search,
    against the bytes of one commit — not an uncommitted inclusion, not another
    spelling of a text that looks like a number, not a count too short to be
    searched; and an instant as the gate renders it, in UTC."""
    from bi_como_codigo.exporter import collisions

    fake = world.fake()
    looks_numeric = "12345.67"
    set_cell(fake, P13, 2, "warehouse_name", looks_numeric)  # a VARCHAR: the gate searches it as text only
    world.rewitness(fake, P13)
    hidden = fake.rows[P13][0][col(fake, P13, "carrier_name")]
    count = str(len(fake.rows[P13]))
    (world.root / "site" / "notes.txt").write_text(f"{hidden}\n")  # committed, outside the committed inclusion list
    releases = world.root / "site" / "releases.md"
    releases.write_text(releases.read_text() + f"\n- 12.345,67 · <p>{count}</p>\n")
    xw.git(world.root, "add", "-A")
    xw.git(world.root, "commit", "-qm", "public texts")
    include = world.root / "release" / "include.txt"
    include.write_text(include.read_text() + "site/notes.txt\n")  # an uncommitted inclusion

    def fresh():
        f = world.fake()
        f.rows = fake.rows
        return f

    lines = collisions.report(world.root, dict(world.environ), connect=lambda _s, _a: fresh(), fetch_metadata=world.fetch_metadata())
    joined = "\n".join(lines)
    assert hidden not in joined and "notes.txt" not in joined
    assert looks_numeric not in joined and "12.345,67" not in joined
    assert f"{count!r}" not in joined
    assert lines[-1].startswith("0 collision(s)")


def test_collisions_render_an_instant_as_the_gate_does(world):
    from bi_como_codigo.exporter import collisions
    import duckdb

    fake = world.fake()
    us = R.instant_us(fake.rows[SKUS][0][col(fake, SKUS, "last_movement_at")])
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    rendered = con.execute("SELECT CAST(make_timestamp(?::BIGINT)::TIMESTAMPTZ AS VARCHAR)", [us]).fetchone()[0]
    releases = world.root / "site" / "releases.md"
    releases.write_text(releases.read_text() + f"\n- {rendered}\n")
    xw.git(world.root, "commit", "-qam", "an instant on the site")
    lines = collisions.report(world.root, dict(world.environ), connect=lambda _s, _a: world.fake(), fetch_metadata=world.fetch_metadata())
    assert any(repr(rendered) in line and "last_movement_at" in line for line in lines), lines


def test_collisions_match_by_token_as_the_gate_does(world):
    """N116: `collisions` uses the gate's `contract.found`: a value glued inside
    a word of the site is not reported, and the same value standing alone is."""
    from bi_como_codigo.exporter import collisions

    text = world.fake().rows[P13][1][col(world.fake(), P13, "warehouse_name")]
    releases = world.root / "site" / "releases.md"
    releases.write_text(releases.read_text() + f"\n- x{text}x\n")
    xw.git(world.root, "commit", "-qam", "a value glued inside a word")
    lines = collisions.report(world.root, dict(world.environ), connect=lambda _s, _a: world.fake(), fetch_metadata=world.fetch_metadata())
    assert repr(text) not in "\n".join(lines), lines
    releases.write_text(releases.read_text() + f"\n- {text}\n")
    xw.git(world.root, "commit", "-qam", "the same value alone")
    lines = collisions.report(world.root, dict(world.environ), connect=lambda _s, _a: world.fake(), fetch_metadata=world.fetch_metadata())
    assert any(repr(text) in line and "warehouse_name" in line for line in lines), lines


def test_a_trusted_declaration_alone_changes_the_receipts_input_identity(world):
    first, _ = export(world)
    import shutil
    shutil.rmtree(world.out)
    media = world.root / "release" / "media_types.txt"
    media.write_text(media.read_text() + "# a comment: no deployed byte changes\n")
    second, _ = export(world)
    site = lambda b: [f for f in b["candidate"]["files"] if not f["path"].startswith("package/")]  # noqa: E731
    assert site(first) == site(second), "no deployed byte of the site changed; the package is sealed afresh each run"
    changed = {k for k in first["candidate"]["declarations"] if first["candidate"]["declarations"][k] != second["candidate"]["declarations"][k]}
    assert changed == {"release/media_types.txt"}


def test_a_declaration_edited_mid_run_does_not_reach_the_candidate_nor_the_receipt(world, monkeypatch):
    """XIMPL-1-09: the declarations are read once; the candidate is built from
    those bytes and the receipt records their digests."""
    import hashlib

    include = world.root / "release" / "include.txt"
    before = include.read_bytes()
    assert b"site/releases.md\n" in before
    original = R.freeze
    edited = []

    def freeze_and_edit(view, rows):
        if not edited:  # a field `release.build` uses: releases.md leaves the inclusion list
            include.write_bytes(before.replace(b"site/releases.md\n", b""))
            edited.append(1)
        return original(view, rows)

    monkeypatch.setattr(R, "freeze", freeze_and_edit)
    body, _ = export(world)
    assert edited and body["candidate"]["declarations"]["release/include.txt"] == hashlib.sha256(before).hexdigest()
    assert "site/releases.md" in body["candidate"]["included"], "the candidate was built from the bytes read at the start"


def test_an_exemption_no_value_uses_is_recorded_as_unused(world):
    public = world.root / "release" / "public_values.json"
    data = json.loads(public.read_bytes())
    data["values"] = [{"value": "fixture_never_a_value", "reason": "a test: an entry no report holds"}]
    public.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    body, _ = export(world)
    assert body["candidate"]["collisions_approved"] == {"used": [], "unused": [0]}



def test_the_witness_count_alone_off(world):
    """XIMPL-2-03: the witness's count one more, its fingerprint unchanged — only
    the count comparison can refuse it."""
    body = world.views_json()
    for entry in body["accepted_builds"][0]["witness"]:
        if entry["view"] == P13:
            entry["rows"] += 1
    world.write_views(body)
    refusal, _ = refuse(world, X.WITNESS_MISMATCH)
    assert refusal.view == P13


def _commit(world, files: dict[str, str], include: list[str]):
    for rel, text in files.items():
        (world.root / rel).parent.mkdir(parents=True, exist_ok=True)
        (world.root / rel).write_text(text)
    inc = world.root / "release" / "include.txt"
    inc.write_text(inc.read_text() + "".join(f"{line}\n" for line in include))
    xw.git(world.root, "add", "-A")
    xw.git(world.root, "commit", "-qm", "site files")


def test_an_uncommitted_file_name_never_reaches_the_receipt(world):
    """XIMPL-2-01: a file the candidate would include under a name not in Git is refused."""
    fake = world.fake()
    value = fake.rows[P13][0][col(fake, P13, "carrier_name")]
    _commit(world, {}, [f"site/{value}.md"])
    (world.root / "site" / f"{value}.md").write_text("")  # empty, so the gate's inspection of contents finds nothing
    refusal, _ = refuse(world, X.CANDIDATE_REFUSED, fake)
    assert refusal.check == "uncommitted_file"
    assert value not in "".join(p.name for p in world.base.rglob("*.json"))


def test_paths_that_sort_differently_as_strings_round_trip(world, monkeypatch):
    """XIMPL-2-04: `site/a/x.md` and `site/a-b.md` — the gate's order, not the strings'."""
    from bi_como_codigo.exporter import cli

    _commit(world, {"site/a/x.md": "", "site/a-b.md": ""}, ["site/a/x.md", "site/a-b.md"])
    body, fake = export(world)
    included = body["candidate"]["included"]
    assert included.index("site/a/x.md") < included.index("site/a-b.md")
    target = world.root / "evidence" / "20261124"
    monkeypatch.setattr(cli, "ROOT", world.root)
    assert cli.main(["evidence", str(world.out / "run.json"), str(target)], {}) == 0


def test_a_signal_while_cleaning_publishes_nothing(world, monkeypatch):
    """XIMPL-2-05: a SIGTERM noted during the cleaning ends the run as
    `interrupted`, before the result is published."""
    import signal as sig
    from bi_como_codigo.exporter import paths as P_

    original = P_.remove_tree
    monkeypatch.setattr(P_, "remove_tree", lambda path: (os.kill(os.getpid(), sig.SIGTERM), original(path)))
    refusal, _ = refuse(world, X.INTERRUPTED)
    assert refusal.check == "cleanup"


def test_one_spelling_of_two_values_lists_both_and_each_needs_its_approval(world):
    """XIMPL-2-06: VARCHAR `1.234` and BIGINT `1234` share the spelling `1.234`."""
    from bi_como_codigo.exporter import collisions

    fake = world.fake()
    set_cell(fake, P13, 0, "warehouse_name", "1.234")
    set_cell(fake, P13, 1, "delivered_count", 1234)
    world.rewitness(fake, P13)
    _commit(world, {"site/notes.md": "1.234\n"}, ["site/notes.md"])

    def fresh():
        f = world.fake()
        f.rows = fake.rows
        return f

    lines = collisions.report(world.root, dict(world.environ), connect=lambda _s, _a: fresh(), fetch_metadata=world.fetch_metadata())
    assert any("'1.234' as '1.234'" in line for line in lines) and any("'1234' as '1.234'" in line for line in lines), lines
    public = world.root / "release" / "public_values.json"
    for approved, passes_ in ((["1.234"], False), (["1.234", "1234"], True)):
        data = json.loads(public.read_bytes())
        data["values"] = [{"value": v, "reason": "a test"} for v in approved]
        public.write_text(json.dumps(data) + "\n")
        if passes_:
            body, _ = export(world, fresh())
            assert body["candidate"]["collisions_approved"] == {"used": [0, 1], "unused": []}
        else:
            refusal, _ = refuse(world, X.CANDIDATE_REFUSED, fresh())
            assert refusal.check == C.CLEAR_VALUE


def test_a_committed_symlink_is_not_public_content(world):
    """XIMPL-2-09: its blob is a target name; a regular file beside it still counts."""
    from bi_como_codigo.exporter import collisions

    fake = world.fake()
    target_value = fake.rows[P13][0][col(fake, P13, "carrier_name")]
    regular_value = fake.rows[P13][1][col(fake, P13, "carrier_name")]
    (world.root / "site" / "link.md").symlink_to(target_value)
    _commit(world, {"site/real.md": f"{regular_value}\n"}, ["site/link.md", "site/real.md"])
    (world.root / "site" / "link.md").unlink()  # the working tree need not hold it: the diagnostic reads the commit
    lines = collisions.report(world.root, dict(world.environ), connect=lambda _s, _a: world.fake(), fetch_metadata=world.fetch_metadata())
    joined = "\n".join(lines)
    assert repr(regular_value) in joined and target_value not in joined


def test_an_exemption_of_a_value_the_gate_never_searches_is_unused(world):
    """XIMPL-2-07: P13's row count has one digit: no needle, so its entry exempts nothing."""
    fake = world.fake()
    count = str(len(fake.rows[P13]))
    assert len(count) == 1
    public = world.root / "release" / "public_values.json"
    data = json.loads(public.read_bytes())
    data["values"] = [{"value": count, "reason": "a test: a one-digit count"}]
    public.write_text(json.dumps(data) + "\n")
    body, _ = export(world)
    assert body["candidate"]["collisions_approved"] == {"used": [], "unused": [0]}


def test_the_stand_in_comes_from_the_commit_resolved_once(world, monkeypatch):
    """XIMPL-2-08: HEAD moves to another valid package between the listing and
    the reads; the manifest, the envelopes and the receipt's digest are all the
    first commit's."""
    import hashlib
    import shutil

    manifest, files = stand_in(world)
    expected = hashlib.sha256(manifest + b"".join(files[k] for k in sorted(files))).hexdigest()
    original = run.committed_paths
    moved = []

    def and_move(root, commit):
        out = original(root, commit)
        if not moved:  # another valid package, committed after the commit was resolved
            declared = REL.profiles(world.root)
            k = C.load(world.root)[0]
            scratch = world.base / "scratch2"
            scratch.mkdir()
            rows = {v.view: fw.typed_rows(v, world.fixture["rows"][v.view]) for v in world.fake().contract.views}
            m2, f2 = e.encrypt_package(declared, xw.payloads_from(world.fake().contract, k, rows, scratch))
            package = world.root / "site" / "package"
            shutil.rmtree(package)
            package.mkdir()
            (package / "manifest.json").write_bytes(m2)
            for name, data in f2.items():
                (package / name).write_bytes(data)
            xw.git(world.root, "add", "-A")
            xw.git(world.root, "commit", "-qm", "another package")
            moved.append(1)
        return out

    monkeypatch.setattr(run, "committed_paths", and_move)
    body, _ = export(world)
    assert moved and body["candidate"]["verify"][1]["live"] == expected
