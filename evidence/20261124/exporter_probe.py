"""A probe of the exporter (docs/exporter.md) against a real PostgreSQL 16, with
no data of eng_dados: an isolated, throwaway container of the same image as
the warehouse's (`postgres:16.15-alpine`), on 127.0.0.1, holding the 16 views'
real columns over the **invented** rows of `tests/exporter/fixture.json`.

It proves, on PostgreSQL itself and through the pinned psycopg, what the fake of
§12 can only encode (§14's assumptions): the SQL of §3, `pg_auth_members`'
options and `pg_database`'s ICU fields in 16, the result's modifiers by
`pgresult.fmod`, numerics as exact `Decimal`, `timestamptz` as aware
datetimes and `infinity` as the adapter's sentinel, the fingerprint of M55's
expression, and a whole export through the real adapter. It writes nothing
into Git but its own output.

    docker run -d --rm --name bice-exporter-probe -e POSTGRES_PASSWORD=<local> \
        -e POSTGRES_DB=probe -p 127.0.0.1:55432:5432 postgres:16.15-alpine
    BICE_PROBE_PASSWORD=<local> uv run --frozen python evidence/20261124/exporter_probe.py
    docker stop bice-exporter-probe
"""

from __future__ import annotations

import datetime as dt
import functools
import json
import os
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

import psycopg  # noqa: E402

import exporter_world as xw  # noqa: E402
import fake_warehouse as fw  # noqa: E402
from bi_como_codigo import envelope as e  # noqa: E402
from bi_como_codigo.exporter import propose as P, run, source as S, views as V  # noqa: E402

PORT = "55432"
READER_PASSWORD = "probe-reader-local"  # the throwaway container's own, never a real one
ADMIN = dict(host="127.0.0.1", port=PORT, dbname="probe", user="postgres", password=os.environ.get("BICE_PROBE_PASSWORD", ""))


def sql_literal(col: V.ViewColumn, value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, dt.datetime):
        return "'" + value.isoformat() + "'"
    return "'" + str(value).replace("'", "''") + "'"


CAST = {"character varying": "varchar", "text": "text", "integer": "integer", "bigint": "bigint",
        "numeric": "numeric", "boolean": "boolean", "timestamp with time zone": "timestamptz"}


def build(admin, contract: V.ViewContract, rows: dict[str, list[tuple]], provenance: dict) -> None:
    cur = admin.cursor()
    cur.execute("CREATE ROLE analyst NOLOGIN")
    cur.execute(f"CREATE ROLE consumption_reader LOGIN PASSWORD '{READER_PASSWORD}' IN ROLE analyst")
    cur.execute("CREATE SCHEMA consumption")
    cur.execute("CREATE SCHEMA governance")
    cur.execute("CREATE TABLE governance.warehouse_provenance (status text, reason text, invocation_id uuid,"
                " built_from_commit text, built_at timestamptz, sequence bigint)")
    cur.execute("INSERT INTO governance.warehouse_provenance VALUES (%s, NULL, %s, %s, now(), %s)",
                (provenance["status"], provenance["invocation_id"], provenance["built_from_commit"], provenance["sequence"]))
    for view in contract.views:
        values = ", ".join("(" + ", ".join(sql_literal(c, v) for c, v in zip(view.columns, r)) + ")" for r in rows[view.view])
        select = ", ".join(f'CAST(t."{c.name}" AS {CAST[c.source_type]}) AS "{c.name}"' for c in view.columns)
        names = ", ".join(f'"{c.name}"' for c in view.columns)
        cur.execute(f'CREATE VIEW consumption."{view.view}" AS SELECT {select} FROM (VALUES {values}) AS t({names})')
    cur.execute("GRANT USAGE ON SCHEMA consumption, governance TO analyst")
    cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA consumption TO analyst")
    cur.execute("GRANT SELECT ON governance.warehouse_provenance TO analyst")
    admin.commit()


def reader_environ(world) -> dict:
    env = dict(world.environ)
    env.update({"BICE_WAREHOUSE_HOST": "127.0.0.1", "BICE_WAREHOUSE_PORT": PORT, "BICE_WAREHOUSE_DB": "probe",
                "BICE_WAREHOUSE_USER": "consumption_reader", "BICE_WAREHOUSE_PASSWORD": READER_PASSWORD,
                "BICE_WAREHOUSE_SSLMODE": "disable"})
    return env


def main() -> int:
    e.derive_kek = functools.cache(e.derive_kek)
    fx = fw.load_fixture()
    contract = V.load(fw.contract_bytes(fx))
    rows = {v.view: fw.typed_rows(v, fx["rows"][v.view]) for v in contract.views}
    print(f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ} — the exporter against an isolated PostgreSQL, invented rows")
    with psycopg.connect(**ADMIN) as admin:
        print("server:", admin.execute("SHOW server_version").fetchone()[0])
        build(admin, contract, rows, fx["provenance"])

    world = xw.make_world()
    try:
        found = S.settings(reader_environ(world))
        # §3 check 7's baseline, through the real adapter
        source = S.connect(found, world.base / "absent", environ=dict(os.environ))
        try:
            catalogue = S.catalogue(source, "consumption_reader", {v.view for v in contract.views},
                                    {k: fx["provenance"][k] for k in ("built_from_commit", "invocation_id", "sequence")})
        finally:
            source.close()
        typmods = {c["typmod"] for v in catalogue["views"] for c in v["columns"]}
        oids = sorted({c["oid"] for v in catalogue["views"] for c in v["columns"]})
        print("catalogue: memberships", catalogue["memberships"], "can_login", catalogue["can_login"])
        print("catalogue: type OIDs", oids, "modifiers", sorted(typmods))
        print("catalogue: defaults", catalogue["defaults"], "encodings", catalogue["encodings"])
        print("catalogue: collation", catalogue["collation"], "actual", catalogue["collation_actual_version"])
        invented = json.loads(xw.ROOT.joinpath("tests", "exporter", "catalogue.json").read_text())
        same = all(
            [(c["name"], c["oid"], c["typmod"]) for c in a["columns"]] == [(c["name"], c["oid"], c["typmod"]) for c in b["columns"]]
            for a, b in zip(sorted(catalogue["views"], key=lambda v: v["view"]), sorted(invented["views"], key=lambda v: v["view"])))
        print("catalogue: columns, OIDs and modifiers equal to the invented catalogue's:", same)

        # the adapter's types, and the result's modifiers by position
        with psycopg.connect(**{**ADMIN}) as admin:
            probe = S.PsycopgSource({**S.connection_parameters(found, world.base / "absent2"), "user": "postgres",
                                     "password": ADMIN["password"]})
            probe.execute("SELECT 1.50::numeric, 'NaN'::numeric, 'infinity'::numeric, 'infinity'::timestamptz,"
                          " '2025-03-01 10:00:00.123457-03'::timestamptz, 12.5::numeric(8,4), 'x'::varchar(9)")
            fields = probe.fields()
            values = probe.fetchall()[0]
            probe.commit()
            probe.close()
        print("adapter: fields", fields)
        print("adapter: values", [type(v).__name__ + ":" + (repr(v) if v is not S.UNREPRESENTABLE else "UNREPRESENTABLE") for v in values])

        # the witness, by M55's expression under the policy the catalogue read
        with psycopg.connect(**ADMIN) as admin:
            for k in V.POLICY_KEYS:
                admin.execute("SELECT set_config(%s, %s, true)", (k, catalogue["defaults"][k]))
            witness = [{"view": v.view, "rows": admin.execute(S.q_fingerprint(v.view)).fetchone()[0],
                        "md5": admin.execute(S.q_fingerprint(v.view)).fetchone()[1]} for v in sorted(contract.views, key=lambda x: x.view)]
        fake_equal = sum(1 for w in witness if w["md5"] == fw.fingerprint(contract.by_view()[w["view"]], rows[w["view"]]))
        print(f"witness: the fake's fingerprint equals PostgreSQL's for {fake_equal} of 16 views")

        # a whole export through the real adapter
        body = world.views_json()
        for v in body["views"]:
            got = {c["name"]: c for c in next(x for x in catalogue["views"] if x["view"] == v["view"])["columns"]}
            for c in v["columns"]:
                c["source_oid"], c["source_typmod"] = got[c["name"]]["oid"], got[c["name"]]["typmod"]
        body["accepted_builds"][0].update({"policy": catalogue["defaults"], "collation": catalogue["collation"], "witness": witness})
        world.write_views(body)
        receipt = run.export(world.root, reader_environ(world), fetch_metadata=world.fetch_metadata())
        print("export: facts", [f["code"] for f in receipt["facts"]])
        print("export: views", len(receipt["views"]), "witness equal", all(v["witness_equal"] for v in receipt["views"]),
              "rows", sum(v["rows"] for v in receipt["views"]))
        print("export: verify", receipt["candidate"]["verify"])
        print("export: result", sorted(p.name for p in world.out.iterdir()))
    finally:
        world.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
