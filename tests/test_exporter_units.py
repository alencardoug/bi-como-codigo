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


def _spilled(con) -> list[pathlib.Path]:
    """DuckDB's own list of its temporary files, while a temporary table larger
    than the memory limit holds them: deterministic, no polling (XIMPL-1-12)."""
    con.execute("CREATE TEMP TABLE big AS SELECT range AS i, md5(range::VARCHAR) || md5((range * 7)::VARCHAR) AS s FROM range(1500000)")
    return [pathlib.Path(os.path.realpath(p)) for (p,) in con.execute("SELECT path FROM duckdb_temporary_files()").fetchall()]


def test_a_forced_spill_stays_inside_the_run_directory_in_the_exporter_and_in_the_gate(outside, monkeypatch):
    staging = outside / "staging"
    staging.mkdir()
    with paths.RunDirectory(staging, [ROOT]) as run_dir:
        exporter = W.connect(run_dir, memory_limit="32MB")
        spilled = _spilled(exporter)
        assert spilled and all(run_dir / "duckdb.tmp" in p.parents for p in spilled), spilled
        monkeypatch.setattr(c, "MEMORY_LIMIT", "32MB")
        gate = c._connect()  # the gate's own connection: in memory, spilling under the working directory
        gate_spilled = _spilled(gate)
        assert gate_spilled and all(run_dir / ".tmp" in p.parents for p in gate_spilled), gate_spilled
        assert all(p.exists() for p in spilled + gate_spilled)
        exporter.close()
        gate.close()
    assert not run_dir.exists() and not any(p.exists() for p in spilled + gate_spilled)


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

    @staticmethod
    def _exactly(sock, n: int) -> bytes:
        """`n` bytes, however the stream splits them; EOF first is an error (XIMPL-1-12)."""
        out = b""
        while len(out) < n:
            chunk = sock.recv(n - len(out))
            if not chunk:
                raise EOFError
            out += chunk
        return out

    def _serve(self):
        with contextlib.suppress(Exception):
            conn, _ = self.sock.accept()
            conn.settimeout(5)
            head = self._exactly(conn, 8)
            if struct.unpack("!II", head) == (8, 80877103):
                conn.sendall(b"S")
                tls = self.ctx.wrap_socket(conn, server_side=True)
                self.seen["tls"] = True
                self.seen["peer_cert"] = tls.getpeercert()
                length = struct.unpack("!I", self._exactly(tls, 4))[0]
                body = self._exactly(tls, length - 4)
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


def test_relative_tls_files_are_the_ones_named_before_the_run_changes_directory(outside, monkeypatch):
    """XIMPL-1-10: a root certificate and a CRL named relative to the caller
    verify the server after the run's change of directory."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization

    certs = outside / "certs"
    certs.mkdir()
    key, cert = _certificate("server")
    k, ct = _pem(key, cert, certs, "server")
    now = dt.datetime.now(dt.timezone.utc)
    crl = (x509.CertificateRevocationListBuilder().issuer_name(cert.subject).last_update(now - dt.timedelta(days=1))
           .next_update(now + dt.timedelta(days=1)).sign(key, hashes.SHA256()))
    (certs / "root.crl").write_bytes(crl.public_bytes(serialization.Encoding.PEM))
    client_ca_key, client_ca = _certificate("client-ca", ca=True)
    _pem(client_ca_key, client_ca, certs, "client-ca")

    class Server(TlsServer):
        def __init__(self):
            self.key, self.cert = k, ct
            self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ctx.load_cert_chain(ct, k)
            self.sock = socket.socket()
            self.sock.bind(("127.0.0.1", 0))
            self.sock.listen(4)
            self.port = self.sock.getsockname()[1]
            self.seen = {"tls": False, "peer_cert": None, "startup": None}
            self.thread = threading.Thread(target=self._serve, daemon=True)
            self.thread.start()

    server = Server()
    monkeypatch.setenv("HOME", str(outside / "nohome"))
    monkeypatch.chdir(outside)
    try:
        found = S.settings(environ(BICE_WAREHOUSE_PORT=str(server.port), BICE_WAREHOUSE_SSLMODE="verify-ca",
                                   BICE_WAREHOUSE_SSLROOTCERT="certs/server.crt", BICE_WAREHOUSE_SSLCRL="certs/root.crl"))
        elsewhere = outside / "run"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)  # as the run does before connecting
        assert code_of(S.connect, found, elsewhere / "absent", environ={}) == X.CONNECT_FAILED
    finally:
        server.close()
    assert server.seen["tls"] and server.seen["startup"] is not None, "the root and the CRL named were read: the handshake verified"


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
def honest():
    """An honest receipt, and the repository it was rehearsed in."""
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
        yield (w.out / "run.json").read_bytes(), w.root
    finally:
        w.cleanup()
        e.derive_kek = original


@pytest.fixture(scope="module")
def honest_receipt(honest):
    return honest[0]


def fixture_contract() -> V.ViewContract:
    return V.load(fw.contract_bytes(fw.load_fixture()))


def test_the_receipt_reads_back_and_holds_no_row_value(honest_receipt):
    body = rc.load(honest_receipt, fixture_contract())
    fx = fw.load_fixture()
    contract = fixture_contract()
    # the fixture's texts — of text columns — with a letter outside hex, so a digest cannot hold one by chance
    texts = {r[i] for v in contract.views for r in fx["rows"][v.view] for i, col in enumerate(v.columns)
             if col.is_text and isinstance(r[i], str) and len(r[i]) >= 3 and set(r[i]) - set("0123456789abcdef")}
    assert texts
    assert not [t for t in texts if t.encode() in honest_receipt]
    assert [f["code"] for f in body["facts"]] == list(rc.FACT_ORDER)
    assert body["read"]["collation"]["version"] == "unavailable"  # N111: the fixture's build declares none


MARKER = "fx_private_marker_7731"  # an invented value standing for a row's


def _first_envelope_twice(b):
    b["envelopes"] = [b["envelopes"][0]] * 16


@pytest.mark.parametrize("change", [
    lambda b: b.pop("durations"),
    lambda b: b["identity"].pop("pin"),
    lambda b: b["identity"].update({"pin": "0" * 40}),
    lambda b: b["views"][0].update({"rows": "4"}),
    lambda b: b["views"][0].update({"rows": b["views"][0]["rows"] + 1}),
    lambda b: b["views"][0].update({"witness_equal": False}),
    lambda b: b["views"][0].update({"fingerprint": "0" * 32}),
    lambda b: b["facts"].reverse(),
    lambda b: b["facts"][0]["compared"].update({"message": MARKER}),
    lambda b: b["facts"][3]["compared"]["can_login"].update({MARKER: True}),
    lambda b: b["facts"][6]["compared"]["views"][next(iter(b["facts"][6]["compared"]["views"]))][0].__setitem__(0, MARKER),
    lambda b: b["read"]["policy"].update({"TimeZone": MARKER}),
    lambda b: b["read"]["collation"].update({"datcollate": MARKER}),
    lambda b: b["read"]["collation"].update({"version": "verified"}),
    lambda b: b["read"].update({"metadata_provenance": {"note": MARKER}}),
    lambda b: b["read"]["tls"].update({"sslmode": "whatever"}),
    lambda b: b.update({"extra": 1}),
    _first_envelope_twice,
    lambda b: b["candidate"].update({"files": []}),
    lambda b: b["candidate"]["files"].pop(),
    lambda b: b["candidate"].update({"listing_digest": "0" * 64}),
    lambda b: b["candidate"]["verify"].pop(),
    lambda b: b["candidate"].update({"collisions_approved": 3}),
    lambda b: b["durations"].update({"read": -1}),
], ids=["missing_durations", "missing_pin", "another_pin", "rows_as_text", "rows_off_witness", "witness_unequal",
        "fingerprint_off_witness", "facts_out_of_order", "free_text_in_a_fact", "free_key_in_roles", "free_text_in_schema",
        "free_text_in_policy", "free_text_in_collation", "version_claimed", "metadata_provenance_as_text", "sslmode",
        "unknown_field", "one_envelope_sixteen_times", "empty_listing", "listing_short_of_an_envelope", "listing_digest",
        "one_verify", "approvals_as_a_count", "negative_duration"])
def test_the_receipt_refuses_an_incomplete_ill_typed_or_inconsistent_one(honest_receipt, change):
    body = json.loads(honest_receipt)
    change(body)
    assert code_of(rc.load, json.dumps(body, ensure_ascii=False).encode("utf-8"), fixture_contract()) == X.RECEIPT_INVALID


def test_the_receipt_refuses_a_non_finite_duration(honest_receipt):
    body = json.loads(honest_receipt)
    text = json.dumps(body).replace('"connect": ' + json.dumps(body["durations"]["connect"]), '"connect": 1e999', 1)
    assert '"connect": 1e999' in text
    assert code_of(rc.load, text.encode("utf-8"), fixture_contract()) == X.RECEIPT_INVALID


@pytest.fixture
def evidence_root(honest, outside, monkeypatch):
    """A copy of the repository the honest receipt was rehearsed in — its view
    contract and its commits — with an evidence/ folder, so that the
    destination is valid and only the receipt decides."""
    import shutil

    root = outside / "repo"
    shutil.copytree(honest[1], root, symlinks=True)
    (root / "evidence").mkdir(exist_ok=True)
    monkeypatch.setattr(cli, "ROOT", root)
    return root


def test_export_evidence_writes_a_valid_receipt_and_refuses_a_bad_one_before_writing(honest_receipt, outside, evidence_root, capsys):
    target = evidence_root / "evidence" / "20261124"
    body = json.loads(honest_receipt)
    body["facts"][0]["compared"]["note"] = MARKER
    bad = outside / "bad.json"
    bad.write_text(json.dumps(body))
    assert cli.main(["evidence", str(bad), str(target)], {}) == 1
    assert not target.exists() and MARKER not in "".join(capsys.readouterr())
    good = outside / "good.json"
    good.write_bytes(honest_receipt)
    assert cli.main(["evidence", str(good), str(target)], {}) == 0
    assert rc.load((target / "export_run.json").read_bytes(), fixture_contract())


def test_export_evidence_refuses_a_destination_outside_evidence(honest_receipt, outside, evidence_root):
    good = outside / "good.json"
    good.write_bytes(honest_receipt)
    assert cli.main(["evidence", str(good), str(outside / "elsewhere")], {}) == 1
    assert not (outside / "elsewhere").exists()


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
    committed = (ROOT / "release" / "contract.json").read_bytes()
    contract = V.check_generated(V.load((ROOT / "release" / "views.json").read_bytes()), committed)
    assert len(contract.reports) == 16


def test_the_committed_fixture_is_what_the_script_writes():
    assert xf.fixture(xf.STRUCTURE.read_bytes()) == xf.FIXTURE.read_bytes()


def test_the_fixtures_witness_is_its_rows_fingerprint():
    fake = fw.Fake()
    witness = fake.contract.builds[0].witness
    assert all(witness[v.view] == (len(fake.rows[v.view]), fw.fingerprint(v, fake.rows[v.view])) for v in fake.contract.views)


@pytest.mark.skipif(not os.environ.get("ENG_DADOS_2_DIR"), reason="needs ENG_DADOS_2_DIR, which make check requires")
def test_the_committed_view_contract_is_what_propose_drafts_over_the_committed_catalogue():
    assert xf.proposed(pathlib.Path(os.environ["ENG_DADOS_2_DIR"])) == xf.STRUCTURE.read_bytes()


@pytest.mark.skipif(not os.environ.get("ENG_DADOS_2_DIR"), reason="needs ENG_DADOS_2_DIR, which make check requires")
def test_export_propose_writes_its_draft_in_drafts_and_leaves_both_contracts(outside):
    staging = outside / "staging"
    staging.mkdir()
    before = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ("release/views.json", "release/contract.json")}
    env = {"BICE_EXPORT_STAGING": str(staging), "ENG_DADOS_2_DIR": os.environ["ENG_DADOS_2_DIR"]}
    argv = ["propose", "--catalogue", str(xf.CATALOGUE), "--pin", xf.PIN]
    assert cli.main(argv, env) == 0
    drafts = list((staging / "drafts").glob("views.*.json"))
    assert len(drafts) == 1 and drafts[0].read_bytes() == xf.STRUCTURE.read_bytes()
    assert before == {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in before}
    env["BICE_EXPORT_STAGING"] = str(ROOT / "release")
    assert cli.main(argv, env) == 1, "a staging root in this repository is refused"


# --- round 1 of the review of the code (XIMPL-1-03, -04, -05, -07, -10, -13) -----------------------


def _session_at_policy(fake=None):
    """A session that has passed checks 1 to 7, so check 8 is the next statement."""
    fake = fake or fw.Fake()
    s = S._Session(fake)
    build = fake.contract.builds[0]
    S.check_transaction(s)
    S.check_provenance(s, fake.contract)
    S.check_login(s, fake.contract.login)
    S.check_roles(s, fake.contract)
    _f, oids = S.check_inventory(s, {v.view for v in fake.contract.views})
    S.check_access(s, oids)
    S.check_schema(s, fake.contract, oids)
    return fake, s, build


@pytest.mark.parametrize("result", [[], [("UTC",), ("UTC",)], [(None,)], [("UTC", "x")]], ids=["no_row", "two_rows", "null", "two_columns"])
def test_check_8_refuses_a_malformed_set_config_result(result, monkeypatch):
    fake, s, build = _session_at_policy()
    original = fake._answer
    monkeypatch.setattr(fake, "_answer", lambda sql, params: result if sql == S.Q_SET_POLICY else original(sql, params))
    with pytest.raises(Refused) as caught:
        S.check_policy(s, build)
    assert (caught.value.code, caught.value.check) == (X.FACT_POLICY, "set_policy")


def test_check_8_passes_on_well_formed_results_and_records_the_version_unavailable():
    _fake, s, build = _session_at_policy()
    fact, _settings, collation = S.check_policy(s, build)
    assert fact.passed and collation["version"] == "unavailable" and collation["actual_version"] is None


@pytest.mark.parametrize("declared, stored, actual, outcome", [
    ("2.36", "2.36", "2.36", "verified"),
    ("2.36", "2.36", "2.40", "collation_version"),
    (None, None, None, "unavailable"),
    (None, None, "2.36", "collation_version"),
    (None, "2.36", "2.36", "collation"),
    ("2.36", None, None, "collation"),
], ids=["versioned_match", "drift_under_a_stored_version", "unavailable", "appears_effective", "appears_stored", "vanishes"])
def test_check_8_the_collation_version_n111(declared, stored, actual, outcome):
    import dataclasses

    fake = fw.Fake()
    build = dataclasses.replace(fake.contract.builds[0], collation={**fake.contract.builds[0].collation, "datcollversion": declared})
    collation = {**build.collation, "datcollversion": stored}
    if outcome in ("verified", "unavailable"):
        assert S.collation_verdict(collation, actual, build) == outcome
    else:
        with pytest.raises(Refused) as caught:
            S.collation_verdict(collation, actual, build)
        assert (caught.value.code, caught.value.check) == (X.FACT_POLICY, outcome)


def test_the_real_result_object_reaches_result_schema():
    """XIMPL-1-07: the modifier read from a libpq result, through the pinned
    adapter's extraction, refuses at `result_schema`; unchanged, it passes."""
    from psycopg import pq

    class Wire(fw.Fake):
        modifier = None

        def fields(self):
            conn = pq.PGconn.connect_start(b"host=/nonexistent-socket-dir port=1")
            result = conn.make_empty_result(pq.ExecStatus.TUPLES_OK)
            described = list(self._fields)
            if self.modifier is not None:
                i = next(i for i, f in enumerate(described) if f[1] == 1700)
                described[i] = (described[i][0], 1700, self.modifier)
            result.set_attributes([pq.PGresAttDesc(n.encode(), 0, 0, 0, oid, -1, mod) for n, oid, mod in described])
            out = S.result_fields(result)
            conn.finish()
            return out

    for modifier, refused in ((None, False), (524296, True)):
        fake = Wire()
        fake.strict_order = False
        fake.modifier = modifier
        view = next(v for v in fake.contract.views if any(c.is_decimal for c in v.columns))
        s = S._Session(fake)
        if refused:
            with pytest.raises(Refused) as caught:
                S.read_view(s, view, fake.contract.builds[0], R.freeze)
            assert (caught.value.code, caught.value.view) == (X.RESULT_SCHEMA, view.view)
        else:
            assert S.read_view(s, view, fake.contract.builds[0], R.freeze).witness_equal


@pytest.mark.parametrize("argv", [
    ["run", "fx_marker_secret"],
    ["fx_marker_secret"],
    ["--password=fx_marker_secret"],
    ["propose", "--pin", "fx_marker_secret"],
    ["evidence", "fx_marker_secret"],
], ids=["extra_argument", "unknown_command", "unknown_option", "missing_argument", "one_of_two"])
def test_argument_refusals_print_a_fixed_line_and_no_argument(argv, capsys):
    assert cli.main(argv, environ()) == 2
    out, err = capsys.readouterr()
    assert (out, err) == ("", "refused: usage_invalid; class ArgumentError\n")


def test_cleanup_survives_a_vanished_caller_directory(outside):
    staging = outside / "staging"
    staging.mkdir()
    caller = outside / "caller"
    caller.mkdir()
    before = os.getcwd()
    os.chdir(caller)
    try:
        with paths.RunDirectory(staging, [ROOT]) as run_dir:
            (run_dir / "clear.parquet").write_bytes(b"an invented clear file")
            os.rmdir(caller)  # the directory the run was launched from goes away
        assert not run_dir.exists() and not list(staging.glob("run-*"))
        assert os.getcwd() == str(staging)
        with paths.RunDirectory(staging, [ROOT]):  # the lock was released
            pass
    finally:
        os.chdir(before)


def test_an_interrupt_during_cleanup_is_held_until_the_private_files_are_gone(outside, monkeypatch):
    import signal as sig

    staging = outside / "staging"
    staging.mkdir()
    original = paths.remove_tree

    def interrupted(path):
        os.kill(os.getpid(), sig.SIGINT)  # arrives mid-cleanup
        original(path)

    monkeypatch.setattr(paths, "remove_tree", interrupted)
    before = os.getcwd()
    with pytest.raises(KeyboardInterrupt):
        with paths.RunDirectory(staging, [ROOT]) as run_dir:
            (run_dir / "clear.parquet").write_bytes(b"an invented clear file")
    os.chdir(before)
    assert not run_dir.exists() and not list(staging.glob("run-*"))


def test_a_run_directory_that_cannot_be_removed_refuses(outside, monkeypatch):
    staging = outside / "staging"
    staging.mkdir()
    monkeypatch.setattr(paths, "remove_tree", lambda path: None)
    before = os.getcwd()
    with pytest.raises(Refused) as caught:
        with paths.RunDirectory(staging, [ROOT]):
            pass
    os.chdir(before)
    assert caught.value.code == X.CLEANUP_FAILED
    assert code_of(paths.RunDirectory(staging, [ROOT]).__enter__) == X.RUN_LEFTOVER


def test_publish_never_replaces_a_destination_that_appears_after_the_check(outside, monkeypatch):
    target = outside / "out"
    original = paths.rename_noreplace

    def racing(source, dest):
        dest.mkdir()  # an empty directory created between the check and the rename
        return original(source, dest)

    monkeypatch.setattr(paths, "rename_noreplace", racing)
    assert code_of(paths.publish, str(target), {"run.json": b"{}"}, [ROOT]) == X.PATH_EXISTS
    assert list(target.iterdir()) == [] and not list(outside.glob(paths.RESULT_PREFIX + "*"))


def test_tls_paths_are_resolved_where_they_are_named(outside, monkeypatch):
    monkeypatch.chdir(outside)
    found = S.settings(environ(BICE_WAREHOUSE_SSLMODE="verify-ca", BICE_WAREHOUSE_SSLROOTCERT="certs/root.crt",
                               BICE_WAREHOUSE_SSLCRL="certs/root.crl"))
    assert found.sslrootcert == str(outside / "certs" / "root.crt") and found.sslcrl == str(outside / "certs" / "root.crl")
    assert S.settings(environ(BICE_WAREHOUSE_SSLMODE="verify-full", BICE_WAREHOUSE_SSLROOTCERT="system")).sslrootcert == "system"


# --- round 2 (XIMPL-2-01 to -09) -------------------------------------------------------------------


def test_export_evidence_refuses_a_file_name_not_committed(honest_receipt, outside, evidence_root):
    """XIMPL-2-01: a candidate file whose name is not in Git is refused before writing."""
    from bi_como_codigo import release

    body = json.loads(honest_receipt)
    body["candidate"]["files"].append({"path": f"{MARKER}.md", "sha256": "0" * 64})
    body["candidate"]["files"].sort(key=lambda f: pathlib.PurePosixPath(f["path"]).parts)
    listing = [(f["path"], f["sha256"]) for f in body["candidate"]["files"]]
    body["candidate"]["listing_digest"] = release.canonical_digest(listing)
    body["candidate"]["included"] = sorted((f"site/{p}" for p, _ in listing), key=lambda p: pathlib.PurePosixPath(p).parts)
    assert rc.load(json.dumps(body).encode(), fixture_contract())  # the loader alone accepts it...
    bad = outside / "named.json"
    bad.write_text(json.dumps(body))
    target = evidence_root / "evidence" / "20261124"
    assert cli.main(["evidence", str(bad), str(target)], {}) == 1  # ...the command does not
    assert not target.exists()


def test_a_library_warning_or_log_line_never_reaches_the_terminal():
    """XIMPL-2-02: psycopg's failed-cancellation warning, through logging, and a
    library warning, while a run is interrupted — in a process of its own, so
    no test harness captures them on the command's behalf."""
    import subprocess

    code = f"""
import logging, warnings
from bi_como_codigo.exporter import cli, run
def interrupted(*a, **k):
    logging.getLogger("psycopg").warning("query cancellation failed: %s", {MARKER!r})
    warnings.warn("a library warning holding {MARKER}")
    raise KeyboardInterrupt
run.export = interrupted
raise SystemExit(cli.main(["run"], {{}}))
"""
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert (done.returncode, done.stdout, done.stderr) == (1, "", "refused: unexpected; class KeyboardInterrupt\n")


def _revoking_crl(cert, key, serials):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization

    now = dt.datetime.now(dt.timezone.utc)
    builder = (x509.CertificateRevocationListBuilder().issuer_name(cert.subject)
               .last_update(now - dt.timedelta(days=1)).next_update(now + dt.timedelta(days=1)))
    for serial in serials:
        builder = builder.add_revoked_certificate(
            x509.RevokedCertificateBuilder().serial_number(serial).revocation_date(now - dt.timedelta(hours=1)).build())
    return builder.sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM)


@pytest.mark.parametrize("revoked", [False, True], ids=["unrevoked", "revoked"])
def test_the_crl_named_relative_to_the_caller_is_the_one_libpq_uses(outside, monkeypatch, revoked):
    """XIMPL-2-03: the CRL is used — a revoked server certificate refuses the
    handshake, an unrevoked one reaches the startup message."""
    certs = outside / "certs"
    certs.mkdir()
    ca_key, ca = _certificate("probe-ca", ca=True)
    _pem(ca_key, ca, certs, "ca")
    server_key, server_cert = _certificate("server", issuer=ca.subject, issuer_key=ca_key)
    k, ct = _pem(server_key, server_cert, certs, "server")
    (certs / "root.crl").write_bytes(_revoking_crl(ca, ca_key, [server_cert.serial_number] if revoked else []))

    class Server(TlsServer):
        def __init__(self):
            self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ctx.load_cert_chain(ct, k)
            self.sock = socket.socket()
            self.sock.bind(("127.0.0.1", 0))
            self.sock.listen(4)
            self.port = self.sock.getsockname()[1]
            self.seen = {"tls": False, "peer_cert": None, "startup": None}
            self.thread = threading.Thread(target=self._serve, daemon=True)
            self.thread.start()

    server = Server()
    monkeypatch.setenv("HOME", str(outside / "nohome"))
    monkeypatch.chdir(outside)
    try:
        found = S.settings(environ(BICE_WAREHOUSE_PORT=str(server.port), BICE_WAREHOUSE_SSLMODE="verify-ca",
                                   BICE_WAREHOUSE_SSLROOTCERT="certs/ca.crt", BICE_WAREHOUSE_SSLCRL="certs/root.crl"))
        elsewhere = outside / "run"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        assert code_of(S.connect, found, elsewhere / "absent", environ={}) == X.CONNECT_FAILED
    finally:
        server.close()
    assert (server.seen["startup"] is None) is revoked


def test_a_signal_noted_while_cleaning_ends_the_run_with_both_handlers_restored(outside, monkeypatch):
    """XIMPL-2-05: SIGTERM noted while cleaning ends as `interrupted`; a SIGINT
    arriving between the two restorations is still noted; afterwards both
    handlers are the caller's."""
    import signal as sig

    staging = outside / "staging"
    staging.mkdir()
    before = (sig.getsignal(sig.SIGINT), sig.getsignal(sig.SIGTERM))
    original = paths.remove_tree
    monkeypatch.setattr(paths, "remove_tree", lambda path: (os.kill(os.getpid(), sig.SIGTERM), original(path)))
    cwd = os.getcwd()
    with pytest.raises(Refused) as caught:
        with paths.RunDirectory(staging, [ROOT]) as run_dir:
            pass
    os.chdir(cwd)
    assert (caught.value.code, caught.value.check) == (X.INTERRUPTED, "cleanup") and not run_dir.exists()
    assert (sig.getsignal(sig.SIGINT), sig.getsignal(sig.SIGTERM)) == before

    real = paths.signal.signal
    sent = []

    def restoring(signum, handler):
        previous = real(signum, handler)
        if not sent and handler in before:  # right after the first of the two restorations
            sent.append(signum)
            os.kill(os.getpid(), sig.SIGINT)
        return previous

    monkeypatch.setattr(paths, "remove_tree", original)
    monkeypatch.setattr(paths.signal, "signal", restoring)
    with pytest.raises(KeyboardInterrupt):
        with paths.RunDirectory(staging, [ROOT]):
            pass
    os.chdir(cwd)
    monkeypatch.setattr(paths.signal, "signal", real)
    assert (sig.getsignal(sig.SIGINT), sig.getsignal(sig.SIGTERM)) == before and not list(staging.glob("run-*"))


# --- round 3 (XIMPL-3-01 to -03) -------------------------------------------------------------------


def _with_extra_path(raw: bytes, path: str) -> dict:
    from bi_como_codigo import release

    body = json.loads(raw)
    body["candidate"]["files"].append({"path": path, "sha256": "0" * 64})
    body["candidate"]["files"].sort(key=lambda f: pathlib.PurePosixPath(f["path"]).parts)
    listing = [(f["path"], f["sha256"]) for f in body["candidate"]["files"]]
    body["candidate"]["listing_digest"] = release.canonical_digest(listing)
    body["candidate"]["included"] = sorted((f"site/{p}" for p, _ in listing), key=lambda p: pathlib.PurePosixPath(p).parts)
    return body


@pytest.mark.parametrize("path", [f"package/{MARKER}.md", f"{MARKER}.md"], ids=["under_package", "at_the_root"])
def test_an_extra_path_never_reaches_the_evidence(honest_receipt, outside, evidence_root, path):
    """XIMPL-3-01: under package/ only the manifest and the sealed envelopes;
    elsewhere only names committed at the rehearsed commit."""
    bad = outside / "named.json"
    bad.write_text(json.dumps(_with_extra_path(honest_receipt, path)))
    target = evidence_root / "evidence" / "20261124"
    assert cli.main(["evidence", str(bad), str(target)], {}) == 1
    assert not target.exists()


def test_an_honest_receipt_survives_a_later_committed_rename(honest_receipt, outside, evidence_root):
    """XIMPL-3-03: names are checked at the commit the run rehearsed."""
    import exporter_world as xw

    good = outside / "good.json"
    good.write_bytes(honest_receipt)
    assert cli.main(["evidence", str(good), str(evidence_root / "evidence" / "a")], {}) == 0
    xw.git(evidence_root, "mv", "site/releases.md", "site/publicacoes.md")
    include = evidence_root / "release" / "include.txt"
    include.write_text(include.read_text().replace("site/releases.md", "site/publicacoes.md"))
    xw.git(evidence_root, "commit", "-qam", "a rename")
    assert cli.main(["evidence", str(good), str(evidence_root / "evidence" / "b")], {}) == 0


_PUBLISH = """
import os, pathlib, signal, sys
from bi_como_codigo.exporter import Refused, paths
target, when = pathlib.Path(sys.argv[1]), sys.argv[2]
original_check, original_rename = paths.check, paths.rename_noreplace
seen = []
def check(path, protected):
    out = original_check(path, protected)
    if when == "writing" and pathlib.Path(path).name == "package":  # called once per file, before its write
        seen.append(1)
        if len(seen) == 2:
            os.kill(os.getpid(), signal.SIGTERM)  # before the second envelope is written
    return out
def rename(source, dest):
    original_rename(source, dest)
    if when == "renamed":
        os.kill(os.getpid(), signal.SIGTERM)  # right after the rename
paths.check, paths.rename_noreplace = check, rename
files = {"package/manifest.json": b"{}", **{f"package/P{i:02d}.0000000000000000.bice": b"x" for i in range(1, 17)},
         "metadata.json": b"{}", "run.json": b"{}"}
try:
    paths.publish(str(target), files, [])
    print("published")
except Refused as refusal:
    print(refusal.code, refusal.check)
"""


@pytest.mark.parametrize("when, printed, complete", [("writing", "interrupted publish", False), ("renamed", "interrupted published", True)])
def test_a_real_sigterm_during_publication_has_a_defined_outcome(outside, when, printed, complete):
    """XIMPL-3-02, with a real signal in a process of its own: while writing, a
    fixed refusal and nothing left; right after the rename, a fixed refusal that
    says the result is published, all 19 files in place."""
    import subprocess

    target = outside / "out"
    done = subprocess.run([sys.executable, "-c", _PUBLISH, str(target), when], capture_output=True, text=True, timeout=60)
    assert (done.returncode, done.stdout.strip(), done.stderr) == (0, printed, "")
    assert not list(outside.glob(paths.RESULT_PREFIX + "*")), "no partial sibling"
    if complete:
        assert sum(1 for p in target.rglob("*") if p.is_file()) == 19
    else:
        assert not target.exists()
