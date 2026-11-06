"""The package gate of stage 2.2b (docs/package_gate.md), on fixtures, with no
network: every mutation of §9 stopped by its check, the honest controls
accepted, and the edges of each check. `release.verify` is the function the
publishing workflow runs; Hosting's API and the live site are stand-ins."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import secrets
import shutil
import sys
from decimal import Decimal

import pytest

from bi_como_codigo import contract as c, envelope as e, release as r

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
import site_fixture as sf  # noqa: E402


@pytest.fixture
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    for name in ("release", "site"):
        shutil.copytree(ROOT / name, tmp_path / name, ignore=shutil.ignore_patterns("node_modules"))
    return tmp_path


def no_live():
    return r.NO_LIVE


def contract(repo) -> c.Contract:
    return c.load(repo)[0]


def rows(report: str) -> list[tuple]:
    return [tuple(row) for row in sf.ROWS[report]]


def payload(repo, report: str, data: list[tuple] | None = None, types=None, totals=None, parquet=None):
    k = contract(repo)
    data = rows(report) if data is None else data
    spec = k.reports[report]
    return (totals if totals is not None else sf.totals(k, spec, data),
            parquet if parquet is not None else sf.parquet(spec, data, types))


def payloads(repo, **changed) -> dict[str, tuple[bytes, bytes]]:
    out = {rid: payload(repo, rid) for rid in ("P01", "P02", "P13")}
    out.update(changed)
    return out


def seal(repo, payloads_, *, declared=None, package_id=None, salts=None, deks=None, ivs=None):
    """A package sealed with `seal_report`, every input choosable, written into
    the repository's site/package/. Returns (manifest bytes, envelopes)."""
    declared = declared or r.profiles(repo)
    package_id = package_id or secrets.token_bytes(16)
    salts = salts or {p.id: secrets.token_bytes(16) for p in declared}
    keks = {p.id: e.derive_kek(p.password, salts[p.id], e.ITERATIONS) for p in declared}
    files = {}
    for rid in sorted(payloads_):
        slots = [e.SlotInput(p.id, salts[p.id], e.ITERATIONS, keks[p.id]) for p in declared if rid in p.reports]
        dek = (deks or {}).get(rid) or secrets.token_bytes(32)
        iv = (ivs or {}).get(rid) or secrets.token_bytes(12)
        envelope = e.seal_report(package_id, rid, slots, dek, iv, e.build_payload(*payloads_[rid]))
        files[e.file_name(rid, envelope)] = envelope
    manifest = e._manifest_bytes(package_id, declared, salts, files)
    write(repo, manifest, files)
    return manifest, files


def write(repo, manifest: bytes, files: dict[str, bytes]) -> None:
    package = repo / "site" / "package"
    shutil.rmtree(package)
    package.mkdir()
    (package / "manifest.json").write_bytes(manifest)
    for name, data in files.items():
        (package / name).write_bytes(data)


def committed(repo) -> tuple[bytes, dict[str, bytes]]:
    package = repo / "site" / "package"
    return (package / "manifest.json").read_bytes(), {p.name: p.read_bytes() for p in package.glob("*.bice")}


def verify(repo, live=no_live):
    deploy = repo / "deploy"
    if deploy.exists():
        shutil.rmtree(deploy)
    r.build(repo, deploy)
    return r.verify(repo, deploy, live=live)


def refused(repo, code: str, live=no_live, where: str | None = None):
    with pytest.raises(r.Refused) as refusal:
        verify(repo, live)
    assert code in str(refusal.value), str(refusal.value)
    if where:
        assert where in str(refusal.value)
    return str(refusal.value)


# --- the controls -------------------------------------------------------------------


def test_the_committed_fixture_passes(repo):
    body = verify(repo)
    assert body["live"] == "none" and body["checked_at"].endswith("Z")


def test_a_fresh_package_against_live_passes(repo):
    live = committed(repo)
    seal(repo, payloads(repo))
    body = verify(repo, live=lambda: live)
    assert body["live"] == sorted(f"package/{name}" for name in live[1])


def test_the_live_package_unchanged_passes(repo):
    live = committed(repo)
    assert verify(repo, live=lambda: live)["live"] == sorted(f"package/{name}" for name in live[1])


# --- MUT-01 to 07d: the package and the inspection ------------------------------------------


def test_mut01_a_tampered_digest_after_the_name_prefix(repo):
    path = repo / "site" / "package" / "manifest.json"
    data = json.loads(path.read_text())
    sha = data["reports"][0]["sha256"]
    data["reports"][0]["sha256"] = sha[:20] + ("0" if sha[20] != "0" else "1") + sha[21:]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    refused(repo, "integrity_mismatch")


def test_mut02_a_reused_key_and_iv(repo):
    dek, iv = secrets.token_bytes(32), secrets.token_bytes(12)
    seal(repo, payloads(repo), deks={"P01": dek, "P02": dek}, ivs={"P01": iv, "P02": iv})
    refused(repo, "dek_reused")


def test_mut03_a_reused_iv(repo):
    iv = secrets.token_bytes(12)
    seal(repo, payloads(repo), ivs={"P01": iv, "P02": iv})
    refused(repo, "iv_reused")


def test_mut04_a_parquet_in_an_included_page(repo):
    with open(repo / "site" / "releases.md", "ab") as fh:
        fh.write(payload(repo, "P01")[1])
    refused(repo, "Parquet magic")


def test_mut05_a_short_row_in_the_page(repo):
    page = repo / "site" / "index.html"
    page.write_text(page.read_text().replace("</main>", "<table><tr><td>fixture_a</td><td>1.25</td><td>2</td></tr></table></main>"))
    refused(repo, "clear_value", where="index.html")


def test_mut06_a_number_alone_in_brazilian_form(repo):
    page = repo / "site" / "index.html"
    page.write_text(page.read_text().replace("</main>", "<p>Total: 1.200</p></main>"))
    refused(repo, "clear_value", where="index.html")


def test_mut07_the_totals_in_the_page(repo):
    page = repo / "site" / "index.html"
    totals = payload(repo, "P13")[0].decode()
    page.write_text(page.read_text().replace("</main>", f"<pre>{totals}</pre></main>"))
    refused(repo, "clear_totals", where="index.html")


def test_mut07b_the_row_count_alone(repo):
    """PGATE-2-02: a report of 140 rows, its count printed on the page."""
    many = [(f"fixture_{i:03d}", Decimal("1.00"), i) for i in range(140)]
    seal(repo, payloads(repo, P01=payload(repo, "P01", many)))
    verify(repo)  # the control: the same package, no leak
    page = repo / "site" / "index.html"
    page.write_text(page.read_text().replace("</main>", "<p>140</p></main>"))
    refused(repo, "clear_value", where="index.html")


def test_mut07c_a_value_in_a_manifest_label(repo):
    declared = [e.DeclaredProfile(p.id, p.label + (" fixture_norte" if p.id == "logistica" else ""), p.password, p.reports)
                for p in r.profiles(repo)]
    seal(repo, payloads(repo), declared=declared)
    refused(repo, "clear_value", where="manifest.json")


def test_mut07d_a_date_collision_refused_unlisted_and_accepted_listed(repo):
    with open(repo / "site" / "releases.md", "a") as fh:
        fh.write("- 2025-01-01 — uma linha que cita a data de um relatório.\n")
    refused(repo, "clear_value", where="releases.md")
    listed = {"about": "test", "values": [{"value": "2025-01-01", "reason": "a release date, public by design"}]}
    (repo / "release" / "public_values.json").write_text(json.dumps(listed))
    verify(repo)


def test_the_manifest_s_typed_fields_are_not_searched(repo):
    """N83: a cell equal to `iterations` does not collide with the manifest."""
    k = contract(repo)
    data = [("600000", Decimal("1.00"), 1)]
    seal(repo, payloads(repo, P01=(sf.totals(k, k.reports["P01"], data), sf.parquet(k.reports["P01"], data))))
    verify(repo)


# --- MUT-08 to 10: the inventory and the entitlements -----------------------------------------


def _declared(repo, change):
    return [e.DeclaredProfile(p.id, p.label, p.password, change(p)) for p in r.profiles(repo)]


def test_mut08_a_missing_view(repo):
    declared = _declared(repo, lambda p: tuple(x for x in p.reports if x != "P02"))
    out = payloads(repo)
    del out["P02"]
    seal(repo, out, declared=declared)
    refused(repo, "inventory_exact")


def test_mut09_an_extra_view(repo):
    declared = _declared(repo, lambda p: (*p.reports, "P03") if p.id == "diretoria" else p.reports)
    seal(repo, payloads(repo, P03=payload(repo, "P01")), declared=declared)
    refused(repo, "inventory_exact")


def test_mut10_an_entitlement_changed(repo):
    declared = _declared(repo, lambda p: ("P01", "P13") if p.id == "logistica" else p.reports)
    seal(repo, payloads(repo), declared=declared)
    refused(repo, "entitlements_exact")


def test_declarations_agree_on_the_two_trusted_files(repo):
    path = repo / "release" / "contract.json"
    data = json.loads(path.read_text())
    data["reports"]["P04"] = data["reports"]["P01"]
    path.write_text(json.dumps(data))
    refused(repo, "declarations_agree")


# --- MUT-11 to 19: the Parquet against the contract ----------------------------------------------


def test_mut11_a_changed_type(repo):
    seal(repo, payloads(repo, P01=payload(repo, "P01", types={"valor": "DOUBLE"})))
    refused(repo, "schema_exact", where="P01")


@pytest.mark.parametrize("change", ["renamed", "dropped", "reordered"])
def test_mut12_a_column_renamed_dropped_or_reordered(repo, change):
    import duckdb

    k = contract(repo)
    base = sf.parquet(k.reports["P01"], rows("P01"))
    tmp = repo / "t.parquet"
    tmp.write_bytes(base)
    select = {"renamed": "rotulo AS nome, valor, unidades", "dropped": "rotulo, valor", "reordered": "valor, rotulo, unidades"}[change]
    out = repo / "m.parquet"
    duckdb.connect().execute(f"COPY (SELECT {select} FROM read_parquet('{tmp}')) TO '{out}' (FORMAT parquet)")
    seal(repo, payloads(repo, P01=payload(repo, "P01", parquet=out.read_bytes())))
    refused(repo, "schema_exact", where="P01")


def test_mut13_a_duplicated_row(repo):
    data = rows("P01") + [rows("P01")[0]]
    seal(repo, payloads(repo, P01=payload(repo, "P01", data)))
    refused(repo, "grain_unique", where="P01")


def test_mut14_a_null_where_the_contract_forbids_it(repo):
    data = rows("P01")
    data[1] = (data[1][0], None, data[1][2])
    seal(repo, payloads(repo, P01=payload(repo, "P01", data)))
    refused(repo, "not_null", where="valor")


def _totals(repo, report="P01", **change) -> bytes:
    body = json.loads(payload(repo, report)[0])
    for key, value in change.items():
        if key == "sum":
            body["sums"].update(value)
        else:
            body[key] = value
    return json.dumps(body).encode()


@pytest.mark.parametrize(
    "totals, code",
    [
        (lambda repo: _totals(repo, rows=5), "totals_rows"),
        (lambda repo: _totals(repo, sum={"valor": "14.01"}), "totals_sums"),
    ],
    ids=["rows_off_by_one", "sum_off_by_a_cent"],
)
def test_mut15_totals_that_do_not_match(repo, totals, code):
    seal(repo, payloads(repo, P01=payload(repo, "P01", totals=totals(repo))))
    refused(repo, code, where="P01")


@pytest.mark.parametrize(
    "totals",
    [
        lambda repo: b'{"contract_version":1,"contract_version":1,"report_version":1,"rows":4,"sums":{"valor":"14.00","unidades":"10"}}',
        lambda repo: _totals(repo, sum={"valor": 14.0}),
        lambda repo: _totals(repo, extra=1),
    ],
    ids=["duplicate_key", "sum_as_a_number", "extra_key"],
)
def test_mut16_totals_malformed(repo, totals):
    seal(repo, payloads(repo, P01=payload(repo, "P01", totals=totals(repo))))
    refused(repo, "totals_shape", where="P01")


@pytest.mark.parametrize("key", ["contract_version", "report_version"])
def test_mut17_totals_of_another_version(repo, key):
    seal(repo, payloads(repo, P01=payload(repo, "P01", totals=_totals(repo, **{key: 2}))))
    refused(repo, "totals_version", where="P01")


def _invalid_utf8_parquet(repo) -> bytes:
    import duckdb

    k = contract(repo)
    tmp = repo / "plain.parquet"
    spec = k.reports["P01"]
    con = duckdb.connect()
    con.execute("CREATE TABLE t (rotulo VARCHAR, valor DECIMAL(18,2), unidades INTEGER)")
    con.executemany("INSERT INTO t VALUES (?, ?, ?)", rows("P01"))
    con.execute(f"COPY t TO '{tmp}' (FORMAT parquet, COMPRESSION uncompressed, DICTIONARY_SIZE_LIMIT 0)")
    raw = tmp.read_bytes()
    assert b"fixture_b" in raw
    return raw.replace(b"fixture_b", b"fixture_\xff", 1)


@pytest.mark.parametrize("parquet", [lambda repo: b"PAR1" + b"\x00" * 64 + b"PAR1", _invalid_utf8_parquet], ids=["garbage", "invalid_utf8"])
def test_mut18_a_parquet_duckdb_cannot_read(repo, parquet):
    seal(repo, payloads(repo, P01=payload(repo, "P01", parquet=parquet(repo))))
    message = refused(repo, "parquet_unreadable")
    assert "fixture" not in message


def test_mut19_a_parquet_over_the_content_bound(repo):
    wide = [(f"fixture_{i:02d}_" + "x" * (1024 * 1024), Decimal("1.00"), 1) for i in range(65)]
    seal(repo, payloads(repo, P01=payload(repo, "P01", wide)))
    refused(repo, "content_bound", where="P01")


# --- MUT-20, 21: against the package live ----------------------------------------------------------


def _live_material(repo, live):
    manifest = e.validate_manifest(live[0])
    deks = dict(zip(sorted(manifest.reports), r._deks(manifest, live[1], {p.id: p.password for p in r.profiles(repo)})))
    ivs = {rid: e.parse_header(live[1][manifest.reports[rid].file])[0].iv for rid in manifest.reports}
    salts = {pid: p.salt for pid, p in manifest.profiles.items()}
    return manifest, deks, ivs, salts


def test_mut20_the_live_package_id_with_one_envelope_resealed(repo):
    live = committed(repo)
    manifest, deks, ivs, salts = _live_material(repo, live)
    seal(repo, payloads(repo), package_id=manifest.package_id, salts=salts,
         deks={k: v for k, v in deks.items() if k != "P02"}, ivs={k: v for k, v in ivs.items() if k != "P02"})
    refused(repo, "package_id_reused", live=lambda: live)


@pytest.mark.parametrize("field, code", [("deks", "dek_reused"), ("ivs", "iv_reused"), ("salts", "salt_reused")])
def test_mut21_a_new_package_reusing_live_material(repo, field, code):
    live = committed(repo)
    _, deks, ivs, salts = _live_material(repo, live)
    choose = {"deks": {"deks": {"P13": deks["P13"]}}, "ivs": {"ivs": {"P13": ivs["P13"]}},
              "salts": {"salts": {"diretoria": secrets.token_bytes(16), "logistica": salts["logistica"]}}}[field]
    seal(repo, payloads(repo), **choose)
    refused(repo, code, live=lambda: live)


def test_read_live_refuses_anything_but_200_or_404():
    assert r.read_live("s", get=lambda url: (404, b"")) is r.NO_LIVE
    with pytest.raises(r.Refused, match="live_unreadable"):
        r.read_live("s", get=lambda url: (503, b""))


def test_read_live_refuses_an_envelope_unlike_its_manifest(repo):
    manifest, files = committed(repo)
    served = {f"https://s.web.app/package/{name}": data[:-1] + b"\x00" for name, data in files.items()}
    served["https://s.web.app/package/manifest.json"] = manifest
    with pytest.raises(r.Refused, match="does not match"):
        r.read_live("s", get=lambda url: (200, served[url]))


# --- MUT-22 to 25: preview binds the live version, promote checks it ----------------------------


class Hosting:
    """Hosting's API, as `channel` and `version_files` read it."""

    def __init__(self, version=None, released="2026-11-06T10:00:00Z", files=()):
        self.version, self.released, self.files, self.fail = version, released, list(files), False

    def channel(self, site, name, token):
        if self.fail:
            raise r.Refused("channel live of s: 503")
        if self.version is None:
            return {"name": "live"}
        return {"release": {"version": {"name": f"sites/s/versions/{self.version}"}, "releaseTime": self.released}}

    def version_files(self, site, version, token):
        assert version == self.version
        return {p: "h" for p in self.files}


@pytest.fixture
def hosting(monkeypatch):
    h = Hosting()
    monkeypatch.setattr(r, "channel", h.channel)
    monkeypatch.setattr(r, "version_files", h.version_files)
    return h


PATHS = ["package/P01.a.bice", "package/P02.b.bice"]


def record(live, at="2026-11-06T10:30:00Z"):
    return {"live": live, "checked_at": at}


def test_bind_live_first_release_with_no_live_release(hosting):
    assert r.bind_live("s", record("none"), "t") == "none"


def test_bind_live_first_release_with_a_version_holding_no_package(hosting):
    hosting.version, hosting.files = "vEmpty", ["index.html"]
    assert r.bind_live("s", record("none"), "t") == "vEmpty"


def test_bind_live_binds_the_compared_version(hosting):
    hosting.version, hosting.files = "vA", [*PATHS, "package/manifest.json", "index.html"]
    assert r.bind_live("s", record(PATHS), "t") == "vA"


def test_mut23_a_package_appeared_after_verify(hosting):
    hosting.version, hosting.files = "vA", [*PATHS, "package/manifest.json"]
    with pytest.raises(r.Refused, match="live changed during this run"):
        r.bind_live("s", record("none"), "t")


def test_mut25_a_release_within_the_margin(hosting):
    hosting.version, hosting.files, hosting.released = "vA", [*PATHS, "package/manifest.json"], "2026-11-06T10:25:00Z"
    with pytest.raises(r.Refused, match="live changed during this run"):
        r.bind_live("s", record(PATHS), "t")


def test_bind_live_refuses_other_paths(hosting):
    hosting.version, hosting.files = "vB", ["package/P01.c.bice", "package/manifest.json"]
    with pytest.raises(r.Refused, match="live changed during this run"):
        r.bind_live("s", record(PATHS), "t")


def test_bind_live_an_api_failure_is_its_own_refusal(hosting):
    hosting.fail = True
    with pytest.raises(r.Refused, match="live could not be read"):
        r.bind_live("s", record(PATHS), "t")


def _promote(hosting, version, live_version, cloned):
    def run(cmd, check):
        cloned.append(cmd)
        hosting.version = version
        import subprocess
        return subprocess.CompletedProcess(cmd, 0)
    return r.promote("s", version, live_version, "t", run=run)


def test_promote_when_live_is_still_the_bound_version(hosting):
    hosting.version, cloned = "vA", []
    assert _promote(hosting, "vB", "vA", cloned) == "promoted" and cloned


def test_promote_first_release_against_none(hosting):
    cloned = []
    assert _promote(hosting, "vB", "none", cloned) == "promoted" and cloned


def test_promote_rerun_of_a_success_is_already_live(hosting):
    hosting.version, cloned = "vB", []
    assert _promote(hosting, "vB", "vA", cloned) == "already live" and not cloned


@pytest.mark.parametrize("now_live", ["vA2", None], ids=["mut22_mut24_another_version", "live_emptied"])
def test_mut22_mut24_live_changed_since_the_preview(hosting, now_live):
    """PGATE-1-01 and PGATE-4-01: whatever reached live since, even A's own
    envelopes under another manifest, is another version ID."""
    hosting.version, cloned = now_live, []
    with pytest.raises(r.Refused, match="live changed since this preview"):
        _promote(hosting, "vR", "vA", cloned)
    assert not cloned


def test_promote_an_api_failure_before_the_clone(hosting):
    hosting.fail, cloned = True, []
    with pytest.raises(r.Refused, match="live could not be read"):
        _promote(hosting, "vB", "vA", cloned)
    assert not cloned


def test_a_record_without_live_version_is_refused():
    raw = json.dumps({"pr": 7, "head_sha": "h", "candidate_run": 1, "version": "v", "channel": "pr-7", "url": "u",
                      "expires": "2026-12-01T00:00:00Z", "digest": "d"}).encode()
    run = {"id": 1, "path": ".github/workflows/publish.yml", "event": "workflow_run", "head_branch": "main",
           "conclusion": "success", "run_started_at": "2026-11-06T01:00:00Z", "run_attempt": 1}
    with pytest.raises(r.Refused, match="no live version"):
        r.select_record([run], "h", lambda _: [{"id": 5, "name": "release-record"}], lambda _: raw)


def test_check_listing_refuses_a_changed_artifact(repo):
    deploy = repo / "deploy"
    r.build(repo, deploy)
    body = r.verify(repo, deploy, live=no_live)
    r.check_listing(deploy, body)
    (deploy / "index.html").write_text("changed")
    with pytest.raises(r.Refused, match="changed"):
        r.check_listing(deploy, body)


# --- §7: what a refusal prints -----------------------------------------------------------------------


def markers(repo, before: set[str]) -> set[str]:
    """GIMPL-2-01: what the candidate itself holds, read after the mutation —
    each report decrypted, its totals, its cells (texts, dates, decimals in
    both spellings, integers of three or more digits) and its current DEKs in
    hex. A report DuckDB cannot read contributes the honest fixture's values
    (`before`), from which its mutation was made. The refusal texts of these
    cases carry no hexadecimal name, so an integer cannot match by chance."""
    import duckdb

    manifest_raw, files = committed(repo)
    m = e.validate_manifest(manifest_raw)
    passwords = {p.id: p.password for p in r.profiles(repo)}
    out = {"fixture_"} | before
    for rid, entry in m.reports.items():
        pid = sorted(m.entitled(rid))[0]
        totals, parquet = e.open_report(m, files[entry.file], rid, e.login(m, pid, passwords[pid]))
        out.add(totals.decode("utf-8", "replace"))
        try:  # each scalar of the totals too, as the candidate holds it (GIMPL-3-01)
            body = json.loads(totals)
            scalars = [str(body.get("rows", ""))] + [str(v) for v in (body.get("sums") or {}).values()]
        except (ValueError, AttributeError):
            scalars = []
        for text in scalars:
            if c._CANONICAL.fullmatch(text) and (c.eligible_number(text) or len(text.lstrip("-")) >= 3):
                out.update(c.spellings(text))
        path = repo / f"{rid}.markers.parquet"
        path.write_bytes(parquet)
        try:
            cells = duckdb.connect().execute(f"SELECT * FROM read_parquet('{path}')").fetchall()
        except Exception:
            continue
        for row in cells:
            for value in row:
                if value is None or isinstance(value, bool):
                    continue
                text = f"{value:f}" if isinstance(value, Decimal) else str(value)
                if isinstance(value, (int, Decimal)):
                    if c.eligible_number(text) or (isinstance(value, int) and len(text.lstrip("-")) >= 3):
                        out.update(c.spellings(text))
                else:
                    out.add(text)
    for dek in r._deks(m, files, passwords):
        out.update({dek.hex(), dek.hex().upper()})
    return out


def honest_markers(repo) -> set[str]:
    k = contract(repo)
    out = set()
    for rid, data in sf.ROWS.items():
        out.add(sf.totals(k, k.reports[rid], data).decode())
        for row in data:
            for value in row:
                if isinstance(value, str):
                    out.add(value)
                elif isinstance(value, Decimal) and value != value.to_integral_value():
                    out.update(c.spellings(f"{value:f}"))
    return out


def _cli_mutations():
    return {
        "mut11_type": lambda repo: seal(repo, payloads(repo, P01=payload(repo, "P01", types={"valor": "DOUBLE"}))),
        "mut13_grain": lambda repo: seal(repo, payloads(repo, P01=payload(repo, "P01", rows("P01") + [rows("P01")[0]]))),
        "mut15_sum": lambda repo: seal(repo, payloads(repo, P01=payload(repo, "P01", totals=_totals(repo, sum={"valor": "14.01"})))),
        "mut16_shape": lambda repo: seal(repo, payloads(repo, P01=payload(repo, "P01", totals=_totals(repo, extra=1)))),
        "mut17_version": lambda repo: seal(repo, payloads(repo, P13=payload(repo, "P13", totals=_totals(repo, "P13", report_version=2)))),
        "mut18_utf8": lambda repo: seal(repo, payloads(repo, P01=payload(repo, "P01", parquet=_invalid_utf8_parquet(repo)))),
        "mut05_page": lambda repo: (repo / "site" / "index.html").write_text("<p>fixture_a 1.25</p>"),
        "mut07_totals": lambda repo: (repo / "site" / "index.html").write_text(payload(repo, "P13")[0].decode()),
    }


@pytest.mark.parametrize("case", sorted(_cli_mutations()))
def test_the_cli_prints_no_value_of_a_refused_package(repo, monkeypatch, capfd, tmp_path, case):
    """PGATE-1-02, GIMPL-1-04: through the CLI, every negative case — stdout,
    stderr, native ones included, and the step summary — holds no decrypted
    value and no key, and no release record is written."""
    before = honest_markers(repo)
    _cli_mutations()[case](repo)
    honest = markers(repo, before)
    deploy = repo / "deploy"
    r.build(repo, deploy)
    summary, record = tmp_path / "summary.md", tmp_path / "rel.json"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(r, "ROOT", repo)
    monkeypatch.setattr(r, "read_live", lambda site: r.NO_LIVE)
    assert r.main(["verify", "--deploy", str(deploy), "--record", str(record), "--site", "s"]) == 1
    out, err = capfd.readouterr()
    text = out + err + summary.read_text()
    assert "refused:" in text and "Traceback" not in text
    assert not record.exists()
    leaked = sorted(m for m in honest if m in text)
    assert not leaked, leaked


# --- the edges of each check ----------------------------------------------------------------------


def _check(columns, sums, data, grain=None):
    report = c.Report("P01", 1, tuple(c.Column(n, t, nl) for n, t, nl in columns), tuple(grain or [columns[0][0]]), tuple(sums))
    k = c.Contract(1, {"P01": report})
    return c.check_payload(k, report, sf.totals(k, report, data), sf.parquet(report, data))


ID = ("id", "INTEGER", False)


@pytest.mark.parametrize(
    "column, values",
    [
        (("v", "DECIMAL(18,2)", False), [Decimal("9999999999999999.99"), Decimal("9999999999999999.99"), Decimal("-9999999999999999.99")]),
        (("v", "DECIMAL(18,2)", False), [Decimal("-9999999999999999.99"), Decimal("9999999999999999.99"), Decimal("9999999999999999.99")]),
        (("v", "BIGINT", False), [9223372036854775807, 9223372036854775807, -9223372036854775808]),
        (("v", "DECIMAL(18,0)", False), [5, -3]),
        (("v", "DECIMAL(18,2)", False), [Decimal("0.75"), Decimal("-0.75")]),
        (("v", "DECIMAL(18,2)", True), [None, None]),
        (("v", "SMALLINT", False), []),
    ],
    ids=["decimal_limit", "decimal_limit_other_order", "bigint_limits", "scale_zero", "negative_zero", "all_null", "no_row"],
)
def test_sums_exact_at_the_edges(column, values):
    data = [(i, v) for i, v in enumerate(values)]
    got = _check([ID, column], ["v"], data)
    assert got.report == "P01"


def test_a_sum_of_more_than_18_digits_is_refused_by_the_contract():
    raw = json.dumps({"contract_version": 1, "reports": {"P01": {"version": 1, "columns": [
        {"name": "id", "type": "INTEGER", "nullable": False}, {"name": "v", "type": "DECIMAL(19,2)", "nullable": False}],
        "grain": ["id"], "sums": ["v"]}}}).encode()
    with pytest.raises(c.Refused, match="contract_invalid"):
        c.load_contract(raw)


def test_the_content_bound_counts_utf8_bytes_and_zero_for_nothing():
    for data in ([(1, "ação"), (2, "fixture_a")], [], [(1, None)]):
        _check([ID, ("t", "VARCHAR", True)], [], data)


@pytest.mark.parametrize(
    "canonical, expected",
    [("-1234.50", ["-1234.50", "-1.234,50", "-1234,50"]), ("1140", ["1140", "1.140"]), ("1234567", ["1234567", "1.234.567"]), ("12.5", ["12.5", "12,5"])],
)
def test_the_three_numeric_spellings(canonical, expected):
    assert c.spellings(canonical) == expected


@pytest.mark.parametrize("value, eligible", [("12", False), ("100", True), ("12.00", False), ("0.05", True), ("-7", False), ("1140", True)])
def test_which_numbers_are_searched(value, eligible):
    assert c.eligible_number(value) is eligible


@pytest.mark.parametrize("text, scale, ok", [("0.00", 2, True), ("-0.00", 2, False), ("01.00", 2, False), ("1.5", 2, False), ("7", 0, True), ("7.0", 0, False), ("-12.34", 2, True)])
def test_the_canonical_decimal_form(text, scale, ok):
    assert c.canonical_ok(text, scale) is ok


# --- GIMPL-1: the order of the checks, the live boundaries, the version types ------------------


def test_declarations_agree_before_any_candidate_byte(repo, monkeypatch):
    """GIMPL-1-01: disagreeing declarations stop the gate before the candidate is listed."""
    path = repo / "release" / "contract.json"
    data = json.loads(path.read_text())
    data["reports"]["P04"] = data["reports"]["P01"]
    path.write_text(json.dumps(data))
    deploy = repo / "deploy"
    r.build(repo, deploy)
    (deploy / "forbidden.txt").write_text("x")
    monkeypatch.setattr(r, "listing", lambda d: pytest.fail("the candidate was read"))
    with pytest.raises(r.Refused, match="declarations_agree"):
        r.verify(repo, deploy, live=no_live)


@pytest.mark.parametrize(
    "case, code",
    [
        (lambda repo: payload(repo, "P01", types={"valor": "DOUBLE"}, totals=_totals(repo, contract_version=2)), "schema_exact"),
        (lambda repo: payload(repo, "P01", types={"valor": "DOUBLE"}, totals=_totals(repo, extra=1)), "schema_exact"),
        (lambda repo: payload(repo, "P01", [rows("P01")[0], ("fixture_b", None, 1)], totals=_totals(repo, extra=1)), "not_null"),
        (lambda repo: payload(repo, "P01", rows("P01") + [rows("P01")[0]], totals=_totals(repo, contract_version=2)), "grain_unique"),
    ],
    ids=["schema_then_version", "schema_then_shape", "null_then_shape", "grain_then_version"],
)
def test_the_parquet_checks_come_before_the_totals(repo, case, code):
    """GIMPL-1-02: §4's order — schema, nulls, grain, then the totals."""
    seal(repo, payloads(repo, P01=case(repo)))
    refused(repo, code, where="P01")


@pytest.mark.parametrize("key", ["contract_version", "report_version"])
def test_a_boolean_version_is_refused(repo, key):
    """GIMPL-1-05: JSON's `true` is not the version 1."""
    seal(repo, payloads(repo, P01=payload(repo, "P01", totals=_totals(repo, **{key: True}))))
    refused(repo, "totals_version", where="P01")


def test_read_live_a_transport_failure_is_live_unreadable():
    with pytest.raises(r.Refused, match="live_unreadable"):
        r.read_live("s", get=lambda url: (0, b""))


def test_public_get_turns_a_transport_failure_into_no_status(monkeypatch):
    import urllib.error

    class Opener:
        def open(self, *a, **k):
            raise urllib.error.URLError("temporary DNS failure")

    monkeypatch.setattr(r.urllib.request, "build_opener", lambda *a: Opener())
    assert r._public_get("https://s.web.app/package/manifest.json") == (0, b"")


def _raise_transport(*a, **k):
    import urllib.error
    raise urllib.error.URLError("temporary DNS failure")


def test_bind_live_a_transport_failure(monkeypatch):
    monkeypatch.setattr(r, "channel", _raise_transport)
    with pytest.raises(r.Refused, match="live could not be read"):
        r.bind_live("s", record(PATHS), "t")


def test_bind_live_a_release_time_without_offset(hosting):
    hosting.version, hosting.files, hosting.released = "vA", [*PATHS, "package/manifest.json"], "2026-11-06T10:00:00"
    with pytest.raises(r.Refused, match="live could not be read"):
        r.bind_live("s", record(PATHS), "t")


def test_promote_a_transport_failure_clones_nothing(monkeypatch):
    monkeypatch.setattr(r, "channel", _raise_transport)
    with pytest.raises(r.Refused, match="nothing was cloned"):
        r.promote("s", "vB", "vA", "t", run=lambda cmd, check: pytest.fail("cloned"))


def test_promote_a_failed_read_back_is_unconfirmed(monkeypatch):
    import subprocess
    reads = iter([{"release": {"version": {"name": "sites/s/versions/vA"}}}])

    def channel(*a):
        try:
            return next(reads)
        except StopIteration:
            _raise_transport()

    monkeypatch.setattr(r, "channel", channel)
    with pytest.raises(r.Refused, match="unconfirmed"):
        r.promote("s", "vB", "vA", "t", run=lambda cmd, check: subprocess.CompletedProcess(cmd, 0))


@pytest.mark.parametrize("command", ["bind-live", "promote"])
def test_the_cli_turns_a_transport_failure_into_a_refusal(monkeypatch, capfd, tmp_path, command):
    monkeypatch.setattr(r, "channel", _raise_transport)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    rec = tmp_path / "rel.json"
    rec.write_text(json.dumps(record(PATHS)))
    argv = {"bind-live": ["bind-live", "--site", "s", "--record", str(rec)],
            "promote": ["promote", "--site", "s", "--version", "vB", "--live-version", "vA"]}[command]
    assert r.main(argv) == 1
    out, err = capfd.readouterr()
    assert "Traceback" not in out + err
    assert "live could not be read" in summary.read_text()


class _Body:
    """A response whose body cannot be read whole, or is not gzip."""

    def __init__(self, failure, encoding="identity"):
        self.failure, self.status, self.headers = failure, 200, {"Content-Encoding": encoding}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        if self.failure == "truncated":
            import http.client
            raise http.client.IncompleteRead(b"par", 100)
        return b"not gzip at all"


@pytest.mark.parametrize("failure, encoding", [("truncated", "identity"), ("gzip", "gzip")])
def test_the_cli_a_broken_live_body_is_live_unreadable(repo, monkeypatch, capfd, tmp_path, failure, encoding):
    """GIMPL-2-02: through the real public GET, a truncated body and a broken
    gzip stream are refusals, with their summary, no traceback and no record."""

    class Opener:
        def open(self, *a, **k):
            return _Body(failure, encoding)

    monkeypatch.setattr(r.urllib.request, "build_opener", lambda *a: Opener())
    deploy = repo / "deploy"
    r.build(repo, deploy)
    summary, rec = tmp_path / "summary.md", tmp_path / "rel.json"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(r, "ROOT", repo)
    assert r.main(["verify", "--deploy", str(deploy), "--record", str(rec), "--site", "s"]) == 1
    out, err = capfd.readouterr()
    assert "Traceback" not in out + err and not rec.exists()
    assert "live_unreadable" in summary.read_text()
