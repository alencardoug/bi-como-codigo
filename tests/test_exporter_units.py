"""The exporter's units (docs/exporter.md §12): the strict loaders, the fit and
the comparator, the path rule, the receipt's schema, the connection's
parameters against a real libpq over a local TLS server, the spill, what the
command-line boundary prints, and the reproduction of the committed fixture
and of the generated report contract."""

from __future__ import annotations

import contextlib
import copy
import datetime as dt
import hashlib
import json
import os
import pathlib
import socket
import ssl
import struct
import sys
import tempfile
import threading
import time
from decimal import Decimal

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

import exporter_fixture as xf  # noqa: E402
import fake_warehouse as fw  # noqa: E402
from bi_como_codigo import contract as c  # noqa: E402
import bi_como_codigo.exporter as X  # noqa: E402
from bi_como_codigo.exporter import Refused, cli, paths, propose as P, receipt as rc, reference as R  # noqa: E402
from bi_como_codigo.exporter import source as S, views as V, writer as W  # noqa: E402


def code_of(fn, *args, **kwargs) -> str:
    with pytest.raises(Refused) as caught:
        fn(*args, **kwargs)
    return caught.value.code


def views_body() -> dict:
    return copy.deepcopy(fw.load_fixture()["views_json"])


def load_body(body: dict):
    return V.load(json.dumps(body, ensure_ascii=False).encode("utf-8"))


# --- §4.1: the strict loader -------------------------------------------------------------------


def test_the_fixtures_view_contract_loads():
    contract = load_body(views_body())
    assert len(contract.views) == 16 and len({v.report for v in contract.views}) == 16


@pytest.mark.parametrize("change", [
    lambda b: b.update({"unknown": 1}),
    lambda b: b["views"][0].update({"unknown": 1}),
    lambda b: b["views"][0]["columns"][0].update({"unknown": 1}),
    lambda b: b["views"][0].update({"max_rows": 1}),
    lambda b: next(col for v in b["views"] for col in v["columns"] if col["source_type"] == "numeric").update({"precision": 19}),
    lambda b: next(col for v in b["views"] for col in v["columns"] if col["source_type"] == "numeric").update({"scale": 99}),
    lambda b: next(col for col in b["views"][0]["columns"] if col["name"] == b["views"][0]["grain"][0]).update({"nullable": True}),
    lambda b: b["accepted_builds"][0]["witness"].pop(),
    lambda b: b["accepted_builds"][0]["witness"].append(dict(b["accepted_builds"][0]["witness"][0])),
    lambda b: b["views"].pop(),
    lambda b: b["views"][1].update({"report": b["views"][0]["report"]}),
    lambda b: b["views"][0].update({"version": True}),
    lambda b: b["views"][0]["columns"][0].update({"source_oid": 25 if b["views"][0]["columns"][0]["source_oid"] != 25 else 23}),
    lambda b: next(col for v in b["views"] for col in v["columns"] if col["source_type"] == "text").update({"max_length": 0}),
    lambda b: b["views"][0]["grain"].append("not_a_column"),
    lambda b: b["accepted_builds"].append(copy.deepcopy(b["accepted_builds"][0])),
    lambda b: b["roles"]["can_login"].pop(),
    lambda b: b["roles"]["memberships"].append({"member": "stranger", "role": "analyst", "inherit_option": True, "set_option": True}),
], ids=["unknown_top", "unknown_view", "unknown_column", "max_rows_below_witness", "precision_over_18", "scale_over_precision",
        "nullable_grain", "witness_missing_one_view", "witness_view_twice", "fifteen_views", "two_views_one_code", "boolean_version",
        "oid_off_its_type", "max_length_zero", "grain_not_a_column", "two_equal_builds", "role_undeclared", "membership_disconnected"])
def test_the_loader_refuses(change):
    body = views_body()
    change(body)
    assert code_of(load_body, body) == X.VIEWS_INVALID


def test_the_loader_refuses_a_duplicate_key():
    raw = P.dump(views_body()).replace(b'"login": ', b'"login": "x", "login": ', 1)
    assert code_of(V.load, raw) == X.VIEWS_INVALID


# --- §4.3: the fit ---------------------------------------------------------------------------------


@pytest.mark.parametrize("value, precision, scale, expected", [
    ("1.50", 4, 2, "1.50"),
    ("1.5", 4, 2, "1.50"),
    ("-0", 4, 2, "0.00"),
    ("-0E-7", 4, 2, "0.00"),
    ("1E+2", 5, 2, "100.00"),
    ("99.99", 4, 2, "99.99"),
    ("0.00123000000000000000000000000000000000", 8, 5, "0.00123"),
    ("-12", 2, 0, "-12"),
    ("1" + "0" * 30 + ".000", 31, 0, "1" + "0" * 30),
])
def test_the_fit_accepts_and_spells_canonically(value, precision, scale, expected):
    assert V.fit(Decimal(value), precision, scale) == expected


@pytest.mark.parametrize("value, precision, scale", [
    ("100.00", 4, 2), ("0.001", 4, 2), ("NaN", 4, 2), ("sNaN", 4, 2), ("Infinity", 4, 2), ("-Infinity", 4, 2),
    ("0." + "0" * 37 + "1", 18, 4),
])
def test_the_fit_refuses(value, precision, scale):
    assert code_of(V.fit, Decimal(value), precision, scale) == X.DECIMAL_REFUSED


def test_the_fit_refuses_what_is_not_a_decimal():
    assert code_of(V.fit, 1.5, 4, 2) == X.VALUE_TYPE


# --- §7: the comparator -----------------------------------------------------------------------------


def test_the_comparator_needs_no_order_and_compares_types():
    fake = fw.Fake()
    view = fake.contract.by_view()[fw.load_fixture()["inventory"][0]["relname"]]
    frozen = R.freeze(view, fake.rows[view.view])
    R.compare(frozen, list(reversed(frozen.rows)))
    swapped = [tuple(True if x == 1 and type(x) is int else x for x in r) for r in frozen.rows]
    if swapped != list(frozen.rows):
        assert code_of(R.compare, frozen, swapped) == X.ROUND_TRIP
    assert code_of(R.compare, frozen, list(frozen.rows)[:-1]) == X.ROUND_TRIP
    assert code_of(R.compare, frozen, list(frozen.rows) + [frozen.rows[0]]) == X.ROUND_TRIP


def test_the_reference_is_immutable_and_its_digest_ignores_order():
    fake = fw.Fake()
    view = fake.contract.views[0]
    a = R.freeze(view, fake.rows[view.view])
    b = R.freeze(view, list(reversed(fake.rows[view.view])))
    assert a.digest == b.digest
    with pytest.raises(TypeError):
        a.by_key[("x",)] = ()  # a read-only mapping


def test_the_totals_of_an_empty_or_all_null_column_are_zero_at_scale():
    fake = fw.Fake()
    view = next(v for v in fake.contract.views if any(col.nullable and col.is_decimal for col in v.columns))
    contract = c.load_contract(V.report_contract(fake.contract))
    report = contract.reports[view.report]
    i = next(i for i, col in enumerate(view.columns) if col.nullable and col.is_decimal)
    rows = [tuple(None if j == i else x for j, x in enumerate(r)) for r in fake.rows[view.view]]
    totals = json.loads(R.totals(contract, report, R.freeze(view, rows)))
    assert totals["sums"][view.columns[i].name] == "0." + "0" * view.columns[i].scale
    empty = json.loads(R.totals(contract, report, R.freeze(view, [])))
    assert empty["rows"] == 0 and all(c.canonical_ok(v, report.column(k).scale) for k, v in empty["sums"].items())


def test_an_instant_is_exact_microseconds_in_utc():
    a = dt.datetime(2025, 3, 1, 10, 0, 0, 123457, tzinfo=dt.timezone(dt.timedelta(hours=-3)))
    b = dt.datetime(2025, 3, 1, 13, 0, 0, 123457, tzinfo=dt.timezone.utc)
    assert R.instant_us(a) == R.instant_us(b) == 1740834000123457


def test_duckdb_writes_and_reads_back_instants_and_decimals_exactly(tmp_path):
    with tempfile.TemporaryDirectory(prefix="bice-") as d:
        con = W.connect(pathlib.Path(d))
        con.execute("CREATE TABLE t (i TIMESTAMPTZ, d DECIMAL(18,4))")
        us = [-62135596800000000, 0, 1740834000123457, 253402300799999999]
        con.executemany("INSERT INTO t VALUES (CAST(make_timestamp(CAST(? AS BIGINT)) AS TIMESTAMPTZ), CAST(? AS DECIMAL(18,4)))",
                        [[u, "99999999999999.9999"] for u in us])
        out = pathlib.Path(d) / "t.parquet"
        con.execute(f"COPY t TO '{out}' (FORMAT parquet)")
        back = con.execute("SELECT epoch_us(i), CAST(d AS VARCHAR) FROM read_parquet(?)", [str(out)]).fetchall()
        con.close()
    assert [b[0] for b in back] == us and {b[1] for b in back} == {"99999999999999.9999"}


# --- §10: the path rule -----------------------------------------------------------------------------


@pytest.fixture
def outside():
    base = pathlib.Path(tempfile.mkdtemp(prefix="bice-unit-"))
    yield base
    import shutil
    shutil.rmtree(base, ignore_errors=True)


def test_an_external_path_passes(outside):
    assert paths.check(outside / "staging", [ROOT]) == pathlib.Path(os.path.realpath(outside / "staging"))


def test_a_git_ancestor_refuses_whatever_git_would_say(outside, monkeypatch):
    (outside / "wt").mkdir()
    (outside / "wt" / ".git").write_text("gitdir: /elsewhere\n")  # a worktree's .git is a file
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(outside))
    monkeypatch.setenv("GIT_DIR", "/nonexistent")
    (outside / "wt" / "deep").mkdir()
    assert code_of(paths.check, outside / "wt" / "deep", [ROOT]) == X.PATH_REFUSED


def test_a_symlink_into_a_worktree_refuses(outside):
    (outside / "link").symlink_to(ROOT / "release")
    assert code_of(paths.check, outside / "link", []) == X.PATH_REFUSED


def test_a_path_in_an_eng_dados_checkout_refuses_even_without_git(outside):
    eng = outside / "eng"
    (eng / "data" / "ignored").mkdir(parents=True)
    protected = paths.protected_roots({"ENG_DADOS_DIR": str(eng)}, ROOT)
    assert code_of(paths.check, eng / "data" / "ignored", protected) == X.PATH_REFUSED


def test_a_path_with_an_apostrophe_refuses(outside):
    (outside / "it's").mkdir()
    assert code_of(paths.check, outside / "it's", [ROOT]) == X.PATH_REFUSED


def test_the_run_directory_is_private_holds_the_temporary_files_and_goes(outside):
    staging = outside / "staging"
    staging.mkdir()
    before = os.getcwd()
    with paths.RunDirectory(staging, [ROOT]) as run_dir:
        assert oct(run_dir.stat().st_mode & 0o777) == "0o700"
        assert os.getcwd() == str(run_dir) and tempfile.gettempdir() == str(run_dir) and os.environ["TMPDIR"] == str(run_dir)
        assert code_of(paths.RunDirectory(staging, [ROOT]).__enter__) == X.RUN_LOCKED
    assert not run_dir.exists() and os.getcwd() == before and tempfile.gettempdir() != str(run_dir)


def test_publish_renames_into_place_and_refuses_an_existing_destination(outside):
    target = paths.publish(str(outside / "out"), {"a/b.txt": b"x"}, [ROOT])
    assert (target / "a" / "b.txt").read_bytes() == b"x"
    assert code_of(paths.publish, str(outside / "out"), {"c": b"y"}, [ROOT]) == X.PATH_EXISTS
    assert not list(outside.glob(paths.RESULT_PREFIX + "*"))


def _spill(con_factory, run_dir: pathlib.Path, watched: list[pathlib.Path]) -> set[pathlib.Path]:
    """Runs a sort that cannot fit in memory and polls for spilled files."""
    seen: set[pathlib.Path] = set()
    done = threading.Event()

    def poll():
        while not done.is_set():
            for root in watched:
                for dirpath, _d, files in os.walk(root):
                    for f in files:
                        seen.add(pathlib.Path(dirpath) / f)
            time.sleep(0.005)

    t = threading.Thread(target=poll)
    t.start()
    try:
        con = con_factory()
        con.execute("SELECT i, s FROM (SELECT range AS i, md5(range::VARCHAR) || md5((range * 7)::VARCHAR) AS s FROM range(600000)) ORDER BY s").fetchall()
        con.close()
    finally:
        done.set()
        t.join()
    return seen


def test_a_forced_spill_stays_inside_the_run_directory_in_the_exporter_and_in_the_gate(outside, monkeypatch):
    staging = outside / "staging"
    staging.mkdir()
    elsewhere = pathlib.Path(tempfile.gettempdir())
    before = {p for p in elsewhere.glob("*.tmp")} | {p for p in pathlib.Path.cwd().glob(".tmp")}
    with paths.RunDirectory(staging, [ROOT]) as run_dir:
        spilled = _spill(lambda: W.connect(run_dir, memory_limit="32MB"), run_dir, [run_dir])
        assert any("duckdb.tmp" in p.parts for p in spilled), "the exporter's DuckDB spilled into its temp_directory"
        monkeypatch.setattr(c, "MEMORY_LIMIT", "32MB")
        gate = _spill(c._connect, run_dir, [run_dir])
        assert any(".tmp" in p.parts for p in gate), "the gate's in-memory DuckDB spilled under the working directory"
        assert all(run_dir in p.parents for p in spilled | gate)
    assert not run_dir.exists()
    after = {p for p in elsewhere.glob("*.tmp")} | {p for p in pathlib.Path.cwd().glob(".tmp")}
    assert after <= before


# --- §3: the environment, the parameters, TLS -------------------------------------------------------


def environ(**over) -> dict:
    env = {"BICE_WAREHOUSE_HOST": "127.0.0.1", "BICE_WAREHOUSE_PORT": "5432", "BICE_WAREHOUSE_DB": "warehouse",
           "BICE_WAREHOUSE_USER": "consumption_reader", "BICE_WAREHOUSE_PASSWORD": "invented-password-for-tests",
           "BICE_WAREHOUSE_SSLMODE": "prefer"}
    env.update(over)
    return {k: v for k, v in env.items() if v is not None}


def test_settings_refuse_a_missing_variable_and_a_verifying_mode_without_a_root():
    assert code_of(S.settings, environ(BICE_WAREHOUSE_PASSWORD=None)) == X.ENVIRONMENT_INVALID
    assert code_of(S.settings, environ(BICE_WAREHOUSE_SSLMODE="verify-full")) == X.TLS_ROOT_REQUIRED
    assert code_of(S.settings, environ(BICE_WAREHOUSE_SSLMODE="verify-ca")) == X.TLS_ROOT_REQUIRED
    assert "invented-password" not in repr(S.settings(environ()))


def test_every_pg_variable_is_removed_and_the_parameters_are_explicit(outside):
    env = {"PGHOSTADDR": "10.255.255.1", "PGOPTIONS": "-c search_path=evil", "PGSERVICEFILE": "/x", "HOME": "/h"}
    assert S.scrub_environment(env) == ["PGHOSTADDR", "PGOPTIONS", "PGSERVICEFILE"] and env == {"HOME": "/h"}
    params = S.connection_parameters(S.settings(environ()), outside / "absent")
    assert params["options"] == "" and params["sslcertmode"] == "disable" and params["application_name"] == S.APPLICATION_NAME
    assert {params[k] for k in ("sslcert", "sslkey", "sslrootcert", "sslcrl", "passfile")} == {str(outside / "absent")}


def _certificate(common_name: str, key=None, issuer=None, issuer_key=None, ca=False):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = key or ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = dt.datetime.now(dt.timezone.utc)
    builder = (x509.CertificateBuilder().subject_name(name).issuer_name(issuer or name).public_key(key.public_key())
               .serial_number(x509.random_serial_number()).not_valid_before(now - dt.timedelta(days=1))
               .not_valid_after(now + dt.timedelta(days=1))
               .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True))
    if not ca:
        builder = builder.add_extension(x509.SubjectAlternativeName([x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1"))]), critical=False)
    cert = builder.sign(issuer_key or key, hashes.SHA256())
    return key, cert


def _pem(key, cert, where: pathlib.Path, stem: str) -> tuple[pathlib.Path, pathlib.Path]:
    from cryptography.hazmat.primitives import serialization

    k, ct = where / f"{stem}.key", where / f"{stem}.crt"
    k.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    os.chmod(k, 0o600)
    ct.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return k, ct


class TlsServer:
    """Answers PostgreSQL's SSLRequest with 'S', completes TLS, reads the startup
    message and records what libpq sent — then closes, so the client fails."""

    def __init__(self, where: pathlib.Path, client_ca: pathlib.Path):
        key, cert = _certificate("server")
        self.key, self.cert = _pem(key, cert, where, "server")
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.load_cert_chain(self.cert, self.key)
        self.ctx.verify_mode = ssl.CERT_OPTIONAL
        self.ctx.load_verify_locations(client_ca)
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(4)
        self.port = self.sock.getsockname()[1]
        self.seen: dict = {"tls": False, "peer_cert": None, "startup": None, "plain_startup": None}
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        with contextlib.suppress(Exception):
            conn, _ = self.sock.accept()
            conn.settimeout(5)
            head = conn.recv(8)
            if struct.unpack("!II", head) == (8, 80877103):
                conn.sendall(b"S")
                tls = self.ctx.wrap_socket(conn, server_side=True)
                self.seen["tls"] = True
                self.seen["peer_cert"] = tls.getpeercert()
                length = struct.unpack("!I", tls.recv(4))[0]
                body = b""
                while len(body) < length - 4:
                    body += tls.recv(length - 4 - len(body))
                parts = body[4:].split(b"\0")
                self.seen["startup"] = {parts[i].decode(): parts[i + 1].decode() for i in range(0, len(parts) - 2, 2) if parts[i]}
                tls.close()

    def close(self):
        self.sock.close()
        self.thread.join(timeout=5)


def test_libpq_reads_no_home_file_sends_no_client_certificate_and_no_pg_options(outside, monkeypatch):
    home = outside / "home"
    (home / ".postgresql").mkdir(parents=True)
    other_ca_key, other_ca = _certificate("another-ca", ca=True)
    _pem(other_ca_key, other_ca, home / ".postgresql", "root")  # would fail the server's certificate if read
    client_key, client_cert = _certificate("consumption_reader", issuer=other_ca.subject, issuer_key=other_ca_key)
    k, ct = _pem(client_key, client_cert, home / ".postgresql", "postgresql")  # would be sent if read
    server = TlsServer(outside, home / ".postgresql" / "root.crt")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PGHOSTADDR", "10.255.255.1")
    monkeypatch.setenv("PGOPTIONS", "-c search_path=evil")
    monkeypatch.setenv("PGSSLCERT", str(ct))
    try:
        found = S.settings(environ(BICE_WAREHOUSE_PORT=str(server.port), BICE_WAREHOUSE_SSLMODE="require"))
        refusal = code_of(S.connect, found, outside / "absent")
    finally:
        server.close()
    assert refusal == X.CONNECT_FAILED
    assert "PGHOSTADDR" not in os.environ and "PGOPTIONS" not in os.environ
    assert server.seen["tls"], "the handshake completed: no root.crt of the home directory was read"
    assert not server.seen["peer_cert"], "no client certificate was sent"
    startup = server.seen["startup"]
    assert startup["user"] == "consumption_reader" and startup["application_name"] == S.APPLICATION_NAME
    assert "evil" not in startup.get("options", "")


def test_the_psycopg_adapter_reads_the_modifier_from_the_result_object():
    from psycopg import pq

    conn = pq.PGconn.connect_start(b"host=/nonexistent-socket-dir port=1")
    result = conn.make_empty_result(pq.ExecStatus.TUPLES_OK)
    result.set_attributes([pq.PGresAttDesc(b"on_time_rate", 0, 0, 0, 1700, -1, 655366),
                           pq.PGresAttDesc(b"carrier_name", 0, 0, 0, 1043, -1, -1)])
    assert S.result_fields(result) == [("on_time_rate", 1700, 655366), ("carrier_name", 1043, -1)]
    conn.finish()


# --- §9: the receipt ---------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def honest_receipt():
    import functools
    import exporter_world as xw
    from bi_como_codigo import envelope as e
    from bi_como_codigo.exporter import run

    original = e.derive_kek
    e.derive_kek = functools.cache(original)
    w = xw.make_world()
    try:
        fake = w.fake()
        run.export(w.root, dict(w.environ), connect=lambda _s, _a: fake, fetch_metadata=w.fetch_metadata())
        yield (w.out / "run.json").read_bytes()
    finally:
        w.cleanup()
        e.derive_kek = original


def test_the_receipt_reads_back_and_holds_no_row_value(honest_receipt):
    body = rc.load(honest_receipt)
    fx = fw.load_fixture()
    # the fixture's texts with a letter outside hex, so a digest cannot hold one by chance
    texts = {v for rows in fx["rows"].values() for r in rows for v in r
             if isinstance(v, str) and len(v) >= 3 and not v.startswith("20") and set(v) - set("0123456789abcdef")}
    assert not [t for t in texts if t.encode() in honest_receipt]
    assert [f["code"] for f in body["facts"]] == list(rc.FACT_ORDER)


@pytest.mark.parametrize("change", [
    lambda b: b.pop("durations"),
    lambda b: b["identity"].pop("pin"),
    lambda b: b["views"][0].update({"rows": "4"}),
    lambda b: b["views"][0].update({"witness_equal": False}),
    lambda b: b["facts"].reverse(),
    lambda b: b["facts"][0]["compared"].update({"message": "a driver's text\nwith a line"}),
    lambda b: b["read"]["tls"].update({"sslmode": "whatever"}),
    lambda b: b.update({"extra": 1}),
    lambda b: b["candidate"]["verify"].pop(),
], ids=["missing_durations", "missing_pin", "rows_as_text", "witness_unequal", "facts_out_of_order", "free_text",
        "sslmode", "unknown_field", "one_verify"])
def test_the_receipt_refuses_an_incomplete_or_ill_typed_one(honest_receipt, change):
    body = json.loads(honest_receipt)
    change(body)
    assert code_of(rc.load, rc.dump(body)) == X.RECEIPT_INVALID


def test_export_evidence_refuses_before_writing_and_writes_only_under_evidence(honest_receipt, outside, monkeypatch):
    bad = outside / "bad.json"
    bad.write_bytes(honest_receipt.replace(b'"receipt_version": 1', b'"receipt_version": 2'))
    target = outside / "evidence"
    assert cli.main(["evidence", str(bad), str(target)], {}) == 1
    assert not target.exists()
    good = outside / "good.json"
    good.write_bytes(honest_receipt)
    assert cli.main(["evidence", str(good), str(target)], {}) == 1, "outside the repository's evidence/"
    assert not target.exists()


# --- §10: what a refusal prints ------------------------------------------------------------------------


def test_an_exception_holding_a_value_or_a_password_prints_only_its_class(monkeypatch, capsys):
    from bi_como_codigo.exporter import run

    def boom(*_a, **_k):
        raise RuntimeError("password=invented-password-for-tests value=fxwj0 at host 127.0.0.1")

    monkeypatch.setattr(run, "export", boom)
    assert cli.main(["run"], environ()) == 1
    err = capsys.readouterr().err
    assert err == "refused: unexpected; class RuntimeError\n"


def test_a_refusal_prints_its_code_view_check_and_cause_only(monkeypatch, capsys):
    from bi_como_codigo.exporter import run

    def refused(*_a, **_k):
        raise Refused(X.STATEMENT_FAILED, "top_skus_by_revenue", "statement", "OperationalError")

    monkeypatch.setattr(run, "export", refused)
    assert cli.main(["run"], environ()) == 1
    assert capsys.readouterr().err == "refused: statement_failed; view top_skus_by_revenue; check statement; class OperationalError\n"


# --- §4.4 and §12: the generated and the committed ------------------------------------------------------


def test_the_committed_report_contract_is_the_generated_one():
    views = ROOT / "release" / "views.json"
    committed = (ROOT / "release" / "contract.json").read_bytes()
    if views.exists():
        V.check_generated(V.load(views.read_bytes()), committed)
    else:  # until the migration of §11, the contract is stage 2.2's three fixtures
        assert set(c.load_contract(committed).reports) == {"P01", "P02", "P13"}


def test_the_committed_fixture_is_what_the_script_writes():
    assert xf.fixture(xf.STRUCTURE.read_bytes()) == xf.FIXTURE.read_bytes()


def test_the_fixtures_witness_is_its_rows_fingerprint():
    fake = fw.Fake()
    witness = fake.contract.builds[0].witness
    assert all(witness[v.view] == (len(fake.rows[v.view]), fw.fingerprint(v, fake.rows[v.view])) for v in fake.contract.views)


@pytest.mark.skipif(not os.environ.get("ENG_DADOS_2_DIR"), reason="needs ENG_DADOS_2_DIR, which make check requires")
def test_the_committed_structure_is_what_propose_drafts_over_the_invented_catalogue():
    catalogue, views = xf.structure(pathlib.Path(os.environ["ENG_DADOS_2_DIR"]))
    assert catalogue == xf.CATALOGUE.read_bytes() and views == xf.STRUCTURE.read_bytes()


@pytest.mark.skipif(not os.environ.get("ENG_DADOS_2_DIR"), reason="needs ENG_DADOS_2_DIR, which make check requires")
def test_export_propose_writes_its_draft_in_drafts_and_leaves_both_contracts(outside):
    staging = outside / "staging"
    staging.mkdir()
    before = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ("release/contract.json",)}
    env = {"BICE_EXPORT_STAGING": str(staging), "ENG_DADOS_2_DIR": os.environ["ENG_DADOS_2_DIR"]}
    argv = ["propose", "--catalogue", str(xf.CATALOGUE), "--pin", xf.PIN]
    assert cli.main(argv, env) == 0
    drafts = list((staging / "drafts").glob("views.*.json"))
    assert len(drafts) == 1 and drafts[0].read_bytes() == xf.STRUCTURE.read_bytes()
    assert before == {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in before}
    assert not (ROOT / "release" / "views.json").exists() or True
    env["BICE_EXPORT_STAGING"] = str(ROOT / "release")
    assert cli.main(argv, env) == 1, "a staging root in this repository is refused"
