"""A fake warehouse for the exporter's tests (docs/exporter.md §12): it
implements `source.Source`, answers each statement of the reader from the
committed fixture, and records every statement in order.

Its state is plain data that a test changes to make one mutation: the
inventory, the attributes, the roles, the settings, the collation, the
provenance rows and the rows of each view. `fail_at` makes the n-th statement
fail; `fields_override` changes a result's description only.

The fingerprint is M55's expression as the fake computes it — each row as
PostgreSQL's record text, sorted by code point, joined by newlines, MD5 —
under the fixture's policy (UTC, ISO). It is the fixture's own witness; the
live run proves the real one.
"""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import pathlib
import re
from decimal import Decimal

from bi_como_codigo.exporter import source as S
from bi_como_codigo.exporter import views as V

FIXTURE = pathlib.Path(__file__).resolve().parent / "exporter" / "fixture.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def contract_bytes(fx: dict) -> bytes:
    from bi_como_codigo.exporter import propose as P

    return P.dump(fx["views_json"])


def typed(col: V.ViewColumn, value):
    """A fixture cell as psycopg returns it."""
    if value is None:
        return None
    if col.is_decimal:
        return Decimal(value)
    if col.is_instant:
        return dt.datetime.fromisoformat(value)
    return value


def typed_rows(view: V.View, rows: list[list]) -> list[tuple]:
    return [tuple(typed(col, v) for col, v in zip(view.columns, row)) for row in rows]


_NEEDS_QUOTE = re.compile(r'[",\\()\s]')


def _field_text(col: V.ViewColumn, value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        text = "t" if value else "f"
    elif isinstance(value, dt.datetime):
        u = value.astimezone(dt.timezone.utc)
        text = u.strftime("%Y-%m-%d %H:%M:%S")
        if u.microsecond:
            text += f".{u.microsecond:06d}".rstrip("0")
        text += "+00"
    else:
        text = str(value)
    if text == "" or _NEEDS_QUOTE.search(text):
        return '"' + text.replace("\\", "\\\\").replace('"', '""') + '"'
    return text


def record_text(view: V.View, row: tuple) -> str:
    return "(" + ",".join(_field_text(col, v) for col, v in zip(view.columns, row)) + ")"


def fingerprint(view: V.View, rows: list[tuple]) -> str:
    texts = sorted(record_text(view, r) for r in rows)
    return hashlib.md5("\n".join(texts).encode("utf-8")).hexdigest()


class Fake:
    """The fake warehouse. Every attribute is a test's to change."""

    def __init__(self, fx: dict | None = None, views_raw: bytes | None = None):
        fx = copy.deepcopy(fx or load_fixture())
        self.contract = V.load(views_raw or contract_bytes(fx))
        self.strict_order = True
        self.log: list[tuple[str, tuple]] = []
        self.isolation, self.read_only = "repeatable read", "on"
        self.read_at = dt.datetime(2026, 11, 24, 12, 0, tzinfo=dt.timezone.utc)
        self.provenance = [fx["provenance"]]
        self.session_user = self.current_user = self.contract.login
        self.memberships = [(m.member, m.role, False, m.inherit_option, m.set_option) for m in self.contract.memberships]
        self.roles = {name: {"super": False, "createrole": False, "createdb": False, "replication": False,
                             "bypassrls": False, "canlogin": can} for name, can in self.contract.can_login.items()}
        self.inventory = [(i["oid"], i["relname"], i["relkind"]) for i in fx["inventory"]]
        oids = {name: oid for oid, name, _k in self.inventory}
        self.access = {oid: {**{p: p == "SELECT" for p in S.TABLE_PRIVILEGES},
                             **{f"col_{p}": False for p in S.COLUMN_PRIVILEGES}, "owner": False} for oid in oids.values()}
        self.schema_access = (True, False)
        self.attributes = {oids[v.view]: [(c.name, c.source_oid, c.source_typmod) for c in v.columns] for v in self.contract.views}
        build = self.contract.builds[0]
        self.defaults = dict(build.policy)
        self.hash_policy = dict(build.policy)  # the policy the rows hash under
        self.settings = dict(self.defaults)
        self.set_override: dict[str, str] = {}
        self.encodings = ["UTF8", "UTF8"]
        self.collation = dict(build.collation)
        self.collation_actual = build.collation["datcollversion"]
        self.rows = {v.view: typed_rows(v, fx["rows"][v.view]) for v in self.contract.views}
        self.count_override: dict[str, int] = {}
        self.fingerprint_override: dict[str, tuple[int, str]] = {}
        self.fields_override: dict[str, list[tuple[str, int, int]]] = {}
        self.fail_at: int | None = None
        self.fail_commit = False
        self.committed = self.closed = False
        self._fields: list = []
        self._rows: list = []

    # --- Source ---

    def execute(self, sql: str, params: tuple = ()) -> None:
        if self.committed or self.closed:
            raise RuntimeError("statement after the end of the transaction")
        self.log.append((sql, tuple(params)))
        if self.fail_at is not None and len(self.log) == self.fail_at:
            raise RuntimeError("injected failure, with a secret-looking message: hunter2")
        if self.strict_order and not self._in_order(len(self.log) - 1, sql):
            raise RuntimeError("statement out of the protocol's order")
        self._fields, self._rows = [], []
        self._rows = self._answer(sql, tuple(params))

    def fields(self):
        return list(self._fields)

    def fetchall(self):
        return list(self._rows)

    def commit(self):
        if self.fail_commit:
            raise RuntimeError("injected commit failure")
        self.committed = True

    def close(self):
        self.closed = True

    # --- the protocol: the facts in their order, then each view's three statements ---

    def protocol(self) -> list:
        facts = [S.Q_TRANSACTION, S.Q_PROVENANCE, S.Q_LOGIN, S.Q_MEMBERSHIPS, S.Q_ROLE_ATTRIBUTES, S.Q_INVENTORY,
                 S.Q_ACCESS, S.Q_SCHEMA_ACCESS, S.Q_ATTRIBUTES, *[S.Q_SET_POLICY] * len(V.POLICY_KEYS), S.Q_POLICY, S.Q_COLLATION]
        per_view = [q for v in self.contract.views for q in (S.q_count(v.view), S.q_rows(v), S.q_fingerprint(v.view))]
        return facts + per_view

    def _in_order(self, index: int, sql: str) -> bool:
        expected = self.protocol()
        return index < len(expected) and expected[index] == sql

    # --- the answers ---

    def _view_by_name(self, name: str) -> V.View:
        return self.contract.by_view()[name]

    def _answer(self, sql: str, params: tuple) -> list[tuple]:
        if sql == S.Q_TRANSACTION:
            return [(self.isolation, self.read_only, self.read_at)]
        if sql == S.Q_PROVENANCE:
            return [(p["status"], p["invocation_id"], p["built_from_commit"], p["sequence"]) for p in self.provenance]
        if sql == S.Q_LOGIN:
            return [(self.session_user, self.current_user)]
        if sql == S.Q_MEMBERSHIPS:
            return sorted(self.memberships)
        if sql == S.Q_ROLE_ATTRIBUTES:
            return [(n, r["super"], r["createrole"], r["createdb"], r["replication"], r["bypassrls"], r["canlogin"])
                    for n, r in sorted(self.roles.items())]
        if sql == S.Q_INVENTORY:
            assert params == (S.SCHEMA,)
            return sorted(self.inventory, key=lambda r: r[1])
        if sql == S.Q_ACCESS:
            wanted = set(params[0])
            return [(oid, *[a[p] for p in S.TABLE_PRIVILEGES], *[a[f"col_{p}"] for p in S.COLUMN_PRIVILEGES], a["owner"])
                    for oid, a in sorted(self.access.items()) if oid in wanted]
        if sql == S.Q_SCHEMA_ACCESS:
            return [self.schema_access]
        if sql == S.Q_ATTRIBUTES:
            wanted = set(params[0])
            return [(oid, *col) for oid, cols in sorted(self.attributes.items()) if oid in wanted for col in cols]
        if sql == S.Q_SET_POLICY:
            key, value = params
            self.settings[key] = self.set_override.get(key, value)
            return [(self.settings[key],)]
        if sql == S.Q_POLICY:
            return [tuple(self.settings[k] for k in V.POLICY_KEYS) + tuple(self.encodings)]
        if sql == S.Q_COLLATION:
            return [tuple(self.collation[k] for k in V.COLLATION_KEYS) + (self.collation_actual,)]
        m = re.fullmatch(r'SELECT count\(\*\) FROM consumption\."([a-z0-9_]+)"', sql)
        if m:
            return [(self.count_override.get(m[1], len(self.rows[m[1]])),)]
        m = re.fullmatch(r'SELECT (.+) FROM consumption\."([a-z0-9_]+)"', sql)
        if m:
            view = self._view_by_name(m[2])
            names = [n.strip('"') for n in m[1].split(", ")]
            assert names == list(view.names), "the reader selects the contract's columns, in order"
            oid = next(o for o, n, _k in self.inventory if n == m[2])
            self._fields = self.fields_override.get(m[2], list(self.attributes[oid]))
            return list(self.rows[m[2]])
        m = re.fullmatch(r"SELECT count\(\*\), md5\(.+\) FROM consumption\.\"([a-z0-9_]+)\" t", sql)
        if m:
            if m[1] in self.fingerprint_override:
                return [self.fingerprint_override[m[1]]]
            view = self._view_by_name(m[1])
            if self.settings != self.hash_policy:
                return [(len(self.rows[m[1]]), "0" * 32)]  # another text form, another hash
            return [(len(self.rows[m[1]]), fingerprint(view, self.rows[m[1]]))]
        raise AssertionError(f"the fake does not know this statement: {sql}")
